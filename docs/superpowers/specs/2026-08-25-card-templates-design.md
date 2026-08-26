# zh-video-gen — Card templates (từ vựng theo chủ đề / hội thoại theo chủ đề) — Thiết kế

## Mục tiêu

Thay thế toàn bộ kiểu ảnh nền "AI sinh ảnh chụp + Ken Burns pan + chữ vẽ đè lên trên mỗi frame" bằng một hệ thống **card thiết kế sẵn** (bố cục cố định, chữ vẽ chính xác 1 lần bằng code, chỉ phần minh họa/mascot là do AI sinh) — giống tinh thần các mẫu card học từ vựng/hội thoại nhiều màu, có mascot dễ thương, số thứ tự, bo tròn.

Lý do đổi cách làm: mô hình sinh ảnh (kể cả FLUX.1-schnell đang dùng) không đáng tin cậy khi phải vẽ chữ Hán/pinyin nhúng trực tiếp vào ảnh — chữ thường bị méo/sai nét. Với app học tiếng Trung, chữ sai là không chấp nhận được, nên toàn bộ text phải do code vẽ.

## Phạm vi

Ứng dụng có 3 chế độ nhập liệu (menu), tất cả xuất video theo hệ thống card mới:

1. **Nhập danh sách** (giữ lại) — người dùng tự nhập CSV `hanzi,pinyin,meaning_vi`. Xuất ra **card danh sách nhiều dòng**, không có tiêu đề bộ thủ.
2. **Từ vựng theo chủ đề** (mới) — người dùng nhập 1 chủ đề/bộ thủ. Groq soạn đúng 5 từ liên quan. Xuất ra **card danh sách 5 dòng có tiêu đề bộ thủ**.
3. **Hội thoại theo chủ đề** (mới) — người dùng nhập 1 chủ đề. Groq soạn đoạn hội thoại 6-8 lượt giữa 2 nhân vật. Xuất ra **video nhiều scene, mỗi lượt thoại 1 scene dạng card hội thoại**.

Bỏ hẳn chế độ "Chủ đề tự động" kiểu cũ (Ken Burns + Gemini/Groq soạn 8-12 từ rời rạc, không có card).

Không đổi: TTS (`edge-tts`), template trình tự audio (`zh-vi-zh`/`zh-zh-vi`), lựa chọn tỉ lệ khung hình, hosting, backend API surface (`generate_video`), cách merge lỗi từng phần vào 1 batch.

## Kiến trúc

### Nguyên tắc cốt lõi

**Text luôn do code vẽ 1 lần vào ảnh card tĩnh (Pillow), AI chỉ sinh phần minh họa không chứa chữ** (mascot, avatar nhân vật — phong cách sticker/chibi, nền đơn giản). Ảnh card tĩnh sau đó được Ken Burns pan/zoom như ảnh chụp trước đây — khác biệt duy nhất: nguồn ảnh giờ là card tự vẽ, không phải ảnh AI, và với card danh sách, điểm zoom di chuyển lần lượt qua từng dòng thay vì zoom cố định vào giữa ảnh.

Hệ quả kiến trúc quan trọng: **`render/overlay.py` (vẽ text đè lên từng frame) không còn được dùng bởi bất kỳ chế độ nào sau thay đổi này** — vì mọi text giờ đã nằm sẵn trong card. Xóa module này khỏi pipeline (không xóa file ngay, đánh dấu unused, xóa hẳn nếu review thấy an toàn).

### Module mới

```
backend/
  content/
    schema.py            # + VocabCardItem, VocabTopicResult, DialogueTurn, DialogueResult
    vocab_topic.py        # MỚI: generate_vocab_topic(topic, llm_call) -> VocabTopicResult
    dialogue_topic.py     # MỚI: generate_dialogue_topic(topic, llm_call) -> DialogueResult
  visuals/
    prompt_builder.py     # + build_mascot_prompt(icon_prompt), build_avatar_prompt(speaker_name, hint)
    image.py               # không đổi interface — generate_image() dùng lại nguyên cho mascot/avatar
  render/
    theme.py               # MỚI: bảng màu pastel cố định (cycle theo dòng/lượt), đường dẫn font
    vocab_card.py           # MỚI: draw_vocab_card(...) -> PIL.Image, row_regions(...) -> list[Region]
    dialogue_card.py        # MỚI: draw_dialogue_turn(...) -> PIL.Image
    highlight.py             # MỚI: make_highlight_clip(...) -> VideoClip (Ken Burns zoom theo từng dòng)
    kenburns.py               # không đổi — tái dùng nguyên cho scene hội thoại
    assemble.py                # + build_static_scene_clip(...) (Ken Burns + audio, KHÔNG overlay text)
                                # assemble_video() không đổi (vẫn nối nhiều scene)
    overlay.py                  # không còn được gọi bởi pipeline mới — giữ file, dọn ở review cuối
  pipeline.py             # + run_vocab_card_pipeline(...), run_dialogue_pipeline(...)
  app.py                  # đổi UI: 3 mode, route sang pipeline tương ứng
```

