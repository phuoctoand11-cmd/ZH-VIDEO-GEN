import json
from typing import Callable

from pydantic import ValidationError

from content.auto import AutoGenerationError
from content.llm_utils import strip_code_fence
from content.schema import VocabTopicResult

PROMPT_TEMPLATE = (
    "Bạn là giáo viên tiếng Trung. Chủ đề hoặc bộ thủ: \"{topic}\". "
    "Soạn đúng 5 từ tiếng Trung liên quan (nếu là 1 bộ thủ, chọn 5 từ có chứa bộ thủ đó). "
    "Với mỗi từ, viết icon_prompt là mô tả NGẮN BẰNG TIẾNG ANH cho 1 hình minh họa cảnh thực tế "
    "thể hiện ĐÚNG hành động/đồ vật/tình huống của từ đó (ví dụ từ \"đi làm\" (上班) → mô tả "
    "cảnh 1 người mặc vest bước ra cửa vẫy tay, có đồng hồ chỉ giờ sáng — không mô tả chung "
    "chung, không nhắc chữ Hán, không yêu cầu vẽ chữ trong ảnh). Mô tả phải đủ cụ thể để người "
    "xem nhận ra ngay đúng nghĩa của từ chỉ qua hình. "
    "Nếu topic là 1 bộ thủ cụ thể, điền radical (chính bộ thủ đó), radical_pinyin, "
    "radical_meaning_vi; nếu không, để 3 trường này là null. "
    "Trả về CHỈ JSON theo đúng schema sau, không thêm giải thích:\n"
    '{{"radical": "...", "radical_pinyin": "...", "radical_meaning_vi": "...", '
    '"items": [{{"hanzi": "...", "pinyin": "...", "meaning_vi": "...", "icon_prompt": "..."}}]}}'
)


def generate_vocab_topic(
    topic: str, llm_call: Callable[[str], str], max_retries: int = 1
) -> VocabTopicResult:
    prompt = PROMPT_TEMPLATE.format(topic=topic)
    last_error: Exception | None = None
    for _attempt in range(max_retries + 1):
        raw_response = llm_call(prompt)
        try:
            data = json.loads(strip_code_fence(raw_response))
            return VocabTopicResult(**data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
    raise AutoGenerationError(
        f"LLM returned invalid vocab topic data after {max_retries + 1} attempts: {last_error}"
    )
