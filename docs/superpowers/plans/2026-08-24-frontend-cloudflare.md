# Frontend (Cloudflare Pages) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `frontend/` — a static HTML/CSS/JS site (no build step) that collects lesson input, calls the deployed HF Space's Gradio API from the browser, and renders the returned video(s) — deployable to Cloudflare Pages by pointing it at this directory.

**Architecture:** Pure-logic pieces (form validation, API payload building, API response parsing) live in small standalone ES modules, each independently unit-tested with Node's built-in test runner (`node --test`) — no npm install, no bundler. A thin `gradioClient.js` wraps `@gradio/client`, imported at runtime via an ESM CDN (`esm.sh`), so the site ships as plain static files. `ui.js` wires the DOM to the pure-logic modules; it has no automated test (no DOM in Node) and is verified manually in a browser.

**Tech Stack:** Vanilla HTML/CSS/JS (ES modules), `@gradio/client` via `https://esm.sh/@gradio/client` (no local dependency, no build step), Node's built-in `node:test` for unit tests, Cloudflare Pages (static site, no build command).

**Spec:** `docs/superpowers/specs/2026-08-24-zh-video-gen-design.md` (Frontend section, Data flow, Xử lý lỗi)

## Global Constraints

- No build step: the deployed site is exactly the files in `frontend/`, served as-is by Cloudflare Pages.
- Backend contract (from the backend implementation, already built): the Gradio endpoint is named `generate_video` (`api_name="generate_video"`), called with positional args in this exact order: `mode: str`, `csv_text: str`, `topic: str`, `template_name: str`, `aspect_ratios: list[str]`. It returns 3 outputs in order: `video_9_16` (video file or `null`), `video_16_9` (video file or `null`), `log: str`.
- `mode` must be exactly `"Nhập danh sách"` or `"Chủ đề tự động"` (these exact strings are what the backend's Gradio `Radio` component uses and branches on).
- Known template names, shipped by the backend, to hardcode as `<select>` options: `zh-zh-vi`, `zh-vi-zh`.
- Aspect ratio values must be exactly `"9:16"` and/or `"16:9"`.
- The HF Space may be asleep (cold start) on first request — the UI must show a "server is starting, please wait" status rather than looking frozen, and must not assume a fast response.
- A video output can be `null` in a valid response (e.g. only one aspect ratio was requested, or that ratio's assembly failed) — the UI must handle a missing video gracefully, not crash.
- Tests run manually via `node --test tests/` from `frontend/`; no CI.

---

## Task 1: Scaffolding

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/css/style.css`
- Create: `frontend/js/config.js`
- Create: `frontend/README.md`
- Create: `frontend/tests/.gitkeep`

**Interfaces:**
- Produces: `SPACE_URL` (exported string constant from `config.js`, placeholder value the user fills in after the HF Space exists) — consumed by Task 6's `ui.js`.

- [ ] **Step 1: Create directories**

```bash
mkdir -p frontend/css frontend/js frontend/tests
touch frontend/tests/.gitkeep
```

- [ ] **Step 2: Write `frontend/package.json`**

```json
{
  "name": "zh-video-gen-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test tests/"
  }
}
```

- [ ] **Step 3: Write `frontend/js/config.js`**

```js
// frontend/js/config.js
export const SPACE_URL = "REPLACE_WITH_HF_SPACE_URL";
```

- [ ] **Step 4: Write `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tạo video dạy tiếng Trung</title>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <h1>Tạo video dạy tiếng Trung song ngữ Việt-Trung</h1>

  <form id="generate-form">
    <fieldset>
      <legend>Chế độ nhập</legend>
      <label><input type="radio" name="mode" value="Nhập danh sách" checked> Nhập danh sách</label>
      <label><input type="radio" name="mode" value="Chủ đề tự động"> Chủ đề tự động</label>
    </fieldset>

    <label for="csv-text">Danh sách CSV (hanzi,pinyin,meaning_vi)</label>
    <textarea id="csv-text" rows="8" placeholder="hanzi,pinyin,meaning_vi&#10;吃,chī,ăn"></textarea>

    <label for="topic">Chủ đề (chế độ tự động)</label>
    <input type="text" id="topic" placeholder="ví dụ: đồ ăn">

    <label for="template-name">Template trình tự audio</label>
    <select id="template-name">
      <option value="zh-zh-vi">zh-zh-vi</option>
      <option value="zh-vi-zh">zh-vi-zh</option>
    </select>

    <fieldset>
      <legend>Tỉ lệ khung hình</legend>
      <label><input type="checkbox" name="aspect_ratio" value="9:16" checked> 9:16</label>
      <label><input type="checkbox" name="aspect_ratio" value="16:9"> 16:9</label>
    </fieldset>

    <button type="submit" id="submit-btn">Tạo video</button>
  </form>

  <p id="status"></p>

  <div id="results">
    <div id="result-9-16" style="display:none">
      <video id="video-9-16" controls></video>
      <a id="download-9-16" download>Tải video 9:16</a>
    </div>
    <div id="result-16-9" style="display:none">
      <video id="video-16-9" controls></video>
      <a id="download-16-9" download>Tải video 16:9</a>
    </div>
    <pre id="log"></pre>
  </div>

  <script type="module" src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 5: Write `frontend/css/style.css`**

```css
body {
  font-family: system-ui, sans-serif;
  max-width: 720px;
  margin: 2rem auto;
  padding: 0 1rem;
  line-height: 1.5;
}

form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

fieldset {
  border: 1px solid #ccc;
  border-radius: 6px;
}

textarea {
  font-family: monospace;
}

#status {
  font-weight: bold;
}

video {
  max-width: 100%;
  margin-top: 1rem;
  display: block;
}

#results > div {
  margin-top: 1rem;
}

#results a[download] {
  display: inline-block;
  margin-top: 0.25rem;
}

#log {
  white-space: pre-wrap;
  background: #f5f5f5;
  padding: 0.5rem;
  border-radius: 6px;
}
```

- [ ] **Step 6: Write `frontend/README.md`**

```markdown
# zh-video-gen frontend

Static site (no build step) that calls the zh-video-gen backend (Hugging Face Space) and renders the generated video.

## Deploy to Cloudflare Pages

1. In the Cloudflare dashboard, create a new Pages project connected to this GitHub repo.
2. Root directory: `frontend`
3. Build command: (leave empty)
4. Build output directory: `/`
5. Before or after the first deploy, edit `frontend/js/config.js` and set `SPACE_URL` to your deployed Hugging Face Space's base URL (e.g. `https://<username>-zh-video-gen.hf.space`), then commit — Cloudflare Pages redeploys automatically on push.
```

- [ ] **Step 7: Verify scaffolding**

Run: `cd frontend && node -e "import('./js/config.js').then(m => console.log(m.SPACE_URL))"`
Expected: prints `REPLACE_WITH_HF_SPACE_URL`, no import errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/index.html frontend/css/style.css frontend/js/config.js frontend/README.md frontend/tests/.gitkeep
git commit -m "chore: scaffold frontend static site"
```

---

## Task 2: Form validation

**Files:**
- Create: `frontend/js/validation.js`
- Test: `frontend/tests/validation.test.js`

**Interfaces:**
- Produces: `validateForm(state: {mode, csvText, topic, aspectRatios}) -> {valid: boolean, error: string|null}`, used by Task 6's `ui.js`.

- [ ] **Step 1: Write the failing test**

```js
// frontend/tests/validation.test.js
import { test } from "node:test";
import assert from "node:assert/strict";
import { validateForm } from "../js/validation.js";

test("valid manual mode with csv text and aspect ratio", () => {
  const result = validateForm({ mode: "Nhập danh sách", csvText: "吃,chī,ăn", topic: "", aspectRatios: ["9:16"] });
  assert.equal(result.valid, true);
  assert.equal(result.error, null);
});

test("manual mode rejects empty csv text", () => {
  const result = validateForm({ mode: "Nhập danh sách", csvText: "   ", topic: "", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
  assert.match(result.error, /CSV/);
});

test("auto mode rejects empty topic", () => {
  const result = validateForm({ mode: "Chủ đề tự động", csvText: "", topic: "  ", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
  assert.match(result.error, /chủ đề/i);
});

test("rejects empty aspect ratios", () => {
  const result = validateForm({ mode: "Nhập danh sách", csvText: "吃,chī,ăn", topic: "", aspectRatios: [] });
  assert.equal(result.valid, false);
  assert.match(result.error, /tỉ lệ/i);
});

test("rejects unknown mode", () => {
  const result = validateForm({ mode: "???", csvText: "", topic: "", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && node --test tests/validation.test.js`
Expected: FAIL — cannot find module `../js/validation.js`

- [ ] **Step 3: Write minimal implementation**

```js
// frontend/js/validation.js
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && node --test tests/validation.test.js`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/js/validation.js frontend/tests/validation.test.js
git commit -m "feat: validate form input before calling the API"
```

---

## Task 3: API payload builder

**Files:**
- Create: `frontend/js/payload.js`
- Test: `frontend/tests/payload.test.js`

**Interfaces:**
- Produces: `buildApiPayload(state: {mode, csvText, topic, templateName, aspectRatios}) -> [mode, csvText, topic, templateName, aspectRatios]`, used by Task 5's `api.js`. The array order matches the backend's `generate_video(mode, csv_text, topic, template_name, aspect_ratios)` parameter order exactly.

- [ ] **Step 1: Write the failing test**

```js
// frontend/tests/payload.test.js
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildApiPayload } from "../js/payload.js";