### Data model mới (`content/schema.py`)

```python
class VocabCardItem(BaseModel):
    hanzi: str
    pinyin: str | None = None
    meaning_vi: str
    icon_prompt: str  # mô tả ngắn TIẾNG ANH để sinh mascot, vd "cute ice cube character"

class VocabTopicResult(BaseModel):
    radical: str | None = None            # None khi dùng cho chế độ "Nhập danh sách"
    radical_pinyin: str | None = None
    radical_meaning_vi: str | None = None
    items: list[VocabCardItem]            # 5 mục (chế độ chủ đề) hoặc N mục (nhập danh sách)

class DialogueTurn(BaseModel):
    speaker_name: str
    line: LessonItem                       # hanzi/pinyin/meaning_vi của câu thoại này

class DialogueResult(BaseModel):
    title: str
    turns: list[DialogueTurn]
```

`LessonItem` (đã có sẵn) giữ nguyên, dùng để tái sử dụng toàn bộ hạ tầng TTS/template hiện có cho từng dòng/lượt thoại.

## Data flow

### Chế độ "Từ vựng theo chủ đề"

1. `content/vocab_topic.py::generate_vocab_topic(topic, groq_llm_call)` — prompt Groq soạn đúng 5 từ liên quan tới chủ đề/bộ thủ, trả JSON đúng schema `VocabTopicResult` (bao gồm `icon_prompt` tiếng Anh cho từng từ). Validate bằng pydantic, retry 1 lần nếu JSON sai — dùng lại cơ chế strip-code-fence + retry đã có trong `content/auto.py`.
2. `content/pinyin.py::fill_pinyin_batch` — điền pinyin còn thiếu (tái dùng nguyên).
3. Với mỗi `VocabCardItem`: `visuals/prompt_builder.py::build_mascot_prompt(item.icon_prompt)` → `visuals/image.py::generate_image(...)` sinh 1 ảnh mascot vuông nhỏ (phong cách sticker/chibi, không chữ). Lỗi sinh ảnh → dùng `make_placeholder_image` sẵn có (không làm hỏng cả card).
4. Với mỗi dòng: `audio/tts.py::synthesize` đọc theo `template.segments` (dùng lại nguyên `AudioTemplate`/`template_name` người dùng chọn), tính tổng thời lượng của dòng đó. Lỗi TTS 1 dòng → dùng audio im lặng độ dài mặc định (2s) thay thế, ghi cảnh báo vào log, KHÔNG bỏ dòng (card cố định 5 dòng, bỏ dòng làm lệch layout).
5. `render/vocab_card.py::draw_vocab_card(result, mascot_paths, size)` — vẽ 1 ảnh card tĩnh đầy đủ: banner tiêu đề bộ thủ (nếu có) trên cùng, N dòng (số thứ tự + hanzi + pinyin + nghĩa + mascot), màu nền mỗi dòng cycle theo bảng màu `render/theme.py`.
6. `render/vocab_card.py::row_regions(size, n_items)` — trả về vùng (y-center, height) từng dòng trên card, dùng làm điểm neo zoom.
7. Nối toàn bộ audio các dòng thành 1 track (`concatenate_audioclips`, tái dùng nguyên cơ chế đã có trong `render/assemble.py::build_scene_clip`).
8. `render/highlight.py::make_highlight_clip(card_image, regions, durations, size)` — Ken Burns zoom lần lượt vào từng dòng theo đúng thời lượng audio dòng đó, gắn audio track đã nối.
9. Ghi video trực tiếp bằng `write_videofile` (không cần `assemble_video`/nối nhiều scene — cả video vốn đã là 1 clip liên tục).

### Chế độ "Nhập danh sách"

Giống hệt flow trên từ bước 2, chỉ khác: `VocabTopicResult` được dựng trực tiếp từ CSV người dùng nhập (không gọi LLM, `radical=None`), và `icon_prompt` cho mascot được suy ra tự động từ `meaning_vi` (không có sẵn từ LLM) — dùng `meaning_vi` làm `icon_prompt` luôn (đơn giản, chấp nhận mascot kém liên quan hơn chế độ AI-soạn).

### Chế độ "Hội thoại theo chủ đề"

