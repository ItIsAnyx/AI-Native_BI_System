import json

from fastapi import HTTPException
from openai import APIError, AsyncOpenAI
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.agent.prompts import summary_prompt
from app.agent.token_counter import count_tokens
from app.tools.dataset import list_sources, load_source
from app.tools.tools import tools, TOOL_FUNCTIONS


CONTEXT_LIMIT_MESSAGE = (
    "Запрошенные данные не помещаются в контекст модели, а пересказ не помог. "
    "Я не могу проанализировать их целиком в этом запросе. "
    "Укажите конкретные столбцы, значения или меньшую выборку данных."
)


class ContextLimitError(Exception):
    pass


async def request_model(
    client: AsyncOpenAI, messages: list[dict], use_tools: bool = False,
    continue_final_message: bool = False,
):
    if not settings.MODEL_NAME:
        raise HTTPException(status_code=503, detail="Model is not configured. Set MODEL_NAME and restart the application")
    available_tokens = settings.MAX_CONTEXT_TOKENS - settings.MAX_RESPONSE_TOKENS
    if available_tokens <= 0:
        raise HTTPException(status_code=503, detail="MAX_RESPONSE_TOKENS must be smaller than MAX_CONTEXT_TOKENS")
    token_count = await run_in_threadpool(count_tokens, messages, tools if use_tools else None, continue_final_message)
    if token_count > available_tokens:
        raise ContextLimitError()
    return await client.chat.completions.create(
        model=settings.MODEL_NAME, messages=messages,
        tools=tools if use_tools else [],
        tool_choice="auto" if use_tools else "none",
        temperature=0.6, max_tokens=settings.MAX_RESPONSE_TOKENS,
    )


async def summarize_messages(client: AsyncOpenAI, messages: list[dict]) -> str | None:
    try:
        out = await request_model(client, [
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": json.dumps(messages, ensure_ascii=False)},
        ])
    except (ContextLimitError, APIError):
        return None
    if not out.choices or out.choices[0].finish_reason != "stop":
        return None
    summary = out.choices[0].message.content or ""
    return summary if summary.strip() else None


async def continue_answer(client: AsyncOpenAI, messages: list[dict], answer: str) -> str:
    question_index = max(index for index, message in enumerate(messages) if message["role"] == "user")
    question = dict(messages[question_index])
    previous_context = messages[1:question_index] + messages[question_index + 1:]
    summary = await summarize_messages(client, previous_context) if previous_context else None
    if summary is not None:
        context = [messages[0], {
            "role": "assistant", "content": "Summary of the preceding context and tool results:\n" + summary,
        }, question]
    else:
        context = [dict(message) for message in messages]
    context[0] = {**context[0], "content": context[0]["content"] + (
        "\nThe assistant answer was interrupted by the output token limit. "
        "Continue it exactly from its end, preserving language and formatting. "
        "Do not repeat or summarize the existing answer and do not call tools."
    )}
    for _ in range(settings.MAX_CONTINUATIONS):
        continuation_context = context + ([{"role": "assistant", "content": answer}] if answer else [])
        try:
            out = await request_model(client, continuation_context, continue_final_message=bool(answer))
        except (ContextLimitError, APIError):
            break
        if not out.choices or out.choices[0].message.tool_calls:
            break
        choice = out.choices[0]
        answer += choice.message.content or ""
        if choice.finish_reason == "stop" and answer.strip():
            return answer
        if choice.finish_reason != "length":
            break
    notice = "Ответ модели был прерван; автоматически завершить его не удалось. Сократите запрос или попросите продолжить."
    return answer + "\n\n" + notice if answer else notice


