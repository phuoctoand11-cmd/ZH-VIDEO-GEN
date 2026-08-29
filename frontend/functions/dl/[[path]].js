// Cloudflare Pages Function serving /dl/<name>?src=<backend file url>.
//
// The download buttons can't point straight at the backend's Gradio file URL:
// it's cross-origin (so the browser ignores the <a download> name) and carries
// no Content-Disposition, so Chrome saves the video under a name-less blob id.
// This same-origin proxy re-serves the exact bytes with
// `Content-Disposition: attachment; filename="video-9-16.mp4"`, the one signal
// every browser and download manager respects.

import { SPACE_URL } from "../../js/config.js";

// Only the project's own backend may be proxied — never an arbitrary URL.
const ALLOWED_ORIGIN = new URL(SPACE_URL).origin;

// Allowlist: keep only characters safe in a filename and in a header value,
// then collapse any ".." runs. Anything else (path separators, quotes,
// control chars, CR/LF) is simply dropped.
function sanitizeFilename(segment) {
  if (typeof segment !== "string") return "";
  return segment
    .replace(/[^A-Za-z0-9._-]/g, "")
    .replace(/\.\.+/g, ".")
    .slice(0, 100);
}

export async function onRequestGet(context) {
  const { request, params } = context;
  const src = new URL(request.url).searchParams.get("src");
  if (!src) return new Response("missing src", { status: 400 });

  let target;
  try {
    target = new URL(src);
  } catch {
    return new Response("invalid src", { status: 400 });
  }
  if (target.origin !== ALLOWED_ORIGIN) {
    return new Response("src not allowed", { status: 400 });
  }

  const segments = Array.isArray(params.path) ? params.path : [params.path];
  const filename = sanitizeFilename(segments[segments.length - 1]) || "video.mp4";

  const upstream = await fetch(target.toString());
  if (!upstream.ok) {
    return new Response(`backend returned ${upstream.status}`, { status: 502 });
  }

  const headers = new Headers();
  headers.set("Content-Type", upstream.headers.get("Content-Type") || "video/mp4");
  const length = upstream.headers.get("Content-Length");
  if (length) headers.set("Content-Length", length);
  headers.set("Content-Disposition", `attachment; filename="${filename}"`);
  headers.set("Cache-Control", "no-store");

  return new Response(upstream.body, { status: 200, headers });
}
