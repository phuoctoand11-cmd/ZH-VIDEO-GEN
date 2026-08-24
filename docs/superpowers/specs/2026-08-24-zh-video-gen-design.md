# zh-video-gen — Thiết kế

## Mục tiêu

Ứng dụng tạo video dạy tiếng Trung song ngữ Việt–Trung, deploy thật (có URL cố định, không phải chạy notebook thủ công), hoàn toàn miễn phí. Mỗi video gồm các cảnh (scene) theo từ/câu tiếng Trung, mỗi cảnh có: ảnh minh họa do AI sinh (Ken Burns pan/zoom), chữ Hán + pinyin + nghĩa tiếng Việt hiển thị trên màn hình, và giọng đọc song ngữ theo trình tự cấu hình được.

## Phạm vi (v1)

- Input: danh sách từ/câu nhập tay (CSV/text) **hoặc** 1 prompt chủ đề để LLM tự soạn bài — cả hai được hỗ trợ, chọn theo từng lần tạo.
- Output: video mp4, chọn xuất 9:16, 16:9, hoặc cả hai. Trả trực tiếp cho người dùng tải về (không lưu trữ lâu dài trong v1).
- Deploy: frontend trên Cloudflare Pages, backend xử lý trên Render.com (Docker web service).
- Không có CI; test chạy thủ công qua `pytest`.

## Kiến trúc

Hai phần triển khai riêng, giao tiếp qua Gradio API:

```
zh-video-gen/
  backend/                    # deploy lên Render.com (Docker web service)
    content/
      schema.py        # LessonItem: hanzi, pinyin, meaning_vi
      manual.py         # parse CSV/text nhập tay -> list[LessonItem]
      auto.py            # LLM: 1 topic prompt -> list[LessonItem]
      pinyin.py           # tự điền pinyin còn thiếu (pypinyin)
    audio/
      tts.py              # wrapper edge-tts: synth(text, lang) -> file audio
      templates.py        # đọc template trình tự audio (JSON)
    visuals/
      image.py            # gọi Hugging Face Inference API (FLUX.1-schnell) qua huggingface_hub.InferenceClient
      prompt_builder.py   # LessonItem -> prompt sinh ảnh
    render/
      kenburns.py          # ảnh tĩnh -> clip có pan/zoom
      overlay.py            # vẽ chữ Hán/pinyin/nghĩa đồng bộ audio
      assemble.py           # ghép các scene -> video hoàn chỉnh, theo tỉ lệ khung hình
    pipeline.py             # điều phối toàn bộ luồng
    app.py                  # Gradio app — vừa là UI dự phòng, vừa expose API cho frontend gọi
    config/templates/*.json # các template trình tự audio (vd zh-zh-vi, zh-vi-zh)
    Dockerfile               # cài ffmpeg + Python deps, chạy app.py — Render build từ đây
    requirements.txt
    README.md                # hướng dẫn deploy Render.com + biến môi trường cần thiết
    tests/                   # unit test cho phần logic thuần
  frontend/                   # deploy lên Cloudflare Pages
    index.html / src/         # form nhập liệu, chọn template, chọn tỉ lệ khung hình
    (gọi backend qua @gradio/client tới URL Render)
```

Mỗi module backend chỉ làm một việc, giao tiếp qua `LessonItem`/đường dẫn file — có thể test độc lập, và có thể thay TTS/model ảnh sau này mà không đụng phần khác. Logic xử lý (content/audio/visuals/render) không đổi so với thiết kế ban đầu — chỉ đổi nơi chạy và cách frontend/backend giao tiếp.

### Công nghệ chọn (đều miễn phí)

- **Pinyin**: `pypinyin` — offline, không cần API.
- **TTS**: `edge-tts` — miễn phí, không cần key, có giọng Trung (`zh-CN-XiaoxiaoNeural`...) và giọng Việt (`vi-VN-HoaiMyNeural`...) trong cùng thư viện.
- **LLM soạn bài (auto mode)**: LLM free tier (Gemini/Groq free API) — trả JSON có schema validate bằng pydantic.
- **Ảnh AI**: FLUX.1-schnell qua **Hugging Face Inference API** (`huggingface_hub.InferenceClient.text_to_image`, xác thực bằng `HF_TOKEN`) — không tự host model, không cần GPU riêng, miễn phí trong quota chia sẻ của HF. (Đã đổi từ phương án ban đầu — tự host model qua `diffusers` trên ZeroGPU — vì tài khoản HF cần thêm billing/credit mới mở khóa được Gradio SDK trên Spaces.)
- **Dựng video**: `moviepy`/`ffmpeg` — chạy trên CPU của backend, cài qua `Dockerfile`.
- **Backend hosting**: Render.com (Docker web service, free tier) — sleep khi không có traffic, tự thức khi có request tới, tương tự trải nghiệm HF Spaces.
- **Frontend hosting**: Cloudflare Pages — site tĩnh, build/deploy tự động khi push GitHub.
- **Giao tiếp frontend↔backend**: `@gradio/client` (JS) gọi API của backend Render từ trình duyệt.
- **Lưu trữ**: không có trong v1 — video trả thẳng cho người dùng tải ngay sau khi tạo xong.

