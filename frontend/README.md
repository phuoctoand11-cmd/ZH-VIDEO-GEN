# zh-video-gen frontend

Static site (no build step) that calls the zh-video-gen backend (Gradio app on Google Cloud Run) and renders the generated video.

## Download proxy (`functions/dl/[[path]].js`)

The backend's Gradio file URL is cross-origin and has no `Content-Disposition`, so a browser saves the video under a name-less blob id instead of `video-9-16.mp4`. The download links point at the same-origin Pages Function `/dl/<name>?src=<backend file url>`, which validates that `src` is on the configured backend origin (`SPACE_URL` in `js/config.js`), fetches it server-side, and re-serves it with `Content-Disposition: attachment; filename="<name>"`. See `tests/dl.test.js`.

## Deploy to Cloudflare Pages

1. In the Cloudflare dashboard, create a new Pages project connected to this GitHub repo.
2. Root directory: `frontend`
3. Build command: (leave empty)
4. Build output directory: `/`
5. Before or after the first deploy, edit `frontend/js/config.js` and set `SPACE_URL` to the deployed Cloud Run service's base URL (e.g. `https://zh-video-gen-backend-<project-number>.<region>.run.app`), then commit — Cloudflare Pages redeploys automatically on push.
