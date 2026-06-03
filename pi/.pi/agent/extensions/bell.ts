import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execFile } from "node:child_process";

export default function (pi: ExtensionAPI) {
  pi.on("agent_end", async () => {
    execFile("paplay", ["/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"], () => {});
  });
}
