import { ipcMain } from "electron";
import path from "node:path";
import fs from "node:fs";
import { tmxImportSchema, tmxExportSchema } from "@shared/schemas/tmx.js";
import { TranslationMemoryEngine } from "../../services/TranslationMemoryEngine.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { createProjectDatabase } from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";

const settings = new SettingsManager();

export function registerTmHandlers(): void {
  ipcMain.handle(
    "tm:import",
    async (_event, payload: unknown) => {
      const parsed = tmxImportSchema.parse(payload);
      const projectPath = resolveProjectPath(parsed.projectId);
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
      const projectPath = resolveProjectPath(parsed.projectId);
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

function resolveProjectPath(projectId: string): string {
  const recent = (settings.get("recentProjects") as string[] | undefined) ?? [];
  const projectPath = recent.find((p) => {
    const dbPath = path.join(p, "project.db");
    if (!fs.existsSync(dbPath)) return false;
    const db = createProjectDatabase(p);
    const found = new ProjectRepository(db).getById(projectId);
    db.close();
    return found !== undefined;
  });
  if (!projectPath) throw new Error(`Projet non trouve : ${projectId}`);
  return projectPath;
}
