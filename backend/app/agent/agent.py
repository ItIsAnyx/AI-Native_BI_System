import json
import re
from uuid import uuid4

from fastapi import HTTPException
from openai import APIError, AsyncOpenAI
from app.services.cancellation import interruptible, run_in_threadpool
from app.agent.completion import model_completion

from app.config import settings
from app.agent.prompts import summary_prompt
from app.agent.tool_results import has_tool_markup, render_tool_results, render_query_results
from app.agent.operation_review import review_tool_call
from app.agent.tool_selection import select_model_tools
from app.agent.token_counter import count_tokens
from app.tools.dataset import list_sources, load_source
from app.tools.joins import join_source_ids
from app.tools.errors import DataSelectionError
from app.tools.tools import tools, MODEL_TOOLS, TOOL_FUNCTIONS, TRANSFORM_TOOLS, ANALYTIC_TOOLS


CONTEXT_LIMIT_MESSAGE = (
    "Запрошенные данные не помещаются в контекст модели, а пересказ не помог. "
    "Я не могу проанализировать их целиком в этом запросе. "
    "Укажите конкретные столбцы, значения или меньшую выборку данных."
)


class ContextLimitError(Exception):
    pass


def completed_executions(executions):
    return [{"name": item["name"], "arguments": item["arguments"],
             "result": {key: value[:20] if key == "rows" else value for key, value in item["result"].items()
                        if key in {"error", "source_id", "parent_source_id", "frequency", "total_rows", "chart_type", "panels",
                                   "title", "aggregation", "x_column", "y_column", "rows", "columns", "method", "calculation_note"}}}
            for item in executions if isinstance(item["result"], dict)]


