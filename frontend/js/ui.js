// frontend/js/ui.js
import { validateForm, validatePreviewRequest, TOPIC_MODES } from "./validation.js";
import { callGenerateVideo, callGeneratePreview, describeStatusEvent } from "./api.js";
import { summarizeResult, buildDownloadHref } from "./result.js";
import { connectClient } from "./gradioClient.js";
import { SPACE_URL } from "./config.js";

const INITIAL_STATUS = "Đang tạo video... (nếu server đang ngủ, lần đầu có thể mất 1-2 phút để khởi động)";

const RESULT_TARGETS = [
  {
    containerId: "result-9-16",
    videoId: "video-9-16",
    downloadId: "download-9-16",
    downloadName: "video-9-16.mp4",
  },
  {
    containerId: "result-16-9",
    videoId: "video-16-9",
    downloadId: "download-16-9",
    downloadName: "video-16-9.mp4",
  },
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

// The download <a> points at the same-origin /dl Pages Function (see
// functions/dl/[[path]].js), which re-serves the backend video with a
// Content-Disposition attachment header. A plain cross-origin link to the
// Gradio file URL would save under a name-less blob id instead.
function renderVideo(doc, { containerId, videoId, downloadId, downloadName, url }) {
  const container = doc.getElementById(containerId);
  const video = doc.getElementById(videoId);
  const download = doc.getElementById(downloadId);

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
    download.removeAttribute("href");
    container.style.display = "none";
    return;
  }

  video.src = url;
  download.href = buildDownloadHref(url, downloadName);
  container.style.display = "block";
}

function clearResults(doc) {
  RESULT_TARGETS.forEach((target) => renderVideo(doc, { ...target, url: null }));
  doc.getElementById("log").textContent = "";
}

function renderResult(doc, result) {
  const urls = [result.video9x16Url, result.video16x9Url];
  RESULT_TARGETS.forEach((target, i) => renderVideo(doc, { ...target, url: urls[i] }));
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
