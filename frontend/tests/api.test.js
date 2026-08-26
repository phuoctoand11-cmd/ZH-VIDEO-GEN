import { test } from "node:test";
import assert from "node:assert/strict";
import { callGenerateVideo, callGeneratePreview, describeStatusEvent } from "../js/api.js";

// Stands in for the async-iterable job returned by @gradio/client's submit().
function fakeJob(events) {
  return (async function* () {
    for (const event of events) yield event;
  })();
}

const LIST_STATE = {
  mode: "Nhập danh sách",
  csvText: "吃,chī,ăn",
  topic: "",
  templateName: "zh-zh-vi",
  aspectRatios: ["9:16"],
};

test("callGenerateVideo builds the payload, calls the named endpoint, and parses the result", async () => {
  const fakeClient = {
    submit: (endpoint, payload, ...rest) => {
      assert.equal(endpoint, "/generate_video");
      assert.deepEqual(payload, ["Nhập danh sách", "吃,chī,ăn", "zh-zh-vi", ["9:16"]]);
      // A default-options @gradio/client only forwards "data" events unless
      // all_events (the 5th positional arg) is true — this must stay true or
      // every status/error-stage event is silently dropped before this test
      // (or production) ever sees it.
      assert.deepEqual(rest, [null, null, true]);
      return fakeJob([
        { type: "status", stage: "pending", queue: true, position: 1, size: 2 },
        { type: "status", stage: "generating", queue: false },
        { type: "data", data: [{ url: "https://x/a.mp4" }, null, "OK"] },
        { type: "status", stage: "complete", queue: false },
      ]);
    },
  };
  const connectClient = async (url) => {
    assert.equal(url, "https://fake-space");
    return fakeClient;
  };

  const result = await callGenerateVideo(LIST_STATE, { spaceUrl: "https://fake-space", connectClient });

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

test("callGenerateVideo reports every status event to onStatus", async () => {
  const events = [
    { type: "status", stage: "pending", queue: true, position: 3, size: 5 },
    { type: "status", stage: "generating", queue: false },
    { type: "data", data: [null, null, "Lỗi: template không hợp lệ"] },
    { type: "status", stage: "complete", queue: false },
  ];
  const connectClient = async () => ({ submit: () => fakeJob(events) });

  const seen = [];
  const result = await callGenerateVideo(LIST_STATE, {
    spaceUrl: "https://fake-space",
    connectClient,
    onStatus: (event) => seen.push(event.stage),
  });

  assert.deepEqual(seen, ["pending", "generating", "complete"]);
  // A backend failure still arrives as a normal data event with null videos.
  assert.equal(result.video9x16Url, null);
  assert.equal(result.video16x9Url, null);
  assert.equal(result.log, "Lỗi: template không hợp lệ");
});

test("callGenerateVideo throws when the job reports an error stage", async () => {
  const connectClient = async () => ({
    submit: () => fakeJob([{ type: "status", stage: "error", message: "queue full" }]),
  });

  await assert.rejects(
    () => callGenerateVideo(LIST_STATE, { spaceUrl: "https://fake-space", connectClient }),
    /queue full/
  );
});

test("callGenerateVideo throws when the job ends without a data event", async () => {
  const connectClient = async () => ({
    submit: () => fakeJob([{ type: "status", stage: "pending", queue: true }]),
  });

  await assert.rejects(
    () => callGenerateVideo(LIST_STATE, { spaceUrl: "https://fake-space", connectClient }),
    /Không nhận được kết quả/
  );
});

test("callGenerateVideo survives an onStatus callback that throws", async () => {
  const connectClient = async () => ({
    submit: () => fakeJob([
      { type: "status", stage: "pending", queue: true },
      { type: "data", data: ["https://x/a.mp4", null, "OK"] },
    ]),
  });

  const result = await callGenerateVideo(LIST_STATE, {
    spaceUrl: "https://fake-space",
    connectClient,
    onStatus: () => {
      throw new Error("DOM blew up");
    },
  });

  assert.equal(result.video9x16Url, "https://x/a.mp4");
});

test("callGeneratePreview builds the payload, calls the named endpoint, and returns csvText/log", async () => {
  const fakeClient = {
    submit: (endpoint, payload, ...rest) => {
      assert.equal(endpoint, "/generate_preview");
      assert.deepEqual(payload, ["Từ vựng theo chủ đề", "đồ ăn"]);
      assert.deepEqual(rest, [null, null, true]);
      return fakeJob([{ type: "data", data: ["冰,bīng,băng", "Đã tạo xong."] }]);
    },
  };
  const connectClient = async (url) => {
    assert.equal(url, "https://fake-space");
    return fakeClient;
  };

  const result = await callGeneratePreview(
    { mode: "Từ vựng theo chủ đề", topic: "đồ ăn" },
    { spaceUrl: "https://fake-space", connectClient }
  );

  assert.equal(result.csvText, "冰,bīng,băng");
  assert.equal(result.log, "Đã tạo xong.");
});

test("callGeneratePreview throws when the job reports an error stage", async () => {
  const connectClient = async () => ({
    submit: () => fakeJob([{ type: "status", stage: "error", message: "groq exploded" }]),
  });

  await assert.rejects(
    () => callGeneratePreview(
      { mode: "Từ vựng theo chủ đề", topic: "đồ ăn" },
      { spaceUrl: "https://fake-space", connectClient }
    ),
    /groq exploded/
  );
});

test("callGeneratePreview throws when the job ends without a data event", async () => {
  const connectClient = async () => ({
    submit: () => fakeJob([{ type: "status", stage: "pending", queue: true }]),
  });

  await assert.rejects(
    () => callGeneratePreview(
      { mode: "Từ vựng theo chủ đề", topic: "đồ ăn" },
      { spaceUrl: "https://fake-space", connectClient }
    ),
    /Không nhận được bản xem trước/
  );
});

test("describeStatusEvent renders queue position, generating, and error stages", () => {
  assert.match(describeStatusEvent({ stage: "pending", position: 2, size: 4 }), /vị trí 2\/4/);
  assert.match(describeStatusEvent({ stage: "pending", position: 0 }), /Đang chờ server/);
  assert.match(describeStatusEvent({ stage: "generating" }), /Đang tạo video/);
  assert.match(
    describeStatusEvent({ stage: "generating", progress_data: [{ desc: "Tổng hợp giọng nói", index: 2, length: 5 }] }),
    /Tổng hợp giọng nói\.\.\. 2\/5/
  );
  assert.match(describeStatusEvent({ stage: "error", message: "boom" }), /boom/);
});

test("describeStatusEvent returns null for unknown or malformed events", () => {
  assert.equal(describeStatusEvent(undefined), null);
  assert.equal(describeStatusEvent(null), null);
  assert.equal(describeStatusEvent("nonsense"), null);
  assert.equal(describeStatusEvent({}), null);
  assert.equal(describeStatusEvent({ stage: "something-new" }), null);
});