1. `content/dialogue_topic.py::generate_dialogue_topic(topic, groq_llm_call)` — prompt Groq soạn tiêu đề + 6-8 lượt thoại giữa 2 nhân vật có tên, trả JSON đúng schema `DialogueResult`. Cùng cơ chế validate/retry như trên.
2. `fill_pinyin_batch` áp dụng lên `line` của từng lượt (coi mỗi lượt như 1 `LessonItem`).
3. Với mỗi nhân vật xuất hiện (thường 2): sinh avatar 1 lần (`build_avatar_prompt` + `generate_image`), tái dùng cho mọi lượt của nhân vật đó (không sinh lại mỗi lượt).
4. Với mỗi lượt: `render/dialogue_card.py::draw_dialogue_turn(turn, avatar_path, accent_color, size)` vẽ 1 ảnh scene đầy đủ (avatar + tên + hanzi + pinyin + nghĩa), màu accent theo nhân vật.
5. TTS đọc theo `template.segments` áp lên `turn.line` — **tái dùng nguyên `audio/tts.py` + `AudioTemplate`**.
6. `render/assemble.py::build_static_scene_clip(dialogue_card_image, audio_paths, aspect_ratio)` — Ken Burns pan (tái dùng `render/kenburns.py` không đổi) + gắn audio, **không gọi overlay** (text đã nằm trong ảnh).
7. `render/assemble.py::assemble_video(scene_clips, out_path)` — nối các scene lượt thoại thành video hoàn chỉnh (tái dùng nguyên, không đổi).

Lỗi 1 lượt thoại (TTS/render fail) → bỏ lượt đó, gom lỗi báo cuối, giống nguyên tắc "1 item lỗi không sập batch" hiện có.

## Thiết kế thị giác (`render/theme.py`)

- Bảng màu pastel cố định, cycle theo dòng/lượt: hồng, xanh dương nhạt, xanh lá nhạt, cam nhạt, tím nhạt (5 màu, khớp cảm giác ảnh mẫu).
- Font: `assets/fonts/NotoSansCJKsc-Regular.otf` (đã có) cho hanzi. Thêm 1 font tròn/vui cho pinyin + tiếng Việt + số thứ tự — chọn từ Google Fonts (license OFL, tải về bundle trong repo, ví dụ **Baloo 2** — hỗ trợ tốt dấu tiếng Việt).
- Trang trí (sao, tim, viền bo tròn) vẽ bằng hình học Pillow (`rounded_rectangle`, `ellipse`) — không dùng SVG/asset ngoài phức tạp như ảnh mẫu, giữ đơn giản để dễ bảo trì.
- Kích thước card khớp `ASPECT_SIZES` hiện có (`render/assemble.py`), chừa margin an toàn quanh vùng bị Ken Burns crop để text không bao giờ bị cắt mất trong lúc zoom.

## Xử lý lỗi

- LLM soạn từ vựng/hội thoại: validate JSON bằng pydantic; sai định dạng → retry 1 lần; vẫn sai → báo lỗi rõ ràng, không tạo video (tái dùng nguyên `AutoGenerationError`).
- Sinh mascot/avatar: dùng lại nguyên cơ chế fallback placeholder + timeout 60s đã có trong `visuals/image.py`.
- TTS 1 dòng (card danh sách): thay bằng audio im lặng, không bỏ dòng.
- TTS 1 lượt (hội thoại): bỏ lượt, báo lỗi, tiếp tục các lượt khác.
- Dựng video: lỗi ffmpeg → trả log lỗi trong response, giống hiện tại.

## Testing

- `content/vocab_topic.py`, `content/dialogue_topic.py`: unit test với `llm_call` giả, theo đúng mẫu đã có ở `tests/content/test_auto.py` (JSON hợp lệ, retry khi JSON sai, JSON có code fence, raise sau khi hết retry).
- `render/vocab_card.py`: test `draw_vocab_card` trả về `Image` đúng kích thước; `row_regions` trả về đúng N vùng, không chồng lấn, theo đúng thứ tự trên xuống.
- `render/dialogue_card.py`: test `draw_dialogue_turn` trả về `Image` đúng kích thước.
- `render/highlight.py`: test `make_highlight_clip` trả về `VideoClip` có `duration` đúng bằng tổng các `durations` truyền vào; test 1 frame lấy mẫu tại giữa mỗi vùng có kích thước đúng target size.
- `render/assemble.py::build_static_scene_clip`: test tương tự `build_scene_clip` hiện có nhưng xác nhận không gọi `overlay.draw_text_on_frame` (frame trả về khớp Ken Burns thuần, không bị vẽ đè).
- `pipeline.py`: test tích hợp `run_vocab_card_pipeline`/`run_dialogue_pipeline` với 1-2 mục thật, kiểm tra output mp4 hợp lệ — theo đúng mẫu `tests/render/test_assemble.py` hiện có (cần `ffmpeg`/`ffprobe` trên PATH).
- `visuals/prompt_builder.py`: test `build_mascot_prompt`/`build_avatar_prompt` trả về chuỗi chứa `icon_prompt`/tên nhân vật, không chứa yêu cầu vẽ chữ.

## Ngoài phạm vi (giai đoạn này)

- Animation mượt giữa các dòng khi zoom (dùng hard-cut zoom tĩnh từng dòng cho v1, chưa làm easing/transition mượt).
- Cho người dùng tùy chỉnh bảng màu/font.
- Card hội thoại nhiều hơn 2 nhân vật.
- Asset trang trí phức tạp (sticker SVG, hiệu ứng như ảnh mẫu Canva) — chỉ vẽ hình học đơn giản.
