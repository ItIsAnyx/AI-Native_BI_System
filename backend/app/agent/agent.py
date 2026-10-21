import json

from fastapi import HTTPException
from openai import AsyncOpenAI
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.agent.prompts import summary_prompt
from app.tools.dataset import list_sources, load_source
from app.tools.tools import tools, TOOL_FUNCTIONS


async def call_llm(
    client: AsyncOpenAI,
    messages: list[dict[str, str]],
    df = None,
    use_tools: bool = False,
    chart_artifacts: list[dict] | None = None,
    sources: list[dict] | None = None,
    active_source_id: str | None = None,
) -> str:

    if not settings.MODEL_NAME:
        raise HTTPException(status_code=503, detail="Model is not configured. Set MODEL_NAME and restart the application")

    working_messages = [dict(message) for message in messages]
    sources = sources or []
    dataframes = {}
    if df is not None:
        dataframes[active_source_id] = df
    if use_tools:
        availability_note = (
            "\n\n<source_metadata>\n"
            + json.dumps({
                "sources": list_sources(sources),
                "active_source_id": active_source_id,
            }, ensure_ascii=False)
            + "\n</source_metadata>"
        )
        if working_messages and working_messages[0]["role"] == "system":
            working_messages[0]["content"] += availability_note
        else:
            working_messages.insert(0, {"role": "system", "content": availability_note})
    max_tool_calls = settings.MAX_TOOL_CALLS
    tool_calls_used = 0

    while True:
        tools_enabled = (
            use_tools and tool_calls_used < max_tool_calls
        )

        out = await client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=working_messages,
            tools=tools if tools_enabled else [],
            tool_choice="auto" if tools_enabled else "none",
            temperature=0.6,
        )
        if not out.choices:
            raise HTTPException(status_code=502, detail="Model returned no results")

        message = out.choices[0].message
        if not message.tool_calls:
            answer = message.content or ""

            if not answer.strip():
                raise HTTPException(status_code=502, detail="Model returned an empty answer")
            return answer

        if not tools_enabled:
            raise HTTPException(status_code=502, detail="Model requested tools when they were disabled")

        working_messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                call.model_dump(exclude_none=True)
                for call in message.tool_calls
            ],
        })

        for tool_call in message.tool_calls:
            if tool_calls_used >= max_tool_calls:
                result = {
                    "error": (
                        "Tool-call limit reached. Answer using the available results."
                    )
                }
            else:
                tool_calls_used += 1
                name = tool_call.function.name

                try:
                    if name not in TOOL_FUNCTIONS:
                        raise ValueError(f"Unknown tool: {name}")

                    args = json.loads(tool_call.function.arguments)
                    if not isinstance(args, dict):
                        raise ValueError("Tool arguments must be a JSON object")

                    function = TOOL_FUNCTIONS[name]
                    if name == "list_sources":
                        result = await run_in_threadpool(function, sources=sources, **args)
                    else:
                        source_id = args.pop("source_id", None) or active_source_id
                        if source_id not in dataframes:
                            dataframes[source_id] = await run_in_threadpool(load_source, sources, source_id)
                        result = await run_in_threadpool(function, df=dataframes[source_id], **args)
                        if source_id:
                            result["source_id"] = source_id
                    if name == "build_chart":
                        if chart_artifacts is not None:
                            chart_artifacts.append(result)
                        # Image bytes never enter the model context or chat history.
                        result = {key: value for key, value in result.items() if key != "image_base64"}

                except (ValueError, TypeError) as exc:
                    result = {"error": str(exc)}

            working_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })


async def compact_context(
    client: AsyncOpenAI,
    context: list[dict[str, str]],
) -> list[dict[str, str]]:
    context_length = sum(len(message["content"]) for message in context)
    if context_length <= settings.MAX_CONTEXT_LENGTH or len(context) <= 2:
        return context

    summary = await call_llm(client, [
        {"role": "system", "content": summary_prompt},
        {"role": "user", "content": json.dumps(context[1:-1], ensure_ascii=False)},
    ], use_tools=False,)
    return [
        context[0],
        {"role": "assistant", "content": "Short summary of the previous dialogue:\n" + summary},
        context[-1],
    ]
