import { ipcMain } from "electron";
import path from "node:path";
import fs from "node:fs";
import { z } from "zod";
import { ExportEngine } from "../../services/ExportEngine.js";
import { exportRunSchema, exportBatchSchema } from "@shared/schemas/export.js";
import type {
  ExportRunResult,
  ExportBatchResult,
} from "@shared/schemas/export.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { createProjectDatabase } from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";
import { ChapterRepository } from "../../db/repositories/ChapterRepository.js";
import { ParagraphRepository } from "../../db/repositories/ParagraphRepository.js";

const exportEngine = new ExportEngine();
const settings = new SettingsManager();

/**
 * Résout le chemin du dossier projet à partir de `projectId`
 * pour configurer le traçage des exports (SDD §6.2).
 */
function resolveProjectPath(projectId: string): string {
  const recent = (settings.get("recentProjects") as string[] | undefined) ?? [];
  const projectPath = recent.find((p) => {
    if (!fs.existsSync(path.join(p, "project.db"))) {return false;}
    const db = createProjectDatabase(p);
    const found = new ProjectRepository(db).getById(projectId);
    db.close();
    return found !== undefined;
  });
  if (!projectPath) {
    throw new Error(`Projet non trouvé : ${projectId}`);
  }
  return projectPath;
}

export function registerExportHandlers(): void {
  ipcMain.handle(
    "export:run",
    async (_event, payload): Promise<ExportRunResult> => {
      try {
        const input = exportRunSchema.parse(payload);

        // SDD §6.2 : configurer le traçage des exports
        try {
          const projectPath = resolveProjectPath(input.projectId);
          const db = createProjectDatabase(projectPath);
          exportEngine.setDatabase(db);
        } catch {
          // Si la DB projet est introuvable, on poursuit quand même l'export
          // mais sans traçage dans la table `exports`
        }

        // SDD §21.3 — Protection contre le path traversal sur le dossier de sortie
        if (input.outputPath) {
          const resolvedOutput = path.resolve(input.outputPath);
          // Empêche les chemins contenant ".." de sortir du répertoire courant
          if (resolvedOutput.includes("..")) {
            return {
              success: false,
              error: {
                code: "VALIDATION_ERROR",
                message:
                  "Chemin de sortie invalide : tentatives de path traversal détectées.",
              },
            };
          }
        }
        const outputPath = await exportEngine.export(input);

        // Validation post-export : le fichier doit exister, ne pas être vide, taille > 0
        const fs = await import("node:fs");
        if (!fs.existsSync(outputPath)) {
          return {
            success: false,
            error: {
              code: "EXPORT_FAILED",
              message: "Le fichier exporté est introuvable après l'écriture.",
            },
          };
        }
        const stat = fs.statSync(outputPath);
        if (stat.size === 0) {
          return {
            success: false,
            error: {
              code: "EXPORT_FAILED",
              message: "Le fichier exporté est vide.",
            },
          };
        }

        return {
          success: true,
          path: outputPath,
          size: stat.size,
          format: input.format,
        };
      } catch (err) {
        if (err instanceof z.ZodError) {
          return {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              message: "Données d'export invalides.",
              details: JSON.stringify(err.errors),
            },
          };
        }
        const message =
          err instanceof Error
            ? err.message
            : "Erreur inconnue lors de l'export.";
        return {
          success: false,
          error: { code: "EXPORT_FAILED", message },
        };
      }
    },
  );

  // SDD §13.6 : Export par lots de plusieurs chapitres
  ipcMain.handle(
    "export:batch",
    async (_event, payload): Promise<ExportBatchResult> => {
      try {
        const input = exportBatchSchema.parse(payload);

        // SDD §21.3 — Protection contre le path traversal sur le dossier de sortie
        const resolvedDir = path.resolve(input.outputDir);
        if (resolvedDir.includes("..")) {
          return {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              message:
                "Chemin de sortie invalide : tentatives de path traversal détectées.",
            },
          };
        }

        // Configurer le traçage des exports (SDD §6.2)
        try {
          const projectPath = resolveProjectPath(input.projectId);
          const db = createProjectDatabase(projectPath);
          exportEngine.setDatabase(db);
        } catch {
          // Si la DB projet est introuvable, on poursuit sans traçage
        }

        // Charger les paragraphes de chaque chapitre depuis la DB projet
        const projectPath = resolveProjectPath(input.projectId);
        const db = createProjectDatabase(projectPath);
        const chapterRepo = new ChapterRepository(db);
        const paragraphRepo = new ParagraphRepository(db);

        const chapters = [];
        for (const chapterId of input.chapterIds) {
          const chapter = chapterRepo.getById(chapterId);
          if (!chapter) {
            db.close();
            return {
              success: false,
              error: {
                code: "EXPORT_FAILED",
                message: `Chapitre introuvable : ${chapterId}`,
              },
            };
          }
          const paragraphs = paragraphRepo.listByChapter(chapterId);
          chapters.push({
            chapterId: chapter.id,
            title: chapter.title ?? `Chapitre ${chapter.orderIndex + 1}`,
            paragraphs,
          });
        }
        db.close();

        const result = await exportEngine.exportBatch(
          input.projectId,
          input.projectTitle,
          input.author,
          chapters,
          input.format,
          input.outputDir,
          input.options,
        );

        return {
          success: true,
          paths: result.paths,
          format: result.format,
        };
      } catch (err) {
        if (err instanceof z.ZodError) {
          return {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              message: "Données d'export par lots invalides.",
              details: JSON.stringify(err.errors),
            },
          };
        }
        const message =
          err instanceof Error
            ? err.message
            : "Erreur inconnue lors de l'export par lots.";
        return {
          success: false,
          error: { code: "EXPORT_FAILED", message },
        };
      }
    },
  );
}
