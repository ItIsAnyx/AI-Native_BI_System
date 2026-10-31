"""Keep trusted system guidance in the first message for local chat templates."""


def normalize_messages(messages):
    guidance=[]
    dialogue=[]
    for message in messages:
        if message["role"] == "system":
            content=message.get("content") or ""
            if not isinstance(content,str):
                raise ValueError("System guidance must be text")
            if content: guidance.append(content)
        else:
            dialogue.append(dict(message))
    return ([{"role":"system","content":"\n\n".join(guidance)}] if guidance else []) + dialogue
