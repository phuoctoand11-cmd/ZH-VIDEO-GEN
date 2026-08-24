import { buildApiPayload } from "./payload.js";
import { parseApiResult } from "./result.js";

export async function callGenerateVideo(state, { spaceUrl, connectClient }) {
  const client = await connectClient(spaceUrl);
  const payload = buildApiPayload(state);
  const response = await client.predict("/generate_video", payload);
  return parseApiResult(response.data);
}
