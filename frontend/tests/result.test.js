import { test } from "node:test";
import assert from "node:assert/strict";
import { parseApiResult, summarizeResult } from "../js/result.js";

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

test("rejects URLs with an unsafe scheme", () => {
  const result = parseApiResult(["javascript:alert(1)", { url: "  JavaScript:alert(2)" }, "log"]);
  assert.equal(result.video9x16Url, null);
  assert.equal(result.video16x9Url, null);
  assert.equal(result.log, "log");

  const dataUri = parseApiResult([{ url: "data:video/mp4;base64,AAAA" }, "file:///etc/passwd", ""]);
  assert.equal(dataUri.video9x16Url, null);
  assert.equal(dataUri.video16x9Url, null);
});

test("accepts http, https, and blob URLs", () => {
  const result = parseApiResult(["http://x/a.mp4", "blob:https://x/abcd", ""]);
  assert.equal(result.video9x16Url, "http://x/a.mp4");
  assert.equal(result.video16x9Url, "blob:https://x/abcd");
});

test("falls back to a nested gr.Video response shape", () => {
  const result = parseApiResult([{ video: { url: "https://x/9x16.mp4" } }, { video: {} }, ""]);
  assert.equal(result.video9x16Url, "https://x/9x16.mp4");
  assert.equal(result.video16x9Url, null);
});

test("returns a safe default for a non-array data argument", () => {
  for (const bad of [undefined, null, "oops", 42, {}]) {
    const result = parseApiResult(bad);
    assert.deepEqual(result, { video9x16Url: null, video16x9Url: null, log: "" });
  }
});

test("summarizeResult distinguishes real success from a silent backend failure", () => {
  assert.equal(summarizeResult({ video9x16Url: "https://x/a.mp4", video16x9Url: null, log: "" }), "Hoàn tất.");
  assert.equal(summarizeResult({ video9x16Url: null, video16x9Url: "https://x/b.mp4", log: "" }), "Hoàn tất.");
  assert.equal(
    summarizeResult({ video9x16Url: null, video16x9Url: null, log: "Lỗi: ffmpeg failed" }),
    "Không tạo được video — xem log bên dưới."
  );
  assert.equal(summarizeResult(undefined), "Không tạo được video — xem log bên dưới.");
});
