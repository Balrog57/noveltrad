import { ipcMain } from "electron";
import { z } from "zod";
import { OllamaManager } from "../../managers/OllamaManager.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { logger } from "../../utils/logger.js";
// WS-2 : schémas IPC promus vers @shared.
import { ollamaHostSchema as hostSchema, modelNameSchema } from "@shared/schemas/ipc.js";

/**
 * Valide la structure retournée par `ollama:is-available` (SDD §16.3).
 * Permet de faire remonter la cause réelle d'un échec à l'UI (ex: ECONNREFUSED,
 * AbortError, HTTP 500…) pour faciliter le diagnostic côté utilisateur.
 *
 * Note : c'est un validateur de SORTIE (résultat du manager), pas un payload
 * IPC entrant — reste local au handler.
 */
const availabilitySchema = z.object({
  available: z.boolean(),
  host: z.string(),
  error: z.string().optional(),
  errorKind: z
    .enum(["network", "timeout", "http", "parse", "unknown"])
    .optional(),
});

const settings = new SettingsManager();
const ollamaManager = new OllamaManager(settings);

export function registerOllamaHandlers(): void {
  logger.debug("[IPC] Ollama handlers registered");

  ipcMain.handle("ollama:is-available", async (_event, host?: unknown) => {
    logger.debug(`[IPC] ollama:is-available called, host=${host}`);
    hostSchema.parse(host);
    const result = await ollamaManager.isAvailable();
    return availabilitySchema.parse(result);
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
