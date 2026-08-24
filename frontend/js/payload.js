export function buildApiPayload(state) {
  return [
    state.mode,
    state.csvText ?? "",
    state.topic ?? "",
    state.templateName,
    state.aspectRatios,
  ];
}