## Data flow

1. Người dùng mở frontend (Cloudflare Pages), nhập input (list thủ công hoặc topic prompt) + chọn template audio + chọn tỉ lệ khung hình.
2. Frontend gọi API của backend (qua `@gradio/client`) để kích hoạt pipeline, kèm tham số đã chọn.
3. Backend: `content/` tạo `list[LessonItem]` (auto mode gọi LLM soạn bài; `pinyin.py` tự điền pinyin thiếu).
4. Với từng `LessonItem`: `prompt_builder.py` tạo prompt ảnh → `image.py` gọi HF Inference API sinh ảnh (cache theo hash prompt trong bộ nhớ phiên chạy).
5. `templates.py` đọc template đã chọn → `tts.py` sinh audio từng đoạn theo trình tự, lấy thời lượng.
6. `overlay.py` tính timing hiển thị chữ Hán/pinyin/nghĩa khớp từng đoạn audio.
7. `kenburns.py` tạo clip pan/zoom từ ảnh tĩnh, đủ độ dài theo tổng audio, theo tỉ lệ khung hình đã chọn.
8. `assemble.py` ghép các scene + audio thành video hoàn chỉnh, xuất riêng cho từng tỉ lệ đã chọn.
9. Backend trả file video qua Gradio API response; frontend hiển thị preview + nút tải trực tiếp từ trình duyệt.

## Xử lý lỗi

Nguyên tắc: một item lỗi không làm sập cả batch — xử lý từng item độc lập, gom lỗi báo cuối.

- Parse thủ công: dòng thiếu chữ Hán → bỏ qua, cảnh báo trả về frontend.
- LLM auto mode: validate JSON bằng pydantic; sai định dạng → retry 1 lần; vẫn sai → bỏ item.
- TTS: lỗi mạng → retry 2 lần có backoff; vẫn lỗi → bỏ scene, đánh dấu lỗi.
- Sinh ảnh: HF Inference API lỗi/timeout (hoặc thiếu `HF_TOKEN`) → giảm resolution/step, thử lại 1 lần; vẫn lỗi → dùng ảnh placeholder (nền màu + chữ).
- Dựng video: lỗi ffmpeg → trả log lỗi trong response cho frontend hiển thị.
- Frontend↔backend: backend đang "ngủ" (Render free tier, cold start) → frontend hiển thị trạng thái "đang khởi động server, vui lòng đợi" thay vì lỗi im lặng; timeout dài hơn bình thường cho request đầu tiên.

## Testing

- Unit test (pytest) cho backend, không cần GPU/mạng: parse CSV, điền pinyin, parse template, tính timing overlay, validate schema `LessonItem`.
- Smoke test tích hợp: pipeline với 1-2 từ thật, kiểm tra output mp4 hợp lệ qua `ffprobe`.
- Kiểm tra thủ công frontend↔backend: gọi thử API từ frontend đã deploy, xác nhận nhận được video.
- Không có CI; chạy `pytest tests/` thủ công.
- Chất lượng thực tế (giọng đọc, ảnh có hợp nghĩa) kiểm tra thủ công bằng mắt/tai trên video output.

## Deploy

- **Backend**: push thư mục `backend/` lên GitHub, tạo Web Service trên Render.com kết nối repo, Root Directory = `backend`, runtime Docker (Render tự nhận `Dockerfile`). Cấu hình biến môi trường `GEMINI_API_KEY` và `HF_TOKEN` trong Settings → Environment.
- **Frontend**: push thư mục `frontend/` lên GitHub, kết nối Cloudflare Pages với repo (không cần build command), tự deploy khi có commit mới. Cần cấu hình URL của backend Render (`frontend/js/config.js`) để frontend biết gọi API tới đâu.
- Repo GitHub là 1 monorepo chứa cả `backend/` và `frontend/`; mỗi nền tảng deploy (Render, Cloudflare Pages) chỉ theo dõi thư mục con tương ứng.

## Ngoài phạm vi (v1)

- Lưu trữ lâu dài video đã tạo (vd Cloudflare R2) — thêm sau nếu cần lịch sử/thư viện video.
- Video AI chuyển động thật (text-to-video) thay ảnh tĩnh — quá nặng cho GPU free.
- Chỉnh sửa video sau khi tạo (timeline editor) — không có trong v1.
- Tài khoản người dùng / đa người dùng đồng thời có hàng đợi riêng — v1 dùng chung 1 Space, xử lý tuần tự theo hàng đợi mặc định của Gradio.
