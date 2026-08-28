# zh-video-gen backend

Backend tạo video dạy tiếng Trung song ngữ Việt-Trung, hỗ trợ 3 chế độ: **Nhập danh sách** (từ vựng tự nhập thủ công), **Từ vựng theo chủ đề** (tự soạn qua [Groq](https://console.groq.com) từ một chủ đề, có bước "Xem trước" để kiểm tra/sửa trước khi tạo video), và **Hội thoại theo chủ đề** (đoạn hội thoại 2 nhân vật, cũng tự soạn qua Groq). Video dùng card thiết kế theo phong cách "poster từ vựng" (tiêu đề, khung từng dòng, icon trang trí) — chữ Hán/pinyin/nghĩa do code vẽ trực tiếp lên card (không phải overlay AI). Ảnh minh họa bối cảnh (chế độ từ vựng) tra trong **kho ảnh Supabase** trước (`visuals/scene_library.py`, so khớp theo `hanzi` — xem `supabase_setup.sql`); không có mới gọi [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) (model `@cf/leonardo/phoenix-1.0`) sinh ảnh mới rồi tự lưu vào kho cho lần sau. Avatar nhân vật (chế độ hội thoại) vẫn luôn gọi Cloudflare, không qua kho. Cuối cùng ghép thành video bằng moviepy/ffmpeg. Expose qua Gradio app (`app.py`), deploy trên [Google Cloud Run](https://cloud.google.com/run).

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
   - `SUPABASE_URL` — Project URL của Supabase (Project Settings → API), dạng `https://xxxxx.supabase.co`.
   - `SUPABASE_SERVICE_ROLE_KEY` — **service_role key** (không phải `anon`/`public` key) từ Project Settings → API, dùng để backend đọc/ghi kho ảnh. Thiếu 2 biến này thì kho ảnh bị bỏ qua hoàn toàn (tự động fallback về gọi Cloudflare mỗi lần), không làm app lỗi.
7. Deploy. Cloud Build sẽ tự động build image từ `Dockerfile`, cài ffmpeg + dependencies, rồi chạy `python app.py` — app tự lắng nghe cổng Cloud Run cấp qua biến `$PORT`.

## Kho ảnh Supabase

Chạy `supabase_setup.sql` trong SQL Editor của project Supabase để tạo bảng `scene_images`, rồi tạo Storage bucket tên `scene-images` (bật **Public bucket**) — chi tiết xem comment trong file SQL.

## Chạy local

```bash
cd backend
pip install -r requirements.txt
export GROQ_API_KEY=...              # chỉ cần cho 2 chế độ theo chủ đề (từ vựng / hội thoại)
export CF_ACCOUNT_ID=...             # bắt buộc để sinh ảnh
export CF_API_TOKEN=...              # bắt buộc để sinh ảnh
export SUPABASE_URL=...              # tùy chọn — thiếu thì luôn gọi Cloudflare, không dùng kho ảnh
export SUPABASE_SERVICE_ROLE_KEY=... # tùy chọn — như trên
python app.py
```

## Test

```bash
cd backend
pytest -v
```

Cần `ffmpeg`/`ffprobe` có sẵn trên PATH (dùng cho fixture audio của một vài test).
