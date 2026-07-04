import { ipcMain } from "electron";
import { z } from "zod";
import { OllamaManager } from "../../managers/OllamaManager.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { logger } from "../../utils/logger.js";

// ── Schémas de validation Zod (SDD §16.3) ──────────────────────────────

const hostSchema = z.string().min(1).optional();
const modelNameSchema = z.string().min(1, { message: "model name requis" });

const settings = new SettingsManager();
const ollamaManager = new OllamaManager(settings);

export function registerOllamaHandlers(): void {
  logger.debug("[IPC] Ollama handlers registered");

  ipcMain.handle("ollama:is-available", async (_event, host?: unknown) => {
    logger.debug(`[IPC] ollama:is-available called, host=${host}`);
    hostSchema.parse(host);
    return ollamaManager.isAvailable();
  });

  ipcMain.handle("ollama:list-models", async (_event, host?: unknown) => {
    hostSchema.parse(host);
    return ollamaManager.listModels();
  });

  ipcMain.handle("ollama:pull-model", async (event, name: unknown) => {
    const parsed = z.object({ name: modelNameSchema }).parse({ name });
    await ollamaManager.pullModel(parsed.name, (progress) => {
      event.sender.send("ollama:pull-progress", progress);
    });
    return { done: true };
  });

  /** SDD §2.5 : test rapide du modèle en envoyant une courte requête */
  ipcMain.handle("ollama:test-model", async (_event, modelName: unknown) => {
    const parsed = z.string().min(1).parse(modelName);
    try {
      const result = await ollamaManager.testModel(parsed);
      return { success: true, response: result };
    } catch (e) {
      logger.warn(`[ollama] Test du modèle "${parsed}" échoué : ${(e as Error).message}`);
      return { success: false, error: (e as Error).message };
    }
  });
}
