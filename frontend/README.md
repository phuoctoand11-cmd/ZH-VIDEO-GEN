# zh-video-gen frontend

Static site (no build step) that calls the zh-video-gen backend (Gradio app on Google Cloud Run) and renders the generated video.

## Deploy to Cloudflare Pages

1. In the Cloudflare dashboard, create a new Pages project connected to this GitHub repo.
2. Root directory: `frontend`
3. Build command: (leave empty)
4. Build output directory: `/`
5. Before or after the first deploy, edit `frontend/js/config.js` and set `SPACE_URL` to the deployed Cloud Run service's base URL (e.g. `https://zh-video-gen-backend-<project-number>.<region>.run.app`), then commit — Cloudflare Pages redeploys automatically on push.
