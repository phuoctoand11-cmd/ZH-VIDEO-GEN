import { buildApiPayload, buildPreviewPayload } from "./payload.js";
import { parseApiResult } from "./result.js";

const ENDPOINT = "/generate_video";
const PREVIEW_ENDPOINT = "/generate_preview";

// Turns a @gradio/client "status" event into human-readable Vietnamese status
// text, or null when the event carries nothing worth showing. Written
// defensively: an unexpected event shape yields null rather than throwing.
export function describeStatusEvent(event) {
  if (!event || typeof event !== "object") return null;

  switch (event.stage) {
    case "pending": {
      const position = event.position;
      if (typeof position === "number" && position > 0) {
        const size = typeof event.size === "number" ? `/${event.size}` : "";
        return `Đang xếp hàng chờ server... vị trí ${position}${size}`;
      }
      return "Đang chờ server xử lý... (server ngủ có thể mất 1-2 phút để khởi động)";
    }
    case "generating": {
      const progress = Array.isArray(event.progress_data) ? event.progress_data[0] : null;
      if (progress && typeof progress === "object") {
        const desc = typeof progress.desc === "string" && progress.desc ? progress.desc : "Đang tạo video";
        if (typeof progress.index === "number" && typeof progress.length === "number") {
          return `${desc}... ${progress.index}/${progress.length}`;
        }
        return `${desc}...`;
      }
      return "Đang tạo video... (TTS + hình ảnh + ghép video)";
    }
    case "complete":
      return "Đang tải kết quả...";
    case "error":
      return `Lỗi: ${event.message || "server báo lỗi không rõ"}`;
    default:
      return null;
  }
}

export async function callGenerateVideo(state, { spaceUrl, connectClient, onStatus }) {
  const client = await connectClient(spaceUrl);
  const payload = buildApiPayload(state);
  // submit() returns an async-iterable job that yields "status" events while
  // the Space queues/generates and a "data" event carrying the outputs.
  // The 5th arg (all_events) must be true, or a default-options @gradio/client
  // only forwards "data" events and every status/error-stage event is dropped
  // before it ever reaches this loop.
  const job = client.submit(ENDPOINT, payload, null, null, true);

  let finalData = null;
  let receivedData = false;

  for await (const event of job) {
    if (!event || typeof event !== "object") continue;

    if (event.type === "data") {
      if (Array.isArray(event.data)) {
        finalData = event.data;
        receivedData = true;
      }
      continue;
    }

    if (event.type === "status") {
      if (typeof onStatus === "function") {
        // A failing UI callback must never abort an in-flight generation.
        try {
          onStatus(event);
        } catch {
          /* ignore */
        }
      }
      if (event.stage === "error") {
        throw new Error(event.message || "Server báo lỗi khi tạo video.");
      }
    }
  }

  if (!receivedData) {
    throw new Error("Không nhận được kết quả từ server.");
  }

  return parseApiResult(finalData);
}

// Asks the LLM to draft content for a topic mode and returns it as editable
// CSV text, without rendering any video yet — mirrors callGenerateVideo's
// submit()/event-loop shape but against the lighter /generate_preview
// endpoint, which only ever returns (csvText, log), never a video.
export async function callGeneratePreview(state, { spaceUrl, connectClient }) {
  const client = await connectClient(spaceUrl);
  const payload = buildPreviewPayload(state);
  const job = client.submit(PREVIEW_ENDPOINT, payload, null, null, true);

  let finalData = null;
  let receivedData = false;

  for await (const event of job) {
    if (!event || typeof event !== "object") continue;

    if (event.type === "data") {
      if (Array.isArray(event.data)) {
        finalData = event.data;
        receivedData = true;
      }
      continue;
    }

    if (event.type === "status" && event.stage === "error") {
      throw new Error(event.message || "Server báo lỗi khi tạo bản xem trước.");
    }
  }

  if (!receivedData) {
    throw new Error("Không nhận được bản xem trước từ server.");
  }

  const [csvText, log] = finalData;
  return { csvText: typeof csvText === "string" ? csvText : "", log: log ?? "" };
}
