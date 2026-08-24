export function validateForm(state) {
  if (state.mode === "Nhập danh sách") {
    if (!state.csvText || !state.csvText.trim()) {
      return { valid: false, error: "Vui lòng nhập danh sách CSV." };
    }
  } else if (state.mode === "Chủ đề tự động") {
    if (!state.topic || !state.topic.trim()) {
      return { valid: false, error: "Vui lòng nhập chủ đề." };
    }
  } else {
    return { valid: false, error: `Chế độ không hợp lệ: ${state.mode}` };
  }

  if (!state.aspectRatios || state.aspectRatios.length === 0) {
    return { valid: false, error: "Vui lòng chọn ít nhất một tỉ lệ khung hình." };
  }

  return { valid: true, error: null };
}
