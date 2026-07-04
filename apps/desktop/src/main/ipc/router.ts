import { ipcMain } from "electron";
import fs from "node:fs";
import path from "node:path";
import { IPC_CHANNELS } from "./channels.js";
import { logger } from "../utils/logger.js";

function debugLog(msg: string): void {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  console.log(msg);
  try {
    const dir = path.join(process.env.APPDATA || "", "NovelTrad");
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(path.join(dir, "debug.log"), line, "utf-8");
  } catch { /* best effort */ }
}

/** Charge chaque handler independamment. Si un handler echoue, les autres survivent. */
export async function registerIpcRouter(): Promise<void> {
  debugLog("[ROUTER] registerIpcRouter called");

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
      debugLog(`[ROUTER] Loading "${name}"...`);
      await loader();
      debugLog(`[ROUTER] OK "${name}"`);
      loaded++;
    } catch (err) {
      failed++;
      const e = err as Error;
      debugLog(`[ROUTER] FAILED "${name}": ${e.message}\n${e.stack}`);
    }
  }

  debugLog(`[ROUTER] Done: ${loaded} loaded, ${failed} failed`);
  logger.info(`[IPC] Handlers: ${loaded} loaded, ${failed} failed`);

  ipcMain.on("message", (event, channel) => {
    if (!IPC_CHANNELS.includes(channel)) {
      event.preventDefault();
      logger.warn(`Unknown IPC channel: ${channel}`);
    }
  });
}
