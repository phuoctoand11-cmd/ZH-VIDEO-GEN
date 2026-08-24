# zh-video-gen — Thiết kế

## Mục tiêu

Ứng dụng tạo video dạy tiếng Trung song ngữ Việt–Trung, chạy hoàn toàn miễn phí trên Google Colab (GPU T4 free tier), điều khiển qua giao diện Gradio. Mỗi video gồm các cảnh (scene) theo từ/câu tiếng Trung, mỗi cảnh có: ảnh minh họa do AI sinh (Ken Burns pan/zoom), chữ Hán + pinyin + nghĩa tiếng Việt hiển thị trên màn hình, và giọng đọc song ngữ theo trình tự cấu hình được.

## Phạm vi (v1)

- Input: danh sách từ/câu nhập tay (CSV/text) **hoặc** 1 prompt chủ đề để LLM tự soạn bài — cả hai được hỗ trợ, chọn theo từng lần tạo.
- Output: video mp4, chọn xuất 9:16, 16:9, hoặc cả hai.
- Chạy trong 1 Colab notebook duy nhất (Approach A — monolith), không cần hạ tầng deploy riêng.
- Không có CI; test chạy thủ công qua `pytest`.

## Kiến trúc

```
zh-video-gen/
  content/
    schema.py        # LessonItem: hanzi, pinyin, meaning_vi
    manual.py         # parse CSV/text nhập tay -> list[LessonItem]
    auto.py            # LLM: 1 topic prompt -> list[LessonItem]
    pinyin.py           # tự điền pinyin còn thiếu (pypinyin)
  audio/
    tts.py              # wrapper edge-tts: synth(text, lang) -> file audio
    templates.py        # đọc template trình tự audio (JSON)
  visuals/
    image.py            # wrapper diffusers (FLUX.1-schnell/SDXL-Turbo): prompt -> ảnh
    prompt_builder.py   # LessonItem -> prompt sinh ảnh
  render/
    kenburns.py          # ảnh tĩnh -> clip có pan/zoom
    overlay.py            # vẽ chữ Hán/pinyin/nghĩa đồng bộ audio
    assemble.py           # ghép các scene -> video hoàn chỉnh, theo tỉ lệ khung hình
  pipeline.py             # điều phối toàn bộ luồng
  app.py                  # Gradio UI
  config/templates/*.json # các template trình tự audio (vd zh-zh-vi, zh-vi-zh)
  notebook.ipynb           # entrypoint Colab: cài deps, mount Drive, chạy app.py
  tests/                   # unit test cho phần logic thuần
```

Mỗi module chỉ làm một việc, giao tiếp qua `LessonItem`/đường dẫn file — có thể test độc lập, và có thể thay TTS/model ảnh sau này mà không đụng phần khác.

### Công nghệ chọn (đều miễn phí)

- **Pinyin**: `pypinyin` — offline, không cần API.
- **TTS**: `edge-tts` — miễn phí, không cần key, có giọng Trung (`zh-CN-XiaoxiaoNeural`...) và giọng Việt (`vi-VN-HoaiMyNeural`...) trong cùng thư viện.
- **LLM soạn bài (auto mode)**: LLM free tier (Gemini/Groq free API) — trả JSON có schema validate bằng pydantic.
- **Ảnh AI**: FLUX.1-schnell hoặc SDXL-Turbo qua `diffusers`, chạy trên GPU T4 Colab free.
- **Dựng video**: `moviepy`/`ffmpeg`.
- **UI**: Gradio (chạy trong Colab, share link tạm).
- **Lưu trữ**: Google Drive mount (Colab session ephemeral, hết hạn ~12h).

## Data flow

1. Gradio UI nhận input (list thủ công hoặc topic prompt) + chọn template audio + chọn tỉ lệ khung hình.
2. `content/` tạo `list[LessonItem]` (auto mode gọi LLM soạn bài; `pinyin.py` tự điền pinyin thiếu).
3. Với từng `LessonItem`: `prompt_builder.py` tạo prompt ảnh → `image.py` sinh ảnh (cache theo hash prompt lên Drive).
4. `templates.py` đọc template đã chọn → `tts.py` sinh audio từng đoạn theo trình tự, lấy thời lượng.
5. `overlay.py` tính timing hiển thị chữ Hán/pinyin/nghĩa khớp từng đoạn audio.
6. `kenburns.py` tạo clip pan/zoom từ ảnh tĩnh, đủ độ dài theo tổng audio, theo tỉ lệ khung hình đã chọn.
7. `assemble.py` ghép các scene + audio thành video hoàn chỉnh, xuất riêng cho từng tỉ lệ đã chọn.
8. Gradio hiển thị preview + nút tải; file cũng lưu vào Drive.

## Xử lý lỗi

Nguyên tắc: một item lỗi không làm sập cả batch — xử lý từng item độc lập, gom lỗi báo cuối.

- Parse thủ công: dòng thiếu chữ Hán → bỏ qua, cảnh báo trong UI.
- LLM auto mode: validate JSON bằng pydantic; sai định dạng → retry 1 lần; vẫn sai → bỏ item.
- TTS: lỗi mạng → retry 2 lần có backoff; vẫn lỗi → bỏ scene, đánh dấu lỗi.
- Sinh ảnh: hết VRAM T4 → giảm resolution/step, thử lại 1 lần; vẫn lỗi → dùng ảnh placeholder (nền màu + chữ).
- Dựng video: lỗi ffmpeg → in log ra panel UI, giữ file tạm để debug.

## Testing

- Unit test (pytest), không cần GPU/mạng: parse CSV, điền pinyin, parse template, tính timing overlay, validate schema `LessonItem`.
- Smoke test tích hợp: pipeline với 1-2 từ thật, kiểm tra output mp4 hợp lệ qua `ffprobe`.
- Không có CI; chạy `pytest tests/` thủ công.
- Chất lượng thực tế (giọng đọc, ảnh có hợp nghĩa) kiểm tra thủ công bằng mắt/tai trên video output.

## Ngoài phạm vi (v1)

- UI/deploy bền vững ngoài Colab (Approach B) — cân nhắc sau nếu cần app chạy liên tục.
- Video AI chuyển động thật (text-to-video) thay ảnh tĩnh — quá nặng cho GPU free.
- Chỉnh sửa video sau khi tạo (timeline editor) — không có trong v1.
