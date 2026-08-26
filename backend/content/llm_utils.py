def strip_code_fence(raw_response: str) -> str:
    """Strip a surrounding markdown code fence from an LLM response, if present.

    LLMs frequently wrap JSON in ```json ... ``` despite being told not to.
    """
    text = (raw_response or "").strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    lines = lines[1:]  # drop the opening ``` / ```json line
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
