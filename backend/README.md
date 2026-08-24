# zh-video-gen backend

Backend tạo video dạy tiếng Trung song ngữ Việt-Trung: soạn nội dung (thủ công hoặc Gemini), tổng hợp giọng đọc (edge-tts), sinh ảnh minh họa qua [Hugging Face Inference API](https://huggingface.co/docs/inference-providers) (không tự host model), rồi ghép video bằng moviepy/ffmpeg. Expose qua Gradio app (`app.py`), deploy trên [Render.com](https://render.com).

Xem thiết kế đầy đủ tại `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md` trong repo chính.

## Deploy lên Render.com

1. Tạo **Web Service** mới trên Render, kết nối repo GitHub này.
2. **Root Directory**: `backend`
3. **Runtime**: Docker (Render tự nhận diện `Dockerfile` trong root directory đã chọn).
4. **Environment Variables** (Settings → Environment):
   - `GEMINI_API_KEY` — key free tier từ [aistudio.google.com/apikey](https://aistudio.google.com/apikey), dùng cho chế độ "chủ đề tự động".
   - `HF_TOKEN` — access token (quyền **Read**) tạo tại [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens), dùng để gọi Inference API sinh ảnh.
5. Deploy. Render sẽ build image từ `Dockerfile`, cài ffmpeg + dependencies, rồi chạy `python app.py` — app tự lắng nghe cổng Render cấp qua biến `$PORT`.

## Chạy local

```bash
cd backend
pip install -r requirements.txt
export GEMINI_API_KEY=...   # chỉ cần cho chế độ chủ đề tự động
export HF_TOKEN=...          # bắt buộc để sinh ảnh
python app.py
```

## Test

```bash
cd backend
pytest -v
```

Cần `ffmpeg`/`ffprobe` có sẵn trên PATH (dùng cho fixture audio của một vài test).
