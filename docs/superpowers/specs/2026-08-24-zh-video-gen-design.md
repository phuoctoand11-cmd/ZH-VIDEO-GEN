# zh-video-gen — Thiết kế

## Mục tiêu

Ứng dụng tạo video dạy tiếng Trung song ngữ Việt–Trung, deploy thật (có URL cố định, không phải chạy notebook thủ công), hoàn toàn miễn phí. Mỗi video gồm các cảnh (scene) theo từ/câu tiếng Trung, mỗi cảnh có: ảnh minh họa do AI sinh (Ken Burns pan/zoom), chữ Hán + pinyin + nghĩa tiếng Việt hiển thị trên màn hình, và giọng đọc song ngữ theo trình tự cấu hình được.

## Phạm vi (v1)

- Input: danh sách từ/câu nhập tay (CSV/text) **hoặc** 1 prompt chủ đề để LLM tự soạn bài — cả hai được hỗ trợ, chọn theo từng lần tạo.
- Output: video mp4, chọn xuất 9:16, 16:9, hoặc cả hai. Trả trực tiếp cho người dùng tải về (không lưu trữ lâu dài trong v1).
- Deploy: frontend trên Cloudflare Pages, backend xử lý trên Hugging Face Spaces (ZeroGPU).
- Không có CI; test chạy thủ công qua `pytest`.

## Kiến trúc

Hai phần triển khai riêng, giao tiếp qua Gradio API:

```
zh-video-gen/
  backend/                    # deploy lên Hugging Face Spaces
    content/
      schema.py        # LessonItem: hanzi, pinyin, meaning_vi
      manual.py         # parse CSV/text nhập tay -> list[LessonItem]
      auto.py            # LLM: 1 topic prompt -> list[LessonItem]
      pinyin.py           # tự điền pinyin còn thiếu (pypinyin)
    audio/
      tts.py              # wrapper edge-tts: synth(text, lang) -> file audio
      templates.py        # đọc template trình tự audio (JSON)
    visuals/
      image.py            # wrapper diffusers (FLUX.1-schnell/SDXL-Turbo), decorator @spaces.GPU (ZeroGPU)
      prompt_builder.py   # LessonItem -> prompt sinh ảnh
    render/
      kenburns.py          # ảnh tĩnh -> clip có pan/zoom
      overlay.py            # vẽ chữ Hán/pinyin/nghĩa đồng bộ audio
      assemble.py           # ghép các scene -> video hoàn chỉnh, theo tỉ lệ khung hình
    pipeline.py             # điều phối toàn bộ luồng
    app.py                  # Gradio app — vừa là UI dự phòng, vừa expose API cho frontend gọi
    config/templates/*.json # các template trình tự audio (vd zh-zh-vi, zh-vi-zh)
    requirements.txt
    README.md                # metadata Space (SDK: gradio, hardware: zero-gpu)
    tests/                   # unit test cho phần logic thuần
  frontend/                   # deploy lên Cloudflare Pages
    index.html / src/         # form nhập liệu, chọn template, chọn tỉ lệ khung hình
    (gọi backend qua @gradio/client tới URL HF Space)
```

Mỗi module backend chỉ làm một việc, giao tiếp qua `LessonItem`/đường dẫn file — có thể test độc lập, và có thể thay TTS/model ảnh sau này mà không đụng phần khác. Logic xử lý (content/audio/visuals/render) không đổi so với thiết kế ban đầu — chỉ đổi nơi chạy và cách frontend/backend giao tiếp.

### Công nghệ chọn (đều miễn phí)