async def answer_context_limit(client: AsyncOpenAI, messages: list[dict]) -> str:
    question_index = max(index for index, message in enumerate(messages) if message["role"] == "user")
    last_question = messages[question_index]
    summary = await summarize_messages(client, messages[1:question_index] + messages[question_index + 1:])
    if summary is None:
        return CONTEXT_LIMIT_MESSAGE
    context = [
        {"role": "system", "content": messages[0]["content"] + (
            "\nTool execution stopped because the context token limit was reached. "
            "Use only the summary, explain the limitation in the user's language, "
            "and ask for specific columns, values or a smaller selection."
        )},
        {"role": "assistant", "content": summary},
        last_question,
    ]
    try:
        out = await request_model(client, context)
    except (ContextLimitError, APIError):
        return CONTEXT_LIMIT_MESSAGE
    if not out.choices:
        return CONTEXT_LIMIT_MESSAGE
    answer = out.choices[0].message.content or ""
    if out.choices[0].finish_reason == "length":
        return await continue_answer(client, context, answer)
    if out.choices[0].finish_reason != "stop" or out.choices[0].message.tool_calls:
        return CONTEXT_LIMIT_MESSAGE
    return answer if answer.strip() else CONTEXT_LIMIT_MESSAGE


async def call_llm(
    client: AsyncOpenAI,
    messages: list[dict[str, str]],
    df = None,
    use_tools: bool = False,
    chart_artifacts: list[dict] | None = None,
    sources: list[dict] | None = None,
    active_source_id: str | None = None,
) -> str:

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

        try:
            out = await request_model(client, working_messages, tools_enabled)
        except ContextLimitError:
            return await answer_context_limit(client, working_messages)
        if not out.choices:
            raise HTTPException(status_code=502, detail="Model returned no results")

        message = out.choices[0].message
        if not message.tool_calls:
            answer = message.content or ""
            if out.choices[0].finish_reason == "length":
                return await continue_answer(client, working_messages, answer)
            if out.choices[0].finish_reason != "stop":
                raise HTTPException(status_code=502, detail="Model stopped without completing its answer")
            if not answer.strip():
                raise HTTPException(status_code=502, detail="Model returned an empty answer")
            return answer

        if not tools_enabled:
            raise HTTPException(status_code=502, detail="Model requested tools when they were disabled")
        if out.choices[0].finish_reason == "length":
            raise HTTPException(status_code=502, detail="Model stopped before completing its tool calls")

        tool_calls = []
        for call in message.tool_calls:
            saved_call = call.model_dump(exclude_none=True)
            try:
                arguments = json.loads(call.function.arguments)
                if not isinstance(arguments, dict):
                    raise ValueError("Tool arguments must be a JSON object")
            except (ValueError, TypeError):
                saved_call["function"]["arguments"] = "{}"
            tool_calls.append(saved_call)
        working_messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": tool_calls,
        })

        token_count = await run_in_threadpool(count_tokens, working_messages, tools)
        context_exceeded = token_count > settings.MAX_CONTEXT_TOKENS - settings.MAX_RESPONSE_TOKENS
        for tool_call in message.tool_calls:
            if context_exceeded:
                result = {"error": "Context token limit reached. Tool execution stopped."}
            elif tool_calls_used >= max_tool_calls:
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
                except HTTPException as exc:
                    if exc.status_code not in (400, 404):
                        raise
                    result = {"error": str(exc.detail)}
                except OSError:
                    result = {"error": "Cannot read the saved CSV source."}

            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            }
            if not context_exceeded:
                token_count = await run_in_threadpool(count_tokens, working_messages + [tool_message], tools)
                if token_count > settings.MAX_CONTEXT_TOKENS - settings.MAX_RESPONSE_TOKENS:
                    context_exceeded = True
                    tool_message["content"] = json.dumps({
                        "error": "Context token limit reached. The result was omitted and tool execution stopped.",
                    })
            working_messages.append(tool_message)
        if context_exceeded:
            return await answer_context_limit(client, working_messages)


async def compact_context(
    client: AsyncOpenAI,
    context: list[dict[str, str]],
) -> list[dict[str, str]]:
    context_length = sum(len(message["content"]) for message in context)
    if context_length <= settings.MAX_CONTEXT_LENGTH or len(context) <= 2:
        return context

    summary = await summarize_messages(client, context[1:-1])
    if summary is None:
        return context
    return [
        context[0],
        {"role": "assistant", "content": "Short summary of the previous dialogue:\n" + summary},
        context[-1],
    ]
