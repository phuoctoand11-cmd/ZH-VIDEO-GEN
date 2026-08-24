// frontend/js/gradioClient.js
import { Client } from "https://esm.sh/@gradio/client@1";

export async function connectClient(spaceUrl) {
  return Client.connect(spaceUrl);
}