test("builds payload in backend's expected parameter order", () => {
  const payload = buildApiPayload({
    mode: "Nhập danh sách",
    csvText: "吃,chī,ăn",
    topic: "",
    templateName: "zh-zh-vi",
    aspectRatios: ["9:16", "16:9"],
  });
  assert.deepEqual(payload, ["Nhập danh sách", "吃,chī,ăn", "", "zh-zh-vi", ["9:16", "16:9"]]);
});

test("defaults missing csvText/topic to empty string", () => {
  const payload = buildApiPayload({ mode: "Chủ đề tự động", templateName: "zh-vi-zh", aspectRatios: ["9:16"] });
  assert.deepEqual(payload, ["Chủ đề tự động", "", "", "zh-vi-zh", ["9:16"]]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && node --test tests/payload.test.js`
Expected: FAIL — cannot find module `../js/payload.js`

- [ ] **Step 3: Write minimal implementation**

```js
// frontend/js/payload.js
export function buildApiPayload(state) {
  return [
    state.mode,
    state.csvText ?? "",
    state.topic ?? "",
    state.templateName,
    state.aspectRatios,
  ];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && node --test tests/payload.test.js`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/js/payload.js frontend/tests/payload.test.js
git commit -m "feat: build API payload matching backend parameter order"
```

---

## Task 4: API result parser

**Files:**
- Create: `frontend/js/result.js`
- Test: `frontend/tests/result.test.js`

**Interfaces:**
- Produces: `parseApiResult(data: [videoOrNull, videoOrNull, string]) -> {video9x16Url: string|null, video16x9Url: string|null, log: string}`, used by Task 5's `api.js`. Handles a Gradio video output shaped as `null`, a plain URL string, or a `{url: string, ...}` object (Gradio's FileData shape).

- [ ] **Step 1: Write the failing test**

```js
// frontend/tests/result.test.js
import { test } from "node:test";
import assert from "node:assert/strict";
import { parseApiResult } from "../js/result.js";

test("parses both videos present as FileData objects", () => {
  const result = parseApiResult([{ url: "https://x/9x16.mp4" }, { url: "https://x/16x9.mp4" }, "Hoàn tất"]);
  assert.equal(result.video9x16Url, "https://x/9x16.mp4");
  assert.equal(result.video16x9Url, "https://x/16x9.mp4");
  assert.equal(result.log, "Hoàn tất");
});

test("handles a missing video as null", () => {
  const result = parseApiResult([null, { url: "https://x/16x9.mp4" }, "Lỗi mục 'X'"]);
  assert.equal(result.video9x16Url, null);
  assert.equal(result.video16x9Url, "https://x/16x9.mp4");
  assert.equal(result.log, "Lỗi mục 'X'");
});

test("handles a plain string URL shape", () => {
  const result = parseApiResult(["https://x/a.mp4", null, ""]);
  assert.equal(result.video9x16Url, "https://x/a.mp4");
  assert.equal(result.video16x9Url, null);
  assert.equal(result.log, "");
});

test("defaults a missing log to empty string", () => {
  const result = parseApiResult([null, null, null]);
  assert.equal(result.log, "");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && node --test tests/result.test.js`
Expected: FAIL — cannot find module `../js/result.js`

- [ ] **Step 3: Write minimal implementation**

```js
// frontend/js/result.js
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && node --test tests/result.test.js`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/js/result.js frontend/tests/result.test.js
git commit -m "feat: parse Gradio API response into video URLs and log"
```

---

## Task 5: API call orchestration

**Files:**
- Create: `frontend/js/api.js`
- Test: `frontend/tests/api.test.js`

**Interfaces:**
- Consumes: `buildApiPayload` (Task 3), `parseApiResult` (Task 4).
- Produces: `callGenerateVideo(state, {spaceUrl, connectClient}) -> Promise<{video9x16Url, video16x9Url, log}>`, used by Task 6's `ui.js`. `connectClient` is an injected `async (spaceUrl) -> {predict(endpoint, payload) -> Promise<{data: [...]}>}` — production code injects the real `@gradio/client`-backed implementation from `gradioClient.js` (Task 6); tests inject a fake, so this module needs no network access to test.

- [ ] **Step 1: Write the failing test**

```js
// frontend/tests/api.test.js
import { test } from "node:test";
import assert from "node:assert/strict";
import { callGenerateVideo } from "../js/api.js";

test("callGenerateVideo builds the payload, calls the named endpoint, and parses the result", async () => {
  const fakeClient = {
    predict: async (endpoint, payload) => {
      assert.equal(endpoint, "/generate_video");
      assert.deepEqual(payload, ["Nhập danh sách", "吃,chī,ăn", "", "zh-zh-vi", ["9:16"]]);
      return { data: [{ url: "https://x/a.mp4" }, null, "OK"] };
    },
  };
  const connectClient = async (url) => {
    assert.equal(url, "https://fake-space");
    return fakeClient;
  };

  const result = await callGenerateVideo(
    { mode: "Nhập danh sách", csvText: "吃,chī,ăn", topic: "", templateName: "zh-zh-vi", aspectRatios: ["9:16"] },
    { spaceUrl: "https://fake-space", connectClient }
  );

  assert.equal(result.video9x16Url, "https://x/a.mp4");
  assert.equal(result.video16x9Url, null);
  assert.equal(result.log, "OK");
});

test("callGenerateVideo propagates a connect failure", async () => {
  const connectClient = async () => {
    throw new Error("space is sleeping");
  };
  await assert.rejects(
    () => callGenerateVideo(
      { mode: "Nhập danh sách", csvText: "x", topic: "", templateName: "zh-zh-vi", aspectRatios: ["9:16"] },
      { spaceUrl: "https://fake-space", connectClient }
    ),
    /space is sleeping/
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && node --test tests/api.test.js`
Expected: FAIL — cannot find module `../js/api.js`

- [ ] **Step 3: Write minimal implementation**

```js
// frontend/js/api.js
import { buildApiPayload } from "./payload.js";
import { parseApiResult } from "./result.js";

export async function callGenerateVideo(state, { spaceUrl, connectClient }) {
  const client = await connectClient(spaceUrl);
  const payload = buildApiPayload(state);
  const response = await client.predict("/generate_video", payload);
  return parseApiResult(response.data);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && node --test tests/api.test.js`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/js/api.js frontend/tests/api.test.js
git commit -m "feat: orchestrate the generate_video API call"
```

---

## Task 6: Browser wiring (Gradio client, DOM, entrypoint)

**Files:**
- Create: `frontend/js/gradioClient.js`
- Create: `frontend/js/ui.js`
- Create: `frontend/js/app.js`

**Interfaces:**
- Consumes: `validateForm` (Task 2), `callGenerateVideo` (Task 5), `SPACE_URL` (Task 1's `config.js`).
- Produces: `initApp(document)` (called by `app.js` on load) — this is the site's entrypoint, has no automated test (DOM-dependent), verified manually per Step 4 below.

**Note:** `gradioClient.js` does a real network-backed ESM import of `@gradio/client` from a CDN — this cannot run under Node's test runner without a browser or a fetch-capable polyfill, and is intentionally excluded from automated tests, matching how the backend plan left its real (network-dependent) LLM wrapper untested by design.

- [ ] **Step 1: Write `frontend/js/gradioClient.js`**

```js
// frontend/js/gradioClient.js
import { Client } from "https://esm.sh/@gradio/client@1";

export async function connectClient(spaceUrl) {
  return Client.connect(spaceUrl);
}
```

- [ ] **Step 2: Write `frontend/js/ui.js`**

```js
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
```

- [ ] **Step 3: Write `frontend/js/app.js`**

```js
// frontend/js/app.js
import { initApp } from "./ui.js";

initApp(document);
```

- [ ] **Step 4: Manual verification in a browser**

Run: `cd frontend && npx --yes serve .` (or any static file server), open the printed local URL.

Expected, checked by hand:
1. Page loads with no console errors.
2. Submitting with "Nhập danh sách" mode and empty CSV text shows the validation error under the form, no network call made.
3. Leave `SPACE_URL` as the placeholder, submit valid input — the status area shows the "Đang tạo video..." message, then an error mentioning the placeholder URL (proving the call path is wired end to end, even without a real Space to call yet).

- [ ] **Step 5: Commit**

```bash
git add frontend/js/gradioClient.js frontend/js/ui.js frontend/js/app.js
git commit -m "feat: wire the DOM to the API layer and the real Gradio client"
```

---

## Task 7: Deploy to Cloudflare Pages and connect to the live HF Space

**Files:** `frontend/js/config.js` (edit, once the Space URL is known)

- [ ] **Step 1: Create the Cloudflare Pages project**

Manual steps (no CLI credentials available to automate this):
1. Push this branch and merge it (or open a PR) so `frontend/` exists on the repo's default branch — Cloudflare Pages deploys from a branch.
2. In the Cloudflare dashboard: Workers & Pages → Create → Pages → Connect to Git → select this repo.
3. Root directory: `frontend`. Build command: leave empty. Build output directory: `/`.
4. Deploy.

- [ ] **Step 2: Point the frontend at the deployed HF Space**

Once the backend plan's Task 16 (Hugging Face Space creation) is complete and you have the Space's base URL (e.g. `https://<username>-zh-video-gen.hf.space`):

```js
// frontend/js/config.js
export const SPACE_URL = "https://<username>-zh-video-gen.hf.space";
```

Commit and push — Cloudflare Pages redeploys automatically.

- [ ] **Step 3: End-to-end verification**

On the deployed Cloudflare Pages URL:
1. Submit "Nhập danh sách" with a small real CSV (e.g. `hanzi,pinyin,meaning_vi\n吃,,ăn\n`), template `zh-zh-vi`, aspect ratio `9:16`.
2. Confirm the status shows the "đang khởi động" message if the Space was asleep, then a playable video appears.
3. Submit "Chủ đề tự động" with a topic, confirm a lesson is generated and a video produced.

Expected: both flows produce a playable video in the browser with no unhandled JS errors, matching the backend's own Task 16 verification.
