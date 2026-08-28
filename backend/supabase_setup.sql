-- Chạy trong Supabase SQL Editor (dashboard.supabase.com -> project -> SQL Editor).
-- Bảng lưu metadata cho kho ảnh minh hoạ từ vựng. Ảnh thật nằm trong Storage
-- bucket "scene-images" (tạo riêng ở bước Storage, không tạo được bằng SQL).

create table if not exists scene_images (
  id bigint generated always as identity primary key,
  hanzi text not null unique,  -- unique để upsert sạch khi backend tự lưu ảnh mới
  pinyin text,
  meaning_vi text,
  icon_prompt text,
  image_path text not null,  -- đường dẫn file trong bucket "scene-images"
  created_at timestamptz default now()
);

-- So khớp chính xác theo hanzi là truy vấn chính (V1 dùng exact match,
-- không dùng vector/semantic search để tránh phải cài thêm model embedding).
create index if not exists scene_images_hanzi_idx on scene_images (hanzi);

-- Cho phép đọc công khai (ảnh minh hoạ không nhạy cảm) nhưng chỉ backend
-- (dùng service_role key) mới ghi được — chặn ghi từ phía client/anon.
alter table scene_images enable row level security;

create policy "Public read access"
  on scene_images for select
  using (true);
