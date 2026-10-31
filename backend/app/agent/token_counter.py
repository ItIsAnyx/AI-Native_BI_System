import json
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException

from app.config import settings
from app.agent.messages import normalize_messages


@lru_cache(maxsize=1)
def load_tokenizer(path: str):
    try:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        if not tokenizer.chat_template:
            raise ValueError("The tokenizer has no chat template")
        return tokenizer
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Cannot load the local tokenizer. Set TOKENIZER_PATH to the matching model's tokenizer directory.",
        ) from exc


def count_tokens(messages: list[dict], tools: list[dict] | None = None, continue_final_message: bool = False) -> int:
    path = settings.TOKENIZER_PATH
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    tokenizer = load_tokenizer(str(path.resolve()))
    formatted = []
    for message in normalize_messages(messages):
        item = dict(message)
        if item.get("tool_calls"):
            item["tool_calls"] = []
            for call in message["tool_calls"]:
                function = dict(call["function"])
                if isinstance(function["arguments"], str):
                    try:
                        function["arguments"] = json.loads(function["arguments"])
                    except json.JSONDecodeError:
                        pass
                item["tool_calls"].append({**call, "function": function})
        formatted.append(item)
    try:
        tokens = tokenizer.apply_chat_template(
            formatted, tools=tools or None, tokenize=True,
            add_generation_prompt=not continue_final_message,
            continue_final_message=continue_final_message, return_dict=False,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="The local chat template cannot format these messages or tools. Check TOKENIZER_PATH.",
        ) from exc
    return len(tokens)
