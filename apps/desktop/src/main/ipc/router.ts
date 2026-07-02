import { ipcMain } from "electron";
import { IPC_CHANNELS } from "./channels.js";
import { registerProjectHandlers } from "./handlers/project.js";
import { registerOllamaHandlers } from "./handlers/ollama.js";
import { registerSettingsHandlers } from "./handlers/settings.js";
import { registerWorkflowHandlers } from "./handlers/workflow.js";
import { registerUpdateHandlers } from "./handlers/update.js";
import { registerParagraphHandlers } from "./handlers/paragraph.js";
import { registerLexiconHandlers } from "./handlers/lexicon.js";
import { registerExportHandlers } from "./handlers/export.js";
import { registerHistoryHandlers } from "./handlers/history.js";
import { registerTmHandlers } from "./handlers/tm.js";
import { registerPluginHandlers } from "./handlers/plugins.js";
import { logger } from "../utils/logger.js";

export function registerIpcRouter(): void {
  registerProjectHandlers();
  registerOllamaHandlers();
  registerSettingsHandlers();
  registerWorkflowHandlers();
  registerUpdateHandlers();
  registerParagraphHandlers();
  registerLexiconHandlers();
  registerExportHandlers();
  registerHistoryHandlers();
  registerTmHandlers();
  registerPluginHandlers();

  ipcMain.on("message", (event, channel) => {
    if (!IPC_CHANNELS.includes(channel)) {
      event.preventDefault();
      logger.warn(`Unknown IPC channel: ${channel}`);
    }
  });
}
