import json
from typing import Callable

from pydantic import ValidationError

from content.auto import AutoGenerationError
from content.llm_utils import strip_code_fence
from content.schema import DialogueResult

PROMPT_TEMPLATE = (
    "Bạn là giáo viên tiếng Trung. Soạn 1 đoạn hội thoại tiếng Trung 6-8 lượt nói giữa 2 nhân "
    "vật, về chủ đề: \"{topic}\". Mỗi nhân vật có 1 tên tiếng Việt riêng, xưng hô tự nhiên. "
    "Mỗi lượt gồm 1 câu tiếng Trung ngắn tự nhiên, kèm pinyin và nghĩa tiếng Việt. "
    "Trả về CHỈ JSON theo đúng schema sau, không thêm giải thích:\n"
    '{{"title": "...", "turns": [{{"speaker_name": "...", "line": '
    '{{"hanzi": "...", "pinyin": "...", "meaning_vi": "..."}}}}]}}'
)


def generate_dialogue_topic(
    topic: str, llm_call: Callable[[str], str], max_retries: int = 1
) -> DialogueResult:
    prompt = PROMPT_TEMPLATE.format(topic=topic)
    last_error: Exception | None = None
    for _attempt in range(max_retries + 1):
        raw_response = llm_call(prompt)
        try:
            data = json.loads(strip_code_fence(raw_response))
            return DialogueResult(**data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
    raise AutoGenerationError(
        f"LLM returned invalid dialogue data after {max_retries + 1} attempts: {last_error}"
    )
