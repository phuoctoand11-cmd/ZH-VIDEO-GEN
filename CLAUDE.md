# zh-video-gen

App tạo video dạy tiếng Trung song ngữ Việt–Trung, deploy thật (URL cố định), miễn phí.
Monorepo: `backend/` (Google Cloud Run, Gradio) + `frontend/` (Cloudflare Pages, static).

## Trạng thái hiện tại (cập nhật 2026-08-29)

- **Branch `main` sạch**, HEAD `808b383`, đã push. 125 test pytest, tất cả pass.
- **Kho ảnh Supabase: ĐÃ setup xong** (project Supabase `yvybrsjgumwmmnwdqalq`, org "Learning-AI", tài khoản `xinthiet@gmail.com`):
  - ✅ Bảng `scene_images` + index `scene_images_hanzi_idx` + RLS policy "Public read access" — đã chạy trong SQL Editor.
  - ✅ Storage bucket `scene-images` — đã tạo, Public.
  - ✅ Cloud Run (`zh-video-gen-backend`, project number `835496143706`, region `europe-west1`, revision đang chạy `00042-2dn`): `SUPABASE_URL` = `https://yvybrsjgumwmmnwdqalq.supabase.co` + `SUPABASE_SERVICE_ROLE_KEY` (dùng key `sb_secret_...` format mới — vẫn chạy đúng với PostgREST/Storage). Còn `HF_TOKEN` thừa từ hệ cũ, vô hại.
  - ✅ Backend code có scene_library: Cloud Build `b1390431` từ commit `808b383` build + deploy thành công.
  - ⏳ **Chưa chạy test end-to-end**: tạo video "Từ vựng theo chủ đề" trên https://zh-video-gen.pages.dev → xác nhận `scene_images` có row mới + bucket có ảnh; lần 2 cùng từ đó phải lấy từ kho (không gọi lại Cloudflare). Xem log Cloud Run tìm chuỗi `scene_images`.
  - Lần test 28/08 sinh ảnh fail vì Cloudflare trả **HTTP 429 (rate limit)** → placeholder → không lưu kho (đúng thiết kế). Nếu kho vẫn rỗng sau khi tạo video, kiểm tra 429 trước khi nghĩ setup sai.
- **Nạp sẵn kho ảnh**: `backend/tools/load_scene_library.py` + `backend/tools/scene_library_seed.csv` (24 từ: trái cây, rau củ, động vật bộ 1 — map từ `D:\KHO ẢNH`). Chạy local với `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (key nào cũng được — legacy JWT hoặc `sb_secret_`): `python tools/load_scene_library.py --images-root "D:/KHO ẢNH"`. Test `tests/tools/test_load_scene_library.py` (8 test). ✅ **Đã nạp 24 từ (2026-08-29)**: 24 row `scene_images` + 24 PNG trong bucket, public URL trả ảnh thật. Còn ~75 ảnh nữa trong `D:\KHO ẢNH` (FOOD, GIA VỊ, động vật bộ 2) chưa map. ⏳ Chưa có lần chạy pipeline thật xác nhận app lấy ảnh từ kho (test bằng "Nhập danh sách" với 苹果 / 狗).
- **Bug đã sửa 2026-08-29**: `store_generated_image()` (và loader) trước dùng `{hanzi}.png` làm tên object → Supabase Storage trả `400 InvalidKey` (không nhận CJK). Giờ có `visuals/scene_library.py::storage_key_for(hanzi)` = hash sha256[:16] + `.png`, cả 2 nơi ghi đều dùng chung. `find_cached_image` đọc `image_path` từ row nên không đổi. Nghĩa là luồng "app tự lưu ảnh" trước giờ chưa từng chạy được — nay đã fix.
- **Fix tải video 2026-08-29** (đang chờ deploy + verify): nút "Tải video" trước trỏ thẳng URL Gradio cross-origin không có `Content-Disposition` → Chrome lưu file tên UUID không đuôi. Thêm Pages Function `frontend/functions/dl/[[path]].js` (`/dl/<name>?src=<url>`): validate `src` đúng origin backend, fetch server-side, trả kèm `Content-Disposition: attachment`. `frontend/js/result.js` thêm `buildDownloadHref()`; `frontend/js/ui.js` bỏ `downloadVideo`/`wireDownload` (fetch→blob→window.open) — nút tải giờ là link thường tới `/dl/...`. Test: `frontend/tests/dl.test.js` (5), `result.test.js` (+2). 41 test frontend pass. Lần đầu project có `frontend/functions/`.
- Có 2 git worktree trong `.claude/worktrees/` (`backend-implementation`, `frontend-cloudflare`) — nhánh cũ, chưa dọn.

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
