export function buildApiPayload(state) {
  // topic is display-only server-side (labels the vocab card's "Chủ đề: …"
  // subtitle) — it is never sent to the LLM again here, that already
  // happened, if at all, via buildPreviewPayload/generate_preview.
  return [state.mode, state.csvText ?? "", state.templateName, state.aspectRatios, state.topic ?? ""];
}

export function buildPreviewPayload(state) {
  return [state.mode, state.topic ?? ""];
}
