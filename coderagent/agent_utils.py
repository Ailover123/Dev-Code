# Converts LLM response content into plain text for parsing or cleaning.
def response_to_text(content) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))

        return "\n".join(parts).strip()

    return str(content).strip()
