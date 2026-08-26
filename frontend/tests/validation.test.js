// frontend/tests/validation.test.js
import { test } from "node:test";
import assert from "node:assert/strict";
import { validateForm, validatePreviewRequest } from "../js/validation.js";

test("valid manual mode with csv text and aspect ratio", () => {
  const result = validateForm({ mode: "Nhập danh sách", csvText: "吃,chī,ăn", aspectRatios: ["9:16"] });
  assert.equal(result.valid, true);
  assert.equal(result.error, null);
});

test("manual mode rejects empty csv text", () => {
  const result = validateForm({ mode: "Nhập danh sách", csvText: "   ", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
  assert.match(result.error, /CSV/);
});

test("vocab topic mode rejects empty csv text (must run Xem trước first)", () => {
  const result = validateForm({ mode: "Từ vựng theo chủ đề", csvText: "", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
  assert.match(result.error, /Xem trước/i);
});

test("dialogue topic mode rejects empty csv text (must run Xem trước first)", () => {
  const result = validateForm({ mode: "Hội thoại theo chủ đề", csvText: "", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
  assert.match(result.error, /Xem trước/i);
});

test("vocab topic mode accepts csv text produced by Xem trước", () => {
  const result = validateForm({
    mode: "Từ vựng theo chủ đề",
    csvText: "冰,bīng,băng",
    aspectRatios: ["9:16"],
  });
  assert.equal(result.valid, true);
});

test("rejects empty aspect ratios", () => {
  const result = validateForm({ mode: "Nhập danh sách", csvText: "吃,chī,ăn", aspectRatios: [] });
  assert.equal(result.valid, false);
  assert.match(result.error, /tỉ lệ/i);
});

test("rejects unknown mode", () => {
  const result = validateForm({ mode: "???", csvText: "", aspectRatios: ["9:16"] });
  assert.equal(result.valid, false);
});

test("validatePreviewRequest rejects manual mode", () => {
  const result = validatePreviewRequest({ mode: "Nhập danh sách", topic: "đồ ăn" });
  assert.equal(result.valid, false);
});

test("validatePreviewRequest rejects empty topic", () => {
  const result = validatePreviewRequest({ mode: "Từ vựng theo chủ đề", topic: "  " });
  assert.equal(result.valid, false);
  assert.match(result.error, /chủ đề/i);
});

test("validatePreviewRequest accepts a filled topic for a topic mode", () => {
  const result = validatePreviewRequest({ mode: "Hội thoại theo chủ đề", topic: "chào hỏi" });
  assert.equal(result.valid, true);
});
