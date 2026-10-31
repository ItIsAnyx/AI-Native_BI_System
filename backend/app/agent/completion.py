"""Consume a model stream internally so closing it interrupts inference upstream."""
from openai.types.chat import ChatCompletion
from app.agent.messages import normalize_messages


async def model_completion(client, on_chunk=None, **parameters):
    parameters["messages"] = normalize_messages(parameters["messages"])
    stream = await client.chat.completions.create(**parameters, stream=True)
    content, calls = [], {}
    finish = None
    response_id, model, created = "completion", parameters["model"], 0
    async with stream:
        async for chunk in stream:
            if on_chunk is not None:
                on_chunk(chunk)
            response_id, model, created = chunk.id, chunk.model, chunk.created
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if choice.finish_reason:
                finish = choice.finish_reason
            if choice.delta.content:
                content.append(choice.delta.content)
            for delta in choice.delta.tool_calls or []:
                call = calls.setdefault(delta.index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                if delta.id:
                    call["id"] = delta.id
                if delta.function:
                    call["function"]["name"] += delta.function.name or ""
                    call["function"]["arguments"] += delta.function.arguments or ""
    # A transport ending without a finish marker is not a completed model response.
    if finish is None:
        from fastapi import HTTPException
        raise HTTPException(502, "Model stream ended without completing its response")
    return ChatCompletion.model_validate({
        "id": response_id, "object": "chat.completion", "created": created, "model": model,
        "choices": [{"index": 0, "finish_reason": finish, "message": {
            "role": "assistant", "content": "".join(content),
            "tool_calls": [calls[index] for index in sorted(calls)] or None}}],
    })
