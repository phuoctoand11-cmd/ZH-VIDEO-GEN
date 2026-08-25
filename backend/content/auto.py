import json
import os
from typing import Callable

from groq import Groq
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


# Groq's free tier needs no billing account, unlike Gemini's — which got
# auto-upgraded to a paid prepay tier the moment any Cloud billing account
# was linked anywhere under the same Google identity. GROQ_MODEL is
# overridable via env var so a future model retirement (as happened with
# gemini-2.0-flash) doesn't require a code change to fix.
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def groq_llm_call(prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise AutoGenerationError("GROQ_API_KEY environment variable is not set")
    client = Groq(api_key=api_key)
    model = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
