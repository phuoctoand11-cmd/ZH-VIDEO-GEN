# zh-video-gen backend

Backend tạo video dạy tiếng Trung song ngữ Việt-Trung, hỗ trợ 3 chế độ: **Nhập danh sách** (từ vựng tự nhập thủ công), **Từ vựng theo chủ đề** (tự soạn qua [Groq](https://console.groq.com) từ một chủ đề, có bước "Xem trước" để kiểm tra/sửa trước khi tạo video), và **Hội thoại theo chủ đề** (đoạn hội thoại 2 nhân vật, cũng tự soạn qua Groq). Video dùng card thiết kế theo phong cách "poster từ vựng" (tiêu đề, khung từng dòng, icon trang trí) — chữ Hán/pinyin/nghĩa do code vẽ trực tiếp lên card (không phải overlay AI), AI chỉ sinh ảnh minh họa bối cảnh khớp nghĩa từ (chế độ từ vựng) hoặc avatar nhân vật (chế độ hội thoại) bằng model mã nguồn mở **FLUX.1-schnell chạy trên Hugging Face Space riêng (ZeroGPU, miễn phí)** — xem `hf-space-image-gen/` — gọi qua `gradio_client`, không cần torch/diffusers trong container backend, rồi ghép thành video bằng moviepy/ffmpeg. Expose qua Gradio app (`app.py`), deploy trên [Google Cloud Run](https://cloud.google.com/run).

Xem thiết kế đầy đủ tại `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md` trong repo chính.

## Deploy phần sinh ảnh (Hugging Face Space)

1. Tạo Space mới tại [huggingface.co/new-space](https://huggingface.co/new-space): SDK **Gradio**, Hardware **ZeroGPU**.
2. Copy nội dung `hf-space-image-gen/app.py`, `requirements.txt`, `README.md` vào Space đó (qua giao diện web hoặc `git push`).
3. Space tự build và chạy — không cần cấu hình gì thêm.
4. **Lưu ý hạn mức**: tài khoản free có **5 phút GPU/ngày** (reset 24h sau lần dùng đầu tiên). FLUX.1-schnell 4 bước trên GPU thật rất nhanh (~2-4s/ảnh) nên đủ cho hàng chục video/ngày trong điều kiện dùng bình thường — nhưng test dồn dập nhiều lần liên tiếp sẽ cạn hạn mức nhanh.

## Deploy backend lên Google Cloud Run

1. Tạo **Service** mới trên Cloud Run, kết nối repo GitHub này qua Developer Connect (Continuously deploy from a repository).
2. **Root Directory / Source location**: `backend/Dockerfile`
3. **Memory**: tối thiểu 2 GiB (moviepy + Pillow cần nhiều RAM hơn mức mặc định 512 MiB).
4. **Billing**: Instance-based (CPU luôn cấp phát) — cần thiết vì Gradio xử lý video ở tác vụ nền tách khỏi luồng request; Request-based sẽ throttle CPU và khiến request bị treo.
5. **Networking**: bật **Session affinity**.
6. **Environment Variables**:
   - `GROQ_API_KEY` — key free tier từ [console.groq.com/keys](https://console.groq.com/keys), dùng cho 2 chế độ theo chủ đề ("Từ vựng theo chủ đề" và "Hội thoại theo chủ đề"). Không cần thẻ tín dụng, không ràng buộc billing account.
   - `GROQ_MODEL` — tùy chọn, mặc định `llama-3.3-70b-versatile`. Đặt biến này nếu Groq ngừng hỗ trợ model mặc định, không cần sửa code.
   - `HF_TOKEN` — access token (quyền **Read**) tạo tại [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens), dùng để xác thực khi gọi Space — bắt buộc để request tính vào hạn mức GPU của tài khoản bạn thay vì pool dùng chung (giới hạn chặt hơn nhiều).
   - `IMAGE_SPACE_ID` — id của Space vừa tạo, dạng `username/space-name`.
7. Deploy. Cloud Build sẽ tự động build image từ `Dockerfile`, cài ffmpeg + dependencies, rồi chạy `python app.py` — app tự lắng nghe cổng Cloud Run cấp qua biến `$PORT`.

## Chạy local

```bash
cd backend
pip install -r requirements.txt
export GROQ_API_KEY=...      # chỉ cần cho 2 chế độ theo chủ đề (từ vựng / hội thoại)
export HF_TOKEN=...          # bắt buộc để sinh ảnh
export IMAGE_SPACE_ID=...    # bắt buộc để sinh ảnh, dạng username/space-name
python app.py
```

## Test

```bash
cd backend
pytest -v
```

Cần `ffmpeg`/`ffprobe` có sẵn trên PATH (dùng cho fixture audio của một vài test).
