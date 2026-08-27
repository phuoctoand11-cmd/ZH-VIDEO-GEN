# zh-video-gen backend

Backend tạo video dạy tiếng Trung song ngữ Việt-Trung, hỗ trợ 3 chế độ: **Nhập danh sách** (từ vựng tự nhập thủ công), **Từ vựng theo chủ đề** (tự soạn qua [Groq](https://console.groq.com) từ một chủ đề, có bước "Xem trước" để kiểm tra/sửa trước khi tạo video), và **Hội thoại theo chủ đề** (đoạn hội thoại 2 nhân vật, cũng tự soạn qua Groq). Video dùng card thiết kế theo phong cách "poster từ vựng" (tiêu đề, khung từng dòng, icon trang trí) — chữ Hán/pinyin/nghĩa do code vẽ trực tiếp lên card (không phải overlay AI), AI chỉ sinh ảnh minh họa bối cảnh khớp nghĩa từ (chế độ từ vựng) hoặc avatar nhân vật (chế độ hội thoại) bằng model mã nguồn mở **tự host ngay trong container** (`runwayml/stable-diffusion-v1-5` + `latent-consistency/lcm-lora-sdv1-5`, chạy CPU qua `diffusers`, không gọi API bên ngoài nào), rồi ghép thành video bằng moviepy/ffmpeg. Expose qua Gradio app (`app.py`), deploy trên [Google Cloud Run](https://cloud.google.com/run).

Xem thiết kế đầy đủ tại `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md` trong repo chính.

## Deploy lên Google Cloud Run

1. Tạo **Service** mới trên Cloud Run, kết nối repo GitHub này qua Developer Connect (Continuously deploy from a repository).
2. **Root Directory / Source location**: `backend/Dockerfile`
3. **Memory**: tối thiểu **4-8 GiB** (model AI tự host cần nhiều RAM hơn hẳn giai đoạn chỉ gọi API ngoài — 2 GiB trước đây không còn đủ).
4. **CPU**: khuyến nghị **2-4 vCPU** — sinh ảnh chạy trên CPU (không có GPU), càng nhiều vCPU càng nhanh.
5. **Billing**: Instance-based (CPU luôn cấp phát) — cần thiết vì Gradio xử lý video ở tác vụ nền tách khỏi luồng request; Request-based sẽ throttle CPU và khiến request bị treo.
6. **Networking**: bật **Session affinity**.
7. **Environment Variables**:
   - `GROQ_API_KEY` — key free tier từ [console.groq.com/keys](https://console.groq.com/keys), dùng cho 2 chế độ theo chủ đề ("Từ vựng theo chủ đề" và "Hội thoại theo chủ đề"). Không cần thẻ tín dụng, không ràng buộc billing account.
   - `GROQ_MODEL` — tùy chọn, mặc định `llama-3.3-70b-versatile`. Đặt biến này nếu Groq ngừng hỗ trợ model mặc định, không cần sửa code.
   - Không còn cần biến môi trường nào cho phần sinh ảnh — model chạy ngay trong container, không gọi dịch vụ ngoài.
8. Deploy. Cloud Build sẽ tự động build image từ `Dockerfile` — cài ffmpeg + dependencies, **tải sẵn model AI vào image lúc build** (không tải lúc chạy), rồi chạy `python app.py` — app tự lắng nghe cổng Cloud Run cấp qua biến `$PORT`. Build sẽ lâu hơn và image nặng hơn đáng kể so với trước (do tải model weights vào layer).

## Chạy local

```bash
cd backend
pip install -r requirements.txt   # nặng hơn trước — kéo thêm torch/diffusers (~1-3 GB)
export GROQ_API_KEY=...   # chỉ cần cho 2 chế độ theo chủ đề (từ vựng / hội thoại)
python app.py
```

## Test

```bash
cd backend
pytest -v
```

Cần `ffmpeg`/`ffprobe` có sẵn trên PATH (dùng cho fixture audio của một vài test).
