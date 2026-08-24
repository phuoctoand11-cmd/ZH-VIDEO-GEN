// frontend/js/ui.js
import { validateForm } from "./validation.js";
import { callGenerateVideo } from "./api.js";
import { connectClient } from "./gradioClient.js";
import { SPACE_URL } from "./config.js";

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

function renderVideo(doc, { containerId, videoId, downloadId, url }) {
  const container = doc.getElementById(containerId);
  if (!url) {
    container.style.display = "none";
    return;
  }
  doc.getElementById(videoId).src = url;
  doc.getElementById(downloadId).href = url;
  container.style.display = "block";
}

function renderResult(doc, result) {
  renderVideo(doc, { containerId: "result-9-16", videoId: "video-9-16", downloadId: "download-9-16", url: result.video9x16Url });
  renderVideo(doc, { containerId: "result-16-9", videoId: "video-16-9", downloadId: "download-16-9", url: result.video16x9Url });
  doc.getElementById("log").textContent = result.log;
}

export function initApp(doc) {
  const form = doc.getElementById("generate-form");
  const submitBtn = doc.getElementById("submit-btn");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const state = readFormState(form);

    const validation = validateForm(state);
    if (!validation.valid) {
      setStatus(doc, validation.error);
      return;
    }

    submitBtn.disabled = true;
    setStatus(doc, "Đang tạo video... (nếu server đang ngủ, lần đầu có thể mất 1-2 phút để khởi động)");

    try {
      const result = await callGenerateVideo(state, { spaceUrl: SPACE_URL, connectClient });
      renderResult(doc, result);
      setStatus(doc, "Hoàn tất.");
    } catch (err) {
      setStatus(doc, `Lỗi: ${err.message}`);
    } finally {
      submitBtn.disabled = false;
    }
  });
}
