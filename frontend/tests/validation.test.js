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
