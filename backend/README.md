# zh-video-gen backend

Backend tạo video dạy tiếng Trung song ngữ Việt-Trung, hỗ trợ 3 chế độ: **Nhập danh sách** (từ vựng tự nhập thủ công), **Từ vựng theo chủ đề** (tự soạn qua [Groq](https://console.groq.com) từ một chủ đề), và **Hội thoại theo chủ đề** (đoạn hội thoại 2 nhân vật, cũng tự soạn qua Groq). Video dùng card thiết kế sẵn theo template — chữ Hán/pinyin/nghĩa do code vẽ trực tiếp lên card (không phải overlay AI), AI qua [Hugging Face Inference API](https://huggingface.co/docs/inference-providers) (không tự host model) chỉ sinh ảnh mascot (chế độ từ vựng) hoặc avatar nhân vật (chế độ hội thoại), rồi ghép thành video bằng moviepy/ffmpeg kèm hiệu ứng zoom-highlight theo từng dòng/lượt thoại. Expose qua Gradio app (`app.py`), deploy trên [Google Cloud Run](https://cloud.google.com/run).

Xem thiết kế đầy đủ tại `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md` trong repo chính.

## Deploy lên Google Cloud Run

1. Tạo **Service** mới trên Cloud Run, kết nối repo GitHub này qua Developer Connect (Continuously deploy from a repository).
2. **Root Directory / Source location**: `backend/Dockerfile`
3. **Memory**: tối thiểu 2 GiB (moviepy + Pillow + huggingface_hub cần nhiều RAM hơn mức mặc định 512 MiB).
4. **Billing**: Instance-based (CPU luôn cấp phát) — cần thiết vì Gradio xử lý video ở tác vụ nền tách khỏi luồng request; Request-based sẽ throttle CPU và khiến request bị treo.
5. **Networking**: bật **Session affinity**.
6. **Environment Variables**:
   - `GROQ_API_KEY` — key free tier từ [console.groq.com/keys](https://console.groq.com/keys), dùng cho 2 chế độ theo chủ đề ("Từ vựng theo chủ đề" và "Hội thoại theo chủ đề"). Không cần thẻ tín dụng, không ràng buộc billing account.
   - `GROQ_MODEL` — tùy chọn, mặc định `llama-3.3-70b-versatile`. Đặt biến này nếu Groq ngừng hỗ trợ model mặc định, không cần sửa code.
   - `HF_TOKEN` — access token (quyền **Read**) tạo tại [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens), dùng để gọi Inference API sinh ảnh.
7. Deploy. Cloud Build sẽ tự động build image từ `Dockerfile`, cài ffmpeg + dependencies, rồi chạy `python app.py` — app tự lắng nghe cổng Cloud Run cấp qua biến `$PORT`.

## Chạy local

```bash
cd backend
pip install -r requirements.txt
export GROQ_API_KEY=...   # chỉ cần cho 2 chế độ theo chủ đề (từ vựng / hội thoại)
export HF_TOKEN=...        # bắt buộc để sinh ảnh
python app.py
```

## Test

```bash
cd backend
pytest -v
```

Cần `ffmpeg`/`ffprobe` có sẵn trên PATH (dùng cho fixture audio của một vài test).
