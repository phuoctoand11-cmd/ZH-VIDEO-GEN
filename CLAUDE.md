# zh-video-gen

App tạo video dạy tiếng Trung song ngữ Việt–Trung, deploy thật (URL cố định), miễn phí.
Monorepo: `backend/` (Google Cloud Run, Gradio) + `frontend/` (Cloudflare Pages, static).

## Trạng thái hiện tại (cập nhật 2026-09-01)

- **Branch `main`**, HEAD `6a2e52d`, đã push. Backend 134 test pytest pass, frontend 41 test `node --test` pass.

### ⏳ ĐANG DỞ — việc duy nhất còn lại

**Nạp 53 ảnh mới lên bucket.** `backend/tools/scene_library_seed.csv` đã mở rộng lên **77 dòng** (commit `6a2e52d`) nhưng loader **chưa chạy** cho phần mới — bucket vẫn đang có 29 file / bảng `scene_images` 29 row. User cần chạy (PowerShell, cần `SUPABASE_SERVICE_ROLE_KEY` — legacy JWT hoặc `sb_secret_` đều được):
```
cd D:\WORKSPACE\zh-video-gen\backend
$env:SUPABASE_URL = "https://yvybrsjgumwmmnwdqalq.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<key>"
python tools/load_scene_library.py --images-root "D:/KHO ẢNH"
```
Mong đợi `77 loaded, 0 failed` → bucket ~77 file, bảng ~81 row (77 + 4 organic: 煎饼/粥/豆浆/油条). Xong thì verify count trong Supabase dashboard.

### ✅ ĐÃ XONG

