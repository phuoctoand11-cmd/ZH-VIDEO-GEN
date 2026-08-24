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
