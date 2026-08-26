# zh-video-gen backend

Backend tạo video dạy tiếng Trung song ngữ Việt-Trung, hỗ trợ 3 chế độ: **Nhập danh sách** (từ vựng tự nhập thủ công), **Từ vựng theo chủ đề** (tự soạn qua [Groq](https://console.groq.com) từ một chủ đề, có bước "Xem trước" để kiểm tra/sửa trước khi tạo video), và **Hội thoại theo chủ đề** (đoạn hội thoại 2 nhân vật, cũng tự soạn qua Groq). Video dùng card thiết kế theo phong cách "poster từ vựng" (tiêu đề, khung từng dòng, icon trang trí) — chữ Hán/pinyin/nghĩa do code vẽ trực tiếp lên card (không phải overlay AI), AI qua [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) (model `@cf/leonardo/phoenix-1.0`, không tự host model) chỉ sinh ảnh minh họa bối cảnh khớp nghĩa từ (chế độ từ vựng) hoặc avatar nhân vật (chế độ hội thoại), rồi ghép thành video bằng moviepy/ffmpeg. Expose qua Gradio app (`app.py`), deploy trên [Google Cloud Run](https://cloud.google.com/run).

Xem thiết kế đầy đủ tại `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md` trong repo chính.

## Deploy lên Google Cloud Run

1. Tạo **Service** mới trên Cloud Run, kết nối repo GitHub này qua Developer Connect (Continuously deploy from a repository).
2. **Root Directory / Source location**: `backend/Dockerfile`
3. **Memory**: tối thiểu 2 GiB (moviepy + Pillow cần nhiều RAM hơn mức mặc định 512 MiB).
4. **Billing**: Instance-based (CPU luôn cấp phát) — cần thiết vì Gradio xử lý video ở tác vụ nền tách khỏi luồng request; Request-based sẽ throttle CPU và khiến request bị treo.
5. **Networking**: bật **Session affinity**.
6. **Environment Variables**:
   - `GROQ_API_KEY` — key free tier từ [console.groq.com/keys](https://console.groq.com/keys), dùng cho 2 chế độ theo chủ đề ("Từ vựng theo chủ đề" và "Hội thoại theo chủ đề"). Không cần thẻ tín dụng, không ràng buộc billing account.
   - `GROQ_MODEL` — tùy chọn, mặc định `llama-3.3-70b-versatile`. Đặt biến này nếu Groq ngừng hỗ trợ model mặc định, không cần sửa code.
   - `CF_ACCOUNT_ID` — Account ID Cloudflare (xem ở dashboard chính, sidebar phải).
   - `CF_API_TOKEN` — API Token tạo tại [dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens) với quyền **Account → Workers AI → Edit**, dùng để gọi Workers AI sinh ảnh.
7. Deploy. Cloud Build sẽ tự động build image từ `Dockerfile`, cài ffmpeg + dependencies, rồi chạy `python app.py` — app tự lắng nghe cổng Cloud Run cấp qua biến `$PORT`.

## Chạy local

```bash
cd backend
pip install -r requirements.txt
export GROQ_API_KEY=...   # chỉ cần cho 2 chế độ theo chủ đề (từ vựng / hội thoại)
export CF_ACCOUNT_ID=...  # bắt buộc để sinh ảnh
export CF_API_TOKEN=...   # bắt buộc để sinh ảnh
python app.py
```

## Test

```bash
cd backend
pytest -v
```

Cần `ffmpeg`/`ffprobe` có sẵn trên PATH (dùng cho fixture audio của một vài test).
