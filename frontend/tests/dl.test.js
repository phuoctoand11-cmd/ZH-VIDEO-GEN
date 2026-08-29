import { test } from "node:test";
import assert from "node:assert/strict";
import { onRequestGet } from "../functions/dl/[[path]].js";
import { SPACE_URL } from "../js/config.js";

const ALLOWED = `${SPACE_URL.replace(/\/$/, "")}/gradio_api/file=/tmp/gradio/abc/output_9x16.mp4`;

function ctx(url, { path = ["video-9-16.mp4"] } = {}) {
  return { request: new Request(url), params: { path } };
}

function withFetch(impl, run) {
  const original = globalThis.fetch;
  globalThis.fetch = impl;
  return Promise.resolve(run()).finally(() => {
    globalThis.fetch = original;
  });
}

test("400 when src is missing", async () => {
  const res = await onRequestGet(ctx("https://zh-video-gen.pages.dev/dl/video-9-16.mp4"));
  assert.equal(res.status, 400);
});

test("400 when src points at a host other than the backend", async () => {
  const evil = "https://evil.example.com/secret";
  const res = await onRequestGet(
    ctx(`https://zh-video-gen.pages.dev/dl/video-9-16.mp4?src=${encodeURIComponent(evil)}`)
  );
  assert.equal(res.status, 400);
});

test("proxies an allowed src and forces an attachment filename", async () => {
  let fetched = null;
  const res = await withFetch(
    async (u) => {
      fetched = String(u);
      return new Response("FAKE-MP4-BYTES", {
        status: 200,
        headers: { "Content-Type": "video/mp4", "Content-Length": "13" },
      });
    },
    () =>
      onRequestGet(
        ctx(`https://zh-video-gen.pages.dev/dl/video-9-16.mp4?src=${encodeURIComponent(ALLOWED)}`)
      )
  );

  assert.equal(fetched, ALLOWED);
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("Content-Type"), "video/mp4");
  assert.equal(res.headers.get("Content-Disposition"), 'attachment; filename="video-9-16.mp4"');
  assert.equal(await res.text(), "FAKE-MP4-BYTES");
});

test("502 when the backend file request fails", async () => {
  const res = await withFetch(
    async () => new Response("nope", { status: 404 }),
    () =>
      onRequestGet(
        ctx(`https://zh-video-gen.pages.dev/dl/video-9-16.mp4?src=${encodeURIComponent(ALLOWED)}`)
      )
  );
  assert.equal(res.status, 502);
});

test("sanitizes the filename from the path (no traversal, no quotes)", async () => {
  const res = await withFetch(
    async () => new Response("x", { status: 200, headers: { "Content-Type": "video/mp4" } }),
    () =>
      onRequestGet(
        ctx(`https://zh-video-gen.pages.dev/dl/x?src=${encodeURIComponent(ALLOWED)}`, {
          path: ['../../etc/pa"sswd.mp4'],
        })
      )
  );
  const cd = res.headers.get("Content-Disposition");
  assert.ok(cd.startsWith("attachment; filename="));
  assert.ok(!cd.includes('"sswd'));
  assert.ok(!cd.includes("/"));
  assert.ok(!cd.includes(".."));
});
