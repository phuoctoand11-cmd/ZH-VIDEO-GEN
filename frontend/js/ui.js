// frontend/js/ui.js
import { validateForm, validatePreviewRequest, TOPIC_MODES } from "./validation.js";
import { callGenerateVideo, callGeneratePreview, describeStatusEvent } from "./api.js";
import { summarizeResult } from "./result.js";
import { connectClient } from "./gradioClient.js";
import { SPACE_URL } from "./config.js";

const INITIAL_STATUS = "Đang tạo video... (nếu server đang ngủ, lần đầu có thể mất 1-2 phút để khởi động)";

const DOWNLOAD_TARGETS = [
  { downloadId: "download-9-16", filename: "video-9-16.mp4" },
  { downloadId: "download-16-9", filename: "video-16-9.mp4" },
];

function readFormState(form) {
  return {
    mode: form.querySelector('input[name="mode"]:checked').value,
    csvText: form.querySelector("#csv-text").value,
    topic: form.querySelector("#topic").value,
    templateName: form.querySelector("#template-name").value,
    aspectRatios: Array.from(form.querySelectorAll('input[name="aspect_ratio"]:checked')).map((el) => el.value),
  };
}

function setStatus(doc, message) {
  doc.getElementById("status").textContent = message;
}

function isPlaceholderSpaceUrl(url) {
  return typeof url !== "string" || url.startsWith("REPLACE_");
}

// The `download` attribute is ignored by browsers for cross-origin resources
// (Cloudflare Pages -> *.hf.space), so fetch the file and download the Blob.
// If that is blocked (CORS, offline, ...), fall back to opening the video.
async function downloadVideo(doc, url, filename) {
  // Take the browser globals from the document's own window rather than the
  // ambient ones, so the object URL belongs to the same document as the anchor.
  const view = doc.defaultView;
  try {
    const response = await view.fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const blob = await response.blob();
    const objectUrl = view.URL.createObjectURL(blob);
    const tempLink = doc.createElement("a");
    tempLink.href = objectUrl;
    tempLink.download = filename;
    tempLink.style.display = "none";
    doc.body.appendChild(tempLink);
    tempLink.click();
    doc.body.removeChild(tempLink);
    // Revoking immediately can cancel the download in some browsers.
    view.setTimeout(() => view.URL.revokeObjectURL(objectUrl), 60000);
  } catch {
    view.open(url, "_blank");
  }
}

function wireDownload(doc, { downloadId, filename }) {
  const link = doc.getElementById(downloadId);
  if (!link) return;
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const url = link.getAttribute("href");
    if (!url) return;
    downloadVideo(doc, url, filename);
  });
}

function renderVideo(doc, { containerId, videoId, downloadId, url }) {
  const container = doc.getElementById(containerId);
  const video = doc.getElementById(videoId);
  if (!url) {
    // Drop the previous source so a hidden player stops buffering/playing.
    try {
      video.pause();
    } catch {
      /* media methods may be unavailable outside a real browser */
    }
    video.removeAttribute("src");
    try {
      video.load();
    } catch {
      /* ignore */
    }
    doc.getElementById(downloadId).removeAttribute("href");
    container.style.display = "none";
    return;
  }
  video.src = url;
  doc.getElementById(downloadId).href = url;
  container.style.display = "block";
}

function clearResults(doc) {
  renderVideo(doc, { containerId: "result-9-16", videoId: "video-9-16", downloadId: "download-9-16", url: null });
  renderVideo(doc, { containerId: "result-16-9", videoId: "video-16-9", downloadId: "download-16-9", url: null });
  doc.getElementById("log").textContent = "";
}

function renderResult(doc, result) {
  renderVideo(doc, { containerId: "result-9-16", videoId: "video-9-16", downloadId: "download-9-16", url: result.video9x16Url });
  renderVideo(doc, { containerId: "result-16-9", videoId: "video-16-9", downloadId: "download-16-9", url: result.video16x9Url });
  doc.getElementById("log").textContent = result.log;
}

function updatePreviewButtonVisibility(doc) {
  const previewBtn = doc.getElementById("preview-btn");
  const mode = doc.querySelector('input[name="mode"]:checked')?.value;
  previewBtn.style.display = TOPIC_MODES.includes(mode) ? "" : "none";
}

function wirePreviewButton(doc) {
  const previewBtn = doc.getElementById("preview-btn");

  previewBtn.addEventListener("click", async () => {
    const state = readFormState(doc.getElementById("generate-form"));

    const validation = validatePreviewRequest(state);
    if (!validation.valid) {
      setStatus(doc, validation.error);
      return;
    }

    if (isPlaceholderSpaceUrl(SPACE_URL)) {
      setStatus(doc, "Chưa cấu hình SPACE_URL — xem README.md.");
      return;
    }

    previewBtn.disabled = true;
    setStatus(doc, "Đang tạo bản xem trước...");

    try {
      const { csvText, log } = await callGeneratePreview(state, { spaceUrl: SPACE_URL, connectClient });
      doc.getElementById("csv-text").value = csvText;
      setStatus(doc, log);
    } catch (err) {
      setStatus(doc, `Lỗi: ${err.message}`);
    } finally {
      previewBtn.disabled = false;
    }
  });
}

export function initApp(doc) {
  const form = doc.getElementById("generate-form");
  const submitBtn = doc.getElementById("submit-btn");

  DOWNLOAD_TARGETS.forEach((target) => wireDownload(doc, target));

  updatePreviewButtonVisibility(doc);
  form.querySelectorAll('input[name="mode"]').forEach((radio) => {
    radio.addEventListener("change", () => updatePreviewButtonVisibility(doc));
  });
  wirePreviewButton(doc);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      const state = readFormState(form);

      const validation = validateForm(state);
      if (!validation.valid) {
        setStatus(doc, validation.error);
        return;
      }

      clearResults(doc);

      if (isPlaceholderSpaceUrl(SPACE_URL)) {
        setStatus(doc, "Chưa cấu hình SPACE_URL — xem README.md.");
        return;
      }

      submitBtn.disabled = true;
      setStatus(doc, INITIAL_STATUS);

      const onStatus = (statusEvent) => {
        const message = describeStatusEvent(statusEvent);
        if (message) setStatus(doc, message);
      };

      const result = await callGenerateVideo(state, { spaceUrl: SPACE_URL, connectClient, onStatus });
      renderResult(doc, result);
      setStatus(doc, summarizeResult(result));
    } catch (err) {
      setStatus(doc, `Lỗi: ${err.message}`);
    } finally {
      submitBtn.disabled = false;
    }
  });
}
