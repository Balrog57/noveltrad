import { ipcMain, dialog } from "electron";
import path from "node:path";
import fs from "node:fs";
import { z } from "zod";
import { ProjectManager } from "../../managers/ProjectManager.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { createProjectDatabase } from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";

const settings = new SettingsManager();
const projectManager = new ProjectManager(settings);

const createProjectSchema = z.object({
  name: z.string().min(1).max(100),
  author: z.string().max(100).optional(),
  sourceLanguage: z.string().length(2),
  targetLanguage: z.string().length(2),
  parentPath: z.string().min(1),
});

const importFilesSchema = z.object({
  projectId: z.string().uuid(),
  filePaths: z.array(z.string().min(1)).min(1).max(50),
});

export function registerProjectHandlers(): void {
  ipcMain.handle("project:create", async (_event, payload) => {
    const parsed = createProjectSchema.parse(payload);
    return projectManager.create(parsed);
  });

  ipcMain.handle("project:open", async (_event, projectPath: string) => {
    return projectManager.open(projectPath);
  });

  ipcMain.handle("project:path", async (_event, projectId: string) => {
    const recent =
      (settings.get("recentProjects") as string[] | undefined) ?? [];
    const projectPath = recent.find((p) => {
      const db = createProjectDatabase(p);
      const found = new ProjectRepository(db).getById(projectId);
      db.close();
      return found !== undefined;
    });
    if (!projectPath) throw new Error(`Projet non trouve : ${projectId}`);
    return projectPath;
  });

  ipcMain.handle("project:list-recent", async () => {
    return projectManager.listRecent();
  });

  ipcMain.handle(
    "project:delete",
    async (_event, projectId: string, removeFiles: boolean) => {
      return projectManager.delete(projectId, removeFiles);
    },
  );

  ipcMain.handle("chapter:list", async (_event, projectId: string) => {
    return projectManager.listChapters(projectId);
  });

  ipcMain.handle(
    "chapter:import",
    async (_event, projectId: string, filePath: string) => {
      return projectManager.importSource(projectId, filePath);
    },
  );

  /**
   * Import multiple fichiers (drag-and-drop ou sélection multiple).
   * SDD §5.4, §5.9 — Import DOCX/EPUB/TXT/MD avec drag-and-drop.
   */
  ipcMain.handle(
    "source:import-files",
    async (_event, payload: { projectId: string; filePaths: string[] }) => {
      const parsed = importFilesSchema.parse(payload);
      const results: Array<{
        filePath: string;
        success: boolean;
        chapters?: Awaited<ReturnType<ProjectManager["importSource"]>>;
        error?: string;
      }> = [];

      for (const filePath of parsed.filePaths) {
        try {
          const chapters = await projectManager.importSource(
            parsed.projectId,
            filePath,
          );
          results.push({ filePath, success: true, chapters });
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Erreur inconnue lors de l'import";
          results.push({ filePath, success: false, error: message });
        }
      }

      return results;
    },
  );

  /**
   * Retourne les statistiques d'un projet : nombre de chapitres,
   * paragraphes traduits/total, mots source/cible, score qualité moyen,
   * dernier statut workflow.
   * SDD §4.6 — Tableau de bord projet.
   */
  ipcMain.handle(
    "project:stats",
    async (_event, projectId: string): Promise<ProjectStats> => {
      const recent =
        (settings.get("recentProjects") as string[] | undefined) ?? [];
      const projectPath = recent.find((p) => {
        const dbPath = path.join(p, "project.db");
        if (!fs.existsSync(dbPath)) return false;
        const db = createProjectDatabase(p);
        const found = new ProjectRepository(db).getById(projectId);
        db.close();
        return found !== undefined;
      });

      if (!projectPath) {
        throw new Error(`Projet non trouve : ${projectId}`);
      }

      const db = createProjectDatabase(projectPath);

      try {
        // Nombre de chapitres
        const chapterRow = db
          .prepare(
            "SELECT COUNT(*) as count FROM chapters WHERE project_id = ?",
          )
          .get([projectId]) as { count: number };

        // Paragraphes : total et traduits
        const paragraphRow = db
          .prepare(
            `SELECT
               COUNT(*) as total,
               SUM(CASE WHEN translated_text IS NOT NULL AND translated_text != '' THEN 1 ELSE 0 END) as translated
             FROM paragraphs p
             JOIN chapters c ON p.chapter_id = c.id
             WHERE c.project_id = ?`,
          )
          .get([projectId]) as { total: number; translated: number };

        // Nombre de mots source et cible
        const wordRow = db
          .prepare(
            `SELECT
               COALESCE(SUM(LENGTH(source_text) - LENGTH(REPLACE(source_text, ' ', '')) + 1), 0) as source_words,
               COALESCE(SUM(CASE WHEN translated_text IS NOT NULL AND translated_text != ''
                    THEN LENGTH(translated_text) - LENGTH(REPLACE(translated_text, ' ', '')) + 1
                    ELSE 0 END), 0) as target_words
             FROM paragraphs p
             JOIN chapters c ON p.chapter_id = c.id
             WHERE c.project_id = ?`,
          )
          .get([projectId]) as { source_words: number; target_words: number };

        // Score qualité moyen (depuis job_steps.score)
        const qualityRow = db
          .prepare(
            `SELECT AVG(js.score) as avg_score
             FROM job_steps js
             JOIN jobs j ON js.job_id = j.id
             WHERE j.project_id = ? AND js.score IS NOT NULL`,
          )
          .get([projectId]) as { avg_score: number | null };

        // Dernier statut workflow
        const lastJobRow = db
          .prepare(
            `SELECT status FROM jobs
             WHERE project_id = ?
             ORDER BY created_at DESC LIMIT 1`,
          )
          .get([projectId]) as { status: string } | undefined;

        return {
          chapterCount: chapterRow.count,
          totalParagraphs: paragraphRow.total,
          translatedParagraphs: paragraphRow.translated,
          sourceWordCount: wordRow.source_words,
          targetWordCount: wordRow.target_words,
          averageQualityScore:
            qualityRow.avg_score !== null
              ? Math.round(qualityRow.avg_score * 100) / 100
              : null,
          lastWorkflowStatus: lastJobRow?.status ?? null,
        };
      } finally {
        db.close();
      }
    },
  );

  ipcMain.handle("dialog:open-file", async (_event, options) => {
    const result = await dialog.showOpenDialog(options);
    return { canceled: result.canceled, filePaths: result.filePaths };
  });
}

/** Statistiques d'un projet (SDD §4.6) */
interface ProjectStats {
  chapterCount: number;
  totalParagraphs: number;
  translatedParagraphs: number;
  sourceWordCount: number;
  targetWordCount: number;
  averageQualityScore: number | null;
  lastWorkflowStatus: string | null;
}
