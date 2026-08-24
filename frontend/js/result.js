function extractVideoUrl(value) {
  if (!value) return null;
  if (typeof value === "string") return value;
  if (typeof value === "object" && value.url) return value.url;
  return null;
}

export function parseApiResult(data) {
  const [video9x16Raw, video16x9Raw, log] = data;
  return {
    video9x16Url: extractVideoUrl(video9x16Raw),
    video16x9Url: extractVideoUrl(video16x9Raw),
    log: log ?? "",
  };
}
