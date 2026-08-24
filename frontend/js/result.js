// frontend/js/result.js

// Only these schemes may ever reach an <a href> / <video src>. Anything else
// (javascript:, data:, file:, ...) is treated as if no video were returned.
const ALLOWED_URL_SCHEMES = ["http://", "https://", "blob:"];

function isSafeUrl(url) {
  if (typeof url !== "string") return false;
  const normalized = url.trim().toLowerCase();
  return ALLOWED_URL_SCHEMES.some((scheme) => normalized.startsWith(scheme));
}

function extractVideoUrl(value) {
  if (!value) return null;
  if (typeof value === "string") return isSafeUrl(value) ? value : null;
  if (typeof value !== "object") return null;
  // Flat gr.Video shape ({ url, path, ... }) with a fallback for the older /
  // nested shape ({ video: { url, ... } }).
  const url = value.url ?? value.video?.url ?? null;
  return isSafeUrl(url) ? url : null;
}

export function parseApiResult(data) {
  if (!Array.isArray(data)) {
    return { video9x16Url: null, video16x9Url: null, log: "" };
  }
  const [video9x16Raw, video16x9Raw, log] = data;
  return {
    video9x16Url: extractVideoUrl(video9x16Raw),
    video16x9Url: extractVideoUrl(video16x9Raw),
    log: log ?? "",
  };
}

// The backend never raises: every failure comes back as a normal 3-tuple with
// both videos null and the real error text in `log`. The only reliable success
// signal is the presence of at least one video URL.
export function summarizeResult(result) {
  const gotVideo = Boolean(result && (result.video9x16Url || result.video16x9Url));
  return gotVideo ? "Hoàn tất." : "Không tạo được video — xem log bên dưới.";
}
