import { ipcMain } from "electron";
import { IPC_CHANNELS } from "./channels.js";
import { logger } from "../utils/logger.js";

/** Charge chaque handler independamment. Si un handler echoue, les autres survivent. */
export async function registerIpcRouter(): Promise<void> {
  logger.debug("[ROUTER] registerIpcRouter called");

  const handlers: Array<[string, () => Promise<void>]> = [
    ["ollama",   async () => { const m = await import("./handlers/ollama.js"); m.registerOllamaHandlers(); }],
    ["settings", async () => { const m = await import("./handlers/settings.js"); m.registerSettingsHandlers(); }],
    ["project",  async () => { const m = await import("./handlers/project.js"); m.registerProjectHandlers(); }],
    ["workflow", async () => { const m = await import("./handlers/workflow.js"); m.registerWorkflowHandlers(); }],
    ["update",   async () => { const m = await import("./handlers/update.js"); m.registerUpdateHandlers(); }],
    ["paragraph",async () => { const m = await import("./handlers/paragraph.js"); m.registerParagraphHandlers(); }],
    ["lexicon",  async () => { const m = await import("./handlers/lexicon.js"); m.registerLexiconHandlers(); }],
    ["export",   async () => { const m = await import("./handlers/export.js"); m.registerExportHandlers(); }],
    ["history",  async () => { const m = await import("./handlers/history.js"); m.registerHistoryHandlers(); }],
    ["tm",       async () => { const m = await import("./handlers/tm.js"); m.registerTmHandlers(); }],
    ["plugins",  async () => { const m = await import("./handlers/plugins.js"); m.registerPluginHandlers(); }],
    ["ai",       async () => { const m = await import("./handlers/ai.js"); m.registerAiHandlers(); }],
  ];

  let loaded = 0, failed = 0;

  for (const [name, loader] of handlers) {
    try {
      logger.debug(`[ROUTER] Loading "${name}"...`);
      await loader();
      logger.debug(`[ROUTER] OK "${name}"`);
      loaded++;
    } catch (err) {
      failed++;
      const e = err as Error;
      logger.debug(`[ROUTER] FAILED "${name}": ${e.message}`, e);
    }
  }

  logger.info(`[ROUTER] Done: ${loaded} loaded, ${failed} failed`);

  ipcMain.on("message", (event, channel) => {
    if (!IPC_CHANNELS.includes(channel)) {
      event.preventDefault();
      logger.warn(`Unknown IPC channel: ${channel}`);
    }
  });
}
