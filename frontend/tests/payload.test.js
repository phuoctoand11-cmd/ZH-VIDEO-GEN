import { test } from "node:test";
import assert from "node:assert/strict";
import { buildApiPayload, buildPreviewPayload } from "../js/payload.js";

test("builds generate_video payload in backend's expected parameter order", () => {
  const payload = buildApiPayload({
    mode: "Nhập danh sách",
    csvText: "吃,chī,ăn",
    templateName: "zh-zh-vi",
    aspectRatios: ["9:16", "16:9"],
  });
  assert.deepEqual(payload, ["Nhập danh sách", "吃,chī,ăn", "zh-zh-vi", ["9:16", "16:9"]]);
});

test("defaults missing csvText to empty string", () => {
  const payload = buildApiPayload({ mode: "Từ vựng theo chủ đề", templateName: "zh-vi-zh", aspectRatios: ["9:16"] });
  assert.deepEqual(payload, ["Từ vựng theo chủ đề", "", "zh-vi-zh", ["9:16"]]);
});

test("builds generate_preview payload in backend's expected parameter order", () => {
  const payload = buildPreviewPayload({ mode: "Từ vựng theo chủ đề", topic: "đồ ăn" });
  assert.deepEqual(payload, ["Từ vựng theo chủ đề", "đồ ăn"]);
});

test("defaults missing topic to empty string", () => {
  const payload = buildPreviewPayload({ mode: "Hội thoại theo chủ đề" });
  assert.deepEqual(payload, ["Hội thoại theo chủ đề", ""]);
});
