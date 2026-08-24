// frontend/js/gradioClient.js
import { Client } from "https://esm.sh/@gradio/client@2.5.0";

export async function connectClient(spaceUrl) {
  return Client.connect(spaceUrl);
}