- **Pinyin**: `pypinyin` — offline, không cần API.
- **TTS**: `edge-tts` — miễn phí, không cần key, có giọng Trung (`zh-CN-XiaoxiaoNeural`...) và giọng Việt (`vi-VN-HoaiMyNeural`...) trong cùng thư viện.
- **LLM soạn bài (auto mode)**: LLM free tier (Gemini/Groq free API) — trả JSON có schema validate bằng pydantic.
- **Ảnh AI**: FLUX.1-schnell hoặc SDXL-Turbo qua `diffusers`, chạy trên **ZeroGPU** của HF Spaces (GPU cấp phát tạm thời theo request, miễn phí trong quota chia sẻ).
- **Dựng video**: `moviepy`/`ffmpeg` — chạy trên CPU của Space.
- **Backend hosting**: Hugging Face Spaces (Gradio SDK) — chạy thường trực, sleep khi không có traffic, tự thức khi có request tới.
- **Frontend hosting**: Cloudflare Pages — site tĩnh, build/deploy tự động khi push GitHub.
- **Giao tiếp frontend↔backend**: `@gradio/client` (JS) gọi API của HF Space từ trình duyệt.
- **Lưu trữ**: không có trong v1 — video trả thẳng cho người dùng tải ngay sau khi tạo xong.

## Data flow

1. Người dùng mở frontend (Cloudflare Pages), nhập input (list thủ công hoặc topic prompt) + chọn template audio + chọn tỉ lệ khung hình.
2. Frontend gọi API của HF Space (qua `@gradio/client`) để kích hoạt pipeline, kèm tham số đã chọn.
3. Backend: `content/` tạo `list[LessonItem]` (auto mode gọi LLM soạn bài; `pinyin.py` tự điền pinyin thiếu).
4. Với từng `LessonItem`: `prompt_builder.py` tạo prompt ảnh → `image.py` sinh ảnh (hàm GPU decorate bằng `@spaces.GPU`, cache theo hash prompt trong bộ nhớ phiên chạy).
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
- Sinh ảnh: hết quota ZeroGPU hoặc lỗi khi generate → giảm resolution/step, thử lại 1 lần; vẫn lỗi → dùng ảnh placeholder (nền màu + chữ).
- Dựng video: lỗi ffmpeg → trả log lỗi trong response cho frontend hiển thị.
- Frontend↔backend: Space đang "ngủ" (cold start) → frontend hiển thị trạng thái "đang khởi động server, vui lòng đợi" thay vì lỗi im lặng; timeout dài hơn bình thường cho request đầu tiên.

## Testing

- Unit test (pytest) cho backend, không cần GPU/mạng: parse CSV, điền pinyin, parse template, tính timing overlay, validate schema `LessonItem`.
- Smoke test tích hợp: pipeline với 1-2 từ thật, kiểm tra output mp4 hợp lệ qua `ffprobe`.
- Kiểm tra thủ công frontend↔backend: gọi thử API từ frontend đã deploy, xác nhận nhận được video.
- Không có CI; chạy `pytest tests/` thủ công.
- Chất lượng thực tế (giọng đọc, ảnh có hợp nghĩa) kiểm tra thủ công bằng mắt/tai trên video output.

## Deploy

- **Backend**: push thư mục `backend/` lên GitHub, kết nối HF Space với repo GitHub (auto-sync) hoặc `git push` trực tiếp lên remote của HF Space. Cấu hình `README.md` với metadata `sdk: gradio`, `hardware: zero-gpu` (theo yêu cầu HF Spaces).
- **Frontend**: push thư mục `frontend/` lên GitHub, kết nối Cloudflare Pages với repo (build command tùy công nghệ chọn), tự deploy khi có commit mới. Cần cấu hình URL của HF Space (biến môi trường/config) để frontend biết gọi API tới đâu.
- Repo GitHub là 1 monorepo chứa cả `backend/` và `frontend/`; mỗi nền tảng deploy (HF Spaces, Cloudflare Pages) chỉ theo dõi thư mục con tương ứng.

## Ngoài phạm vi (v1)

- Lưu trữ lâu dài video đã tạo (vd Cloudflare R2) — thêm sau nếu cần lịch sử/thư viện video.
- Video AI chuyển động thật (text-to-video) thay ảnh tĩnh — quá nặng cho GPU free.
- Chỉnh sửa video sau khi tạo (timeline editor) — không có trong v1.
- Tài khoản người dùng / đa người dùng đồng thời có hàng đợi riêng — v1 dùng chung 1 Space, xử lý tuần tự theo hàng đợi mặc định của Gradio.