- **Kho ảnh Supabase**: project `yvybrsjgumwmmnwdqalq` (org "Learning-AI", tài khoản `xinthiet@gmail.com` — KHÁC email dùng ở máy). Bảng `scene_images` + index + RLS "Public read access", bucket `scene-images` (Public). Cloud Run `zh-video-gen-backend` (project number `835496143706`, region `europe-west1`) có sẵn `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.
- **Loader** `backend/tools/load_scene_library.py` (+ `scene_library_seed.csv`, `tests/tools/`): đọc CSV `hanzi,pinyin,meaning_vi,source_path`, upload ảnh lên bucket + upsert row. Idempotent. Đã chạy thành công cho 24 dòng đầu; pipeline thật đã verify (video 狗 lấy ảnh từ kho, log "không có lỗi").
- **Bug `InvalidKey` (commit `f3288ed`, deploy rồi)**: Supabase Storage không nhận tên object CJK → thêm `visuals/scene_library.py::storage_key_for(hanzi)` = `sha256(hanzi)[:16] + ".png"`; cả `store_generated_image` và loader dùng chung. `find_cached_image` đọc `image_path` từ row nên scheme-agnostic. (Luồng app tự lưu ảnh trước giờ chưa từng chạy được, nay OK.)
- **Bug tải video ra file UUID không đuôi (commit `28e72cb`, deploy + verify)**: link tải trước trỏ thẳng URL Gradio cross-origin không có `Content-Disposition`. Thêm Pages Function `frontend/functions/dl/[[path]].js` (`/dl/<name>?src=<url>`): validate `src` đúng origin backend (chống SSRF), fetch server-side, trả kèm `Content-Disposition: attachment; filename=...`. `result.js::buildDownloadHref()`; `ui.js` bỏ hẳn `downloadVideo`/`wireDownload`. Verify: `/dl` trả 200 + `attachment; filename="video-9-16.mp4"` + MP4 thật.

### Ghi chú

- Lần test 28/08 sinh ảnh fail vì Cloudflare **HTTP 429 (rate limit)** → placeholder → không lưu kho (đúng thiết kế). Nếu kho không lớn thêm sau khi tạo video, kiểm tra 429 trước khi nghĩ setup sai.
- 2 git worktree trong `.claude/worktrees/` (`backend-implementation`, `frontend-cloudflare`) — nhánh cũ, chưa dọn. `.claude/` đã gitignore.
- `KHO ẢNH`: `D:\KHO ẢNH`, 92 PNG, tên `NN_<nhãn VN không dấu>.png`. Đã map hết trừ các bản trùng (gia_vi_2 = bản màu khác của gia_vi_1; 4 cupcake/2 flan/2 thạch/2 bắp rang gộp còn 1).

## URL deploy

- Frontend: https://zh-video-gen.pages.dev (Cloudflare Pages, auto-deploy khi push `frontend/`)
- Backend: https://zh-video-gen-backend-835496143706.europe-west1.run.app (đặt trong `frontend/js/config.js` → `SPACE_URL`)

## Kiến trúc (trạng thái THỰC TẾ — spec trong `docs/` đã cũ vài chỗ)

3 chế độ (`backend/app.py` → `MODES`):
1. **Nhập danh sách** — từ vựng nhập tay (CSV/text).
2. **Từ vựng theo chủ đề** — Groq soạn từ 1 chủ đề, có bước "Xem trước" sửa trước khi tạo.
3. **Hội thoại theo chủ đề** — hội thoại 2 nhân vật, cũng qua Groq.

Video dùng **card thiết kế sẵn**: chữ Hán/pinyin/nghĩa do code vẽ trực tiếp (`render/vocab_card.py`, `render/dialogue_card.py`), KHÔNG overlay AI. Scene clip **tĩnh** (không Ken Burns).

Pipeline (`backend/pipeline.py`): `run_vocab_card_pipeline` / `run_dialogue_pipeline`.
- Ảnh minh hoạ scene (chế độ từ vựng): tra `visuals/scene_library.py` `find_cached_image(hanzi)` trong Supabase trước → không có mới gọi `visuals/image.py` `generate_image()` (Cloudflare Workers AI, model `@cf/leonardo/phoenix-1.0`) → ảnh sinh thành công tự lưu lại qua hook `on_success` → `store_generated_image()`. Match theo **exact hanzi**, không semantic.
- Avatar nhân vật (chế độ hội thoại): luôn gọi Cloudflare, KHÔNG qua kho.
- `scene_library` best-effort tuyệt đối: mọi lỗi Supabase phải fall through về generation, không được làm sập tạo video.

Stack: `pypinyin` (offline), `edge-tts` (không key), Groq (`llama-3.3-70b-versatile`, đổi qua `GROQ_MODEL`), `moviepy`/`ffmpeg`, Gradio 6.

## Env vars (Cloud Run)

| Biến | Bắt buộc | Dùng cho |
|---|---|---|
| `GROQ_API_KEY` | cho 2 chế độ theo chủ đề | LLM soạn bài |
| `GROQ_MODEL` | không (mặc định `llama-3.3-70b-versatile`) | đổi model nếu Groq bỏ model cũ |
| `CF_ACCOUNT_ID` | có (để sinh ảnh) | Cloudflare Workers AI |
| `CF_API_TOKEN` | có (để sinh ảnh) | Cloudflare Workers AI, quyền Workers AI → Edit |
| `SUPABASE_URL` | không (thiếu → luôn gọi CF) | kho ảnh |
| `SUPABASE_SERVICE_ROLE_KEY` | không (thiếu → luôn gọi CF) | kho ảnh, đọc/ghi |

## Chạy local + test

```bash
cd backend
pip install -r requirements.txt
export GROQ_API_KEY=... CF_ACCOUNT_ID=... CF_API_TOKEN=...
# SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY tùy chọn
python app.py            # nghe cổng $PORT (mặc định 7860)
pytest -v                # cần ffmpeg/ffprobe trên PATH
```

## Quy ước làm việc

- Không có CI; chạy `pytest tests/` thủ công trước khi commit.
- Commit message viết kỹ, giải thích *lý do* (xem git log — mẫu tốt sẵn có).
- Cloud Build trigger KHÔNG lọc theo path: mọi commit vào `main` (kể cả chỉ sửa `frontend/`) đều rebuild backend.
- Google Cloud/Gemini bị né chủ ý: gắn billing account bất kỳ vào 1 project cùng danh tính Google là toàn bộ bị nâng lên tier trả phí — nên dùng Groq (tách biệt).
- Cuối mỗi phiên làm việc: cập nhật mục "Trạng thái hiện tại" ở trên + ghi tiến độ vào auto-memory.

## Tài liệu thiết kế

- `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md` — spec gốc (một số chỗ đã cũ: nói HF Inference + Ken Burns; giờ là Cloudflare + scene tĩnh).
- `docs/superpowers/specs/2026-08-25-card-templates-design.md` — thiết kế card template (bản thay thế hệ ảnh nền).
