export function buildApiPayload(state) {
  return [state.mode, state.csvText ?? "", state.templateName, state.aspectRatios];
}

export function buildPreviewPayload(state) {
  return [state.mode, state.topic ?? ""];
}
