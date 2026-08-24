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
