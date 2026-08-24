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
