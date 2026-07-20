import { tmxImportSchema, tmxExportSchema } from "@shared/schemas/tmx.js";
import { TranslationMemoryEngine } from "../../services/TranslationMemoryEngine.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { ProjectPathResolver } from "../../managers/ProjectPathResolver.js";
import { createProjectDatabase } from "../../db/connection.js";
// Axe 4 : adoption safeHandle (validation Zod + try/catch + log standardisés).
import { safeHandle } from "../safeHandle.js";

const settings = new SettingsManager();
// WS-4 : résolution centralisée du chemin projet (tue la duplication 8×).
const pathResolver = new ProjectPathResolver(settings);

export function registerTmHandlers(): void {
  // Axe 4 : safeHandle valide le payload via tmxImportSchema puis englobe le
  // handler body d'un try/catch (log structuré + re-throw lisible). Le
  // try/finally DB reste nécessaire côté handler (safeHandle ne gère pas les
  // ressources).
  safeHandle(
    "tm:import",
    tmxImportSchema,
    async (parsed) => {
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

  safeHandle(
    "tm:export",
    tmxExportSchema,
    async (parsed) => {
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
