import { ipcMain } from "electron";
import { OllamaManager } from "../../managers/OllamaManager.js";
import { SettingsManager } from "../../managers/SettingsManager.js";

const settings = new SettingsManager();
const ollamaManager = new OllamaManager(settings);

export function registerOllamaHandlers(): void {
  ipcMain.handle("ollama:is-available", async () => {
    return ollamaManager.isAvailable();
  });

  ipcMain.handle("ollama:list-models", async () => {
    return ollamaManager.listModels();
  });

  ipcMain.handle("ollama:pull-model", async (event, name: string) => {
    await ollamaManager.pullModel(name, (progress) => {
      event.sender.send("ollama:pull-progress", progress);
    });
    return { done: true };
  });
}
