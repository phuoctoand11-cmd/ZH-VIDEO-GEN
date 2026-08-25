import json
import os
from typing import Callable

from pydantic import BaseModel, ValidationError

from content.schema import LessonItem


class AutoGenerationError(Exception):
    pass


class _RawItem(BaseModel):
    hanzi: str
    pinyin: str | None = None
    meaning_vi: str


class _RawLesson(BaseModel):
    items: list[_RawItem]


PROMPT_TEMPLATE = (
    "Bạn là giáo viên tiếng Trung. Soạn danh sách 8-12 từ vựng hoặc câu tiếng Trung "
    "về chủ đề: \"{topic}\". Trả về CHỈ JSON theo đúng schema sau, không thêm giải thích:\n"
    '{{"items": [{{"hanzi": "...", "pinyin": "...", "meaning_vi": "..."}}]}}'
)


def _strip_code_fence(raw_response: str) -> str:
    """Strip a surrounding markdown code fence from an LLM response, if present.

    Gemini frequently wraps JSON in ```json ... ``` despite being told not to.
    """
    text = (raw_response or "").strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    lines = lines[1:]  # drop the opening ``` / ```json line
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def generate_lesson(
    topic: str, llm_call: Callable[[str], str], max_retries: int = 1
) -> list[LessonItem]:
    prompt = PROMPT_TEMPLATE.format(topic=topic)
    last_error: Exception | None = None
    for _attempt in range(max_retries + 1):
        raw_response = llm_call(prompt)
        try:
            data = json.loads(_strip_code_fence(raw_response))
            parsed = _RawLesson(**data)
            return [
                LessonItem(hanzi=i.hanzi, pinyin=i.pinyin, meaning_vi=i.meaning_vi)
                for i in parsed.items
            ]
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
    raise AutoGenerationError(
        f"LLM returned invalid lesson data after {max_retries + 1} attempts: {last_error}"
    )


def gemini_llm_call(prompt: str) -> str:
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise AutoGenerationError("GEMINI_API_KEY environment variable is not set")
    genai.configure(api_key=api_key)
    # gemini-2.0-flash was retired; confirmed live via the Gemini API's own
    # 404 error, which names gemini-3.6-flash as its replacement.
    model = genai.GenerativeModel("gemini-3.6-flash")
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )
    return response.text