async def request_model(
    client: AsyncOpenAI, messages: list[dict], use_tools: bool = False,
    continue_final_message: bool = False,
    available_tools: list | None = None,
):
    if not settings.MODEL_NAME:
        raise HTTPException(status_code=503, detail="Model is not configured. Set MODEL_NAME and restart the application")
    available_tokens = settings.MAX_CONTEXT_TOKENS - settings.MAX_RESPONSE_TOKENS
    if available_tokens <= 0:
        raise HTTPException(status_code=503, detail="MAX_RESPONSE_TOKENS must be smaller than MAX_CONTEXT_TOKENS")
    menu = MODEL_TOOLS if available_tools is None else available_tools
    token_count = await run_in_threadpool(count_tokens, messages, menu if use_tools else None, continue_final_message)
    if token_count > available_tokens:
        raise ContextLimitError()
    return await interruptible(model_completion(client,
        model=settings.MODEL_NAME, messages=messages,
        tools=menu if use_tools else [],
        tool_choice="auto" if use_tools else "none",
        temperature=0, max_tokens=settings.MAX_RESPONSE_TOKENS,
    ))


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
    processed_sources: list[dict] | None = None,
    user_request: str | None = None,
) -> str:

    working_messages = [dict(message) for message in messages]
    sources = sources or []
    dataframes = {}
    if df is not None:
        dataframes[active_source_id] = df
    last_question = user_request if user_request is not None else next(
        (message["content"] for message in reversed(messages) if message["role"] == "user"), "")
    russian = bool(re.search(r"[А-Яа-яЁё]", last_question))
    executions = []
    repaired_draft = False
    selection_error = None
    operation_reviews = {}
    # Review follow-up requests against the same dialogue as the main agent.
    # Keep recent context bounded; these messages are data for the reviewer.
    review_dialogue = [{"role": m["role"], "content": m["content"][-4000:]}
                       for m in messages[1:-1][-6:]]
    workflow_checks = 0
    if use_tools:
        availability_note = (
            "\n\n<source_metadata>\n"
            + json.dumps({
                "sources": list_sources(sources),
                "active_source_id": active_source_id,
                "query_table": "dataset",
                "query_table_note": "query_dataset SQL always uses FROM dataset; source_id selects its data separately, never use the filename or UUID as a SQL table name.",
                "active_schema": {"total_rows": len(df), "columns": {name: str(dtype) for name, dtype in df.dtypes.items()},
                                  "key_columns": df.attrs.get("key_columns", []),
                                  "technical_id_column": df.attrs.get("technical_id_column")} if df is not None else None,
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
            out = await request_model(client, working_messages, tools_enabled,
                                      available_tools=select_model_tools(last_question, executions))
        except ContextLimitError:
            grounded = render_tool_results(executions, russian)
            if grounded:
                return grounded + "\n\n" + CONTEXT_LIMIT_MESSAGE
            return await answer_context_limit(client, working_messages)
        if not out.choices:
            raise HTTPException(status_code=502, detail="Model returned no results")

        message = out.choices[0].message
        if not message.tool_calls:
            answer = message.content or ""
            if not repaired_draft and tools_enabled and has_tool_markup(answer):
                repaired_draft = True
                working_messages.extend([
                    {"role": "assistant", "content": answer},
                    {"role": "system", "content": "The preceding XML did not execute a tool. If the user requested an operation, use a native tool call. "
                     "Do not print XML or JSON instead of executing it. If the operation is invalid, explain why and ask for clarification."},
                ])
                continue
            grounded = render_tool_results(executions, russian)
            workflow_executed = bool(executions)
            if workflow_executed and not selection_error and out.choices[0].finish_reason in ("stop", "length"):
                completed = completed_executions(executions)
                mismatch = await review_tool_call(client, last_question, "completed_workflow",
                                                 {"executions": completed, "answer": answer}, sources, active_source_id, review_dialogue)
                workflow_checks += 1
                if mismatch:
                    if tools_enabled and workflow_checks == 1:
                        working_messages.extend([
                            {"role": "assistant", "content": answer},
                            {"role": "system", "content": "The requested workflow is incomplete. " + mismatch
                             + " Execute only the missing requested steps with native tools on the correct source. "
                             "Correct mismatched calculations on their parent_source_id, not on the derived result. "
                             "Preserve already-correct transformations and do not claim unexecuted steps finished."},
                        ])
                        continue
                    notice = ("Не все запрошенные операции завершены. " if russian
                              else "Some requested operations remain incomplete. ") + mismatch
                    return notice
            query_answer = render_query_results(executions, russian)
            if query_answer and out.choices[0].finish_reason in ("stop", "length"):
                return query_answer
            if out.choices[0].finish_reason == "length":
                return await continue_answer(client, working_messages, answer)
            if out.choices[0].finish_reason != "stop":
                raise HTTPException(status_code=502, detail="Model stopped without completing its answer")
            if not answer.strip():
                raise HTTPException(status_code=502, detail="Model returned an empty answer")
            if has_tool_markup(answer):
                return ("Не удалось выполнить корректный вызов инструмента. Повторите запрос или уточните параметры."
                        if russian else "Could not execute a valid tool call. Retry or clarify the parameters.")
            if use_tools and sources and not executions:
                mismatch = await review_tool_call(client, last_question, "unexecuted_answer", {"answer": answer}, sources, active_source_id, review_dialogue)
                if mismatch:
                    if tools_enabled and not repaired_draft:
                        repaired_draft = True
                        working_messages.extend([
                            {"role": "assistant", "content": answer},
                            {"role": "system", "content": "No tools executed in this request. " + mismatch
                             + " Use a native call for an actually requested operation, or explain why it cannot be performed."},
                        ])
                        continue
                    return ("В этом запросе обработка данных не выполнялась. Уточните параметры или повторите запрос."
                            if russian else "No data operation was executed in this request. Clarify the parameters or retry.")
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

        token_count = await run_in_threadpool(count_tokens, working_messages, MODEL_TOOLS)
        context_exceeded = token_count > settings.MAX_CONTEXT_TOKENS - settings.MAX_RESPONSE_TOKENS
        for tool_call in message.tool_calls:
            executed_arguments = {}
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
                    contract = next(t["function"]["parameters"] for t in tools if t["function"]["name"] == name)
                    missing = [key for key in contract.get("required", []) if key not in args]
                    if missing:
                        raise ValueError("Не переданы обязательные параметры: " + ", ".join(missing))
                    executed_arguments = dict(args)
                    if selection_error and name in (TRANSFORM_TOOLS - ANALYTIC_TOOLS) | {"join_tables", "get_rows_by_period", "build_dashboard", "build_chart"}:
                        raise DataSelectionError("Требуется уточнение после ошибки выбора данных: " + selection_error)
                    # SELECT cannot modify the source. Validate it in the engine,
                    # then review the actual completed calculation below.
                    if name in (TRANSFORM_TOOLS - ANALYTIC_TOOLS) | {"join_tables", "get_rows_by_period", "build_dashboard", "build_chart"}:
                        review_key = (name, json.dumps(args, sort_keys=True, ensure_ascii=False), active_source_id,
                                      tuple(source["id"] for source in sources))
                        if review_key not in operation_reviews:
                            operation_reviews[review_key] = await review_tool_call(
                                client, last_question, name, args, sources, active_source_id, review_dialogue)
                        mismatch = operation_reviews[review_key]
                        if mismatch:
                            raise ValueError(mismatch)

                    function = TOOL_FUNCTIONS[name]
                    if name == "list_sources":
                        result = await run_in_threadpool(function, sources=sources, **args)
                    elif name == "join_tables":
                        source_ids = join_source_ids(args.get("source_id"), args.get("joins"))
                        available_ids = {source["id"] for source in sources}
                        if any(source_id not in available_ids for source_id in source_ids):
                            raise ValueError("Выберите доступные CSV-источники текущего чата через list_sources")
                        for source_id in source_ids:
                            if source_id not in dataframes:
                                dataframes[source_id] = await run_in_threadpool(load_source, sources, source_id)
                        selected = {source_id: dataframes[source_id] for source_id in source_ids}
                        result = await run_in_threadpool(function, dataframes=selected, **args)
                    else:
                        source_id = args.pop("source_id", None) or active_source_id
                        if name in TRANSFORM_TOOLS:
                            if processed_sources is None:
                                raise ValueError("Сохранение обработанных источников не настроено")
                            if not any(source["id"] == source_id for source in sources):
                                raise ValueError("Выберите доступный CSV-источник текущего чата через list_sources")
                        if source_id not in dataframes:
                            dataframes[source_id] = await run_in_threadpool(load_source, sources, source_id)
                        result = await run_in_threadpool(function, df=dataframes[source_id], **args)
                        if name in TRANSFORM_TOOLS:
                            processed_df = result.pop("_dataframe")
                            parent = next(source for source in sources if source["id"] == source_id)
                            new_id = str(uuid4())
                            derived = {
                                "id": new_id, "name": parent["name"].rsplit(".", 1)[0][:180] + f"_{name}.csv",
                                "description": f"{name}; исходный источник: {source_id}", "type": "csv",
                            }
                            dataframes[new_id] = processed_df
                            sources.append(derived)
                            processed_sources.append({"source": derived, "dataframe": processed_df})
                            result["parent_source_id"] = source_id
                            result["active_source_id"] = new_id
                            active_source_id = source_id = new_id
                        if source_id:
                            result["source_id"] = source_id
                    if name in {"build_chart", "build_dashboard"}:
                        if chart_artifacts is not None:
                            chart_artifacts.append(result)
                        # Image bytes never enter the model context or chat history.
                        result = {key: value for key, value in result.items() if key != "image_base64"}

                except DataSelectionError as exc:
                    if name not in ANALYTIC_TOOLS:
                        selection_error = selection_error or str(exc)
                    result = {"error": str(exc)}
                except (ValueError, TypeError) as exc:
                    result = {"error": str(exc)}
                except HTTPException as exc:
                    if exc.status_code not in (400, 404):
                        raise
                    result = {"error": str(exc.detail)}
                except OSError:
                    result = {"error": "Cannot read the saved CSV source."}

            executions.append({"name": tool_call.function.name, "arguments": executed_arguments, "result": result})

            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            }
            if not context_exceeded:
                token_count = await run_in_threadpool(count_tokens, working_messages + [tool_message], MODEL_TOOLS)
                if token_count > settings.MAX_CONTEXT_TOKENS - settings.MAX_RESPONSE_TOKENS:
                    context_exceeded = True
                    tool_message["content"] = json.dumps({
                        "error": "Context token limit reached. The result was omitted and tool execution stopped.",
                    })
            working_messages.append(tool_message)
        if context_exceeded:
            grounded = render_tool_results(executions, russian)
            if grounded:
                return grounded + "\n\n" + CONTEXT_LIMIT_MESSAGE
            return await answer_context_limit(client, working_messages)
        # A parameterized metric already produces a complete answer. Check it
        # against the user's full request without an extra numerical paraphrase.
        # Missing charts or other deliverables return to the regular tool loop.
        candidate = render_query_results(executions, russian)
        if (candidate and executions[-1]["name"] in ANALYTIC_TOOLS - {"query_dataset"}
                and "error" not in executions[-1]["result"] and not selection_error and workflow_checks == 0):
            mismatch = await review_tool_call(client, last_question, "completed_workflow",
                {"executions": completed_executions(executions), "answer": candidate}, sources, active_source_id, review_dialogue)
            workflow_checks += 1
            if not mismatch:
                return candidate
            working_messages.append({"role": "system", "content": "The requested workflow is incomplete. " + mismatch
                + " Execute missing steps; correct mismatched calculations on their parent_source_id, not the derived result. "
                "Preserve already-correct calculations."})


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
