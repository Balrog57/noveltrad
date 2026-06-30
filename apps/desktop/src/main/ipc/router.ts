import { ipcMain } from "electron";
import { IPC_CHANNELS } from "./channels.js";
import { registerProjectHandlers } from "./handlers/project.js";
import { registerOllamaHandlers } from "./handlers/ollama.js";
import { registerSettingsHandlers } from "./handlers/settings.js";
import { registerWorkflowHandlers } from "./handlers/workflow.js";
import { registerUpdateHandlers } from "./handlers/update.js";
import { registerParagraphHandlers } from "./handlers/paragraph.js";

export function registerIpcRouter(): void {
  registerProjectHandlers();
  registerOllamaHandlers();
  registerSettingsHandlers();
  registerWorkflowHandlers();
  registerUpdateHandlers();
  registerParagraphHandlers();

  ipcMain.on("message", (event, channel) => {
    if (!IPC_CHANNELS.includes(channel)) {
      event.preventDefault();
      console.warn(`Unknown IPC channel: ${channel}`);
    }
  });
}
