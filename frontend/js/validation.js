const MODES = ["Nhập danh sách", "Từ vựng theo chủ đề", "Hội thoại theo chủ đề"];
export const TOPIC_MODES = ["Từ vựng theo chủ đề", "Hội thoại theo chủ đề"];

// generate_video always renders from csvText now, for every mode — a topic
// mode's csvText is populated by "Xem trước" (generate_preview) rather than
// typed directly, but by the time the user submits, csvText is the only
// thing that matters here.
export function validateForm(state) {
  if (!MODES.includes(state.mode)) {
    return { valid: false, error: `Chế độ không hợp lệ: ${state.mode}` };
  }

  if (!state.csvText || !state.csvText.trim()) {
    const error = TOPIC_MODES.includes(state.mode)
      ? 'Vui lòng bấm "Xem trước" để tạo nội dung trước khi tạo video.'
      : "Vui lòng nhập danh sách CSV.";
    return { valid: false, error };
  }

  if (!state.aspectRatios || state.aspectRatios.length === 0) {
    return { valid: false, error: "Vui lòng chọn ít nhất một tỉ lệ khung hình." };
  }

  return { valid: true, error: null };
}

export function validatePreviewRequest(state) {
  if (!TOPIC_MODES.includes(state.mode)) {
    return { valid: false, error: `Chế độ '${state.mode}' không dùng xem trước.` };
  }
  if (!state.topic || !state.topic.trim()) {
    return { valid: false, error: "Vui lòng nhập chủ đề." };
  }
  return { valid: true, error: null };
}
