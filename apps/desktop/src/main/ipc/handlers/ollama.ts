import { ipcMain } from "electron";
import { z } from "zod";
import { OllamaManager } from "../../managers/OllamaManager.js";
import { SettingsManager } from "../../managers/SettingsManager.js";

// ── Schémas de validation Zod (SDD §16.3) ──────────────────────────────

const hostSchema = z.string().min(1).optional();
const modelNameSchema = z.string().min(1, { message: "model name requis" });

const settings = new SettingsManager();
const ollamaManager = new OllamaManager(settings);

export function registerOllamaHandlers(): void {
  ipcMain.handle("ollama:is-available", async (_event, host?: unknown) => {
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
}
