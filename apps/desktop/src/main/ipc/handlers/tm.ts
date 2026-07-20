import { ipcMain } from "electron";
import { tmxImportSchema, tmxExportSchema } from "@shared/schemas/tmx.js";
import { TranslationMemoryEngine } from "../../services/TranslationMemoryEngine.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { ProjectPathResolver } from "../../managers/ProjectPathResolver.js";
import { createProjectDatabase } from "../../db/connection.js";

const settings = new SettingsManager();
// WS-4 : résolution centralisée du chemin projet (tue la duplication 8×).
const pathResolver = new ProjectPathResolver(settings);

export function registerTmHandlers(): void {
  ipcMain.handle(
    "tm:import",
    async (_event, payload: unknown) => {
      const parsed = tmxImportSchema.parse(payload);
      const projectPath = pathResolver.resolve(parsed.projectId);
      const db = createProjectDatabase(projectPath);
      try {
        const tmEngine = new TranslationMemoryEngine(db);
        const count = tmEngine.importTmx(parsed.filePath, parsed.projectId);
        return { success: true, importedCount: count };
      } finally {
        db.close();
      }
    },
  );

  ipcMain.handle(
    "tm:export",
    async (_event, payload: unknown) => {
      const parsed = tmxExportSchema.parse(payload);
      const projectPath = pathResolver.resolve(parsed.projectId);
      const db = createProjectDatabase(projectPath);
      try {
        const tmEngine = new TranslationMemoryEngine(db);
        tmEngine.exportTmx(parsed.filePath, parsed.projectId);
        return { success: true };
      } finally {
        db.close();
      }
    },
  );
}
