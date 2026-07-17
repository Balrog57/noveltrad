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
import type { ProjectDatabase } from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";
import { ChapterRepository } from "../../db/repositories/ChapterRepository.js";
import { ParagraphRepository } from "../../db/repositories/ParagraphRepository.js";
import { assertSafeProjectPath } from "../../utils/paths.js";

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
    // Bug fix : try/finally pour garantir la fermeture de la DB même si
    // getById lance une exception (DB corrompue / WAL verrouillé).
    const db = createProjectDatabase(p);
    try {
      const found = new ProjectRepository(db).getById(projectId);
      return found !== undefined;
    } finally {
      db.close();
    }
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
      let traceDb: ProjectDatabase | null = null;
      try {
        const input = exportRunSchema.parse(payload);

        // SDD §6.2 : configurer le traçage des exports. On ouvre une DB dédiée
        // au traçage et on s'assure de la fermer dans tous les cas (le fix
        // précédent laissait fuir la connexion sur chaque export).
        try {
          const projectPath = resolveProjectPath(input.projectId);
          traceDb = createProjectDatabase(projectPath);
          exportEngine.setDatabase(traceDb);
        } catch {
          // Si la DB projet est introuvable, on poursuit quand même l'export
          // mais sans traçage dans la table `exports`
          exportEngine.setDatabase(null as never);
        }

        // P0-5 fix : l'ancien check `resolvedOutput.includes("..")` était
        // inopérant — path.resolve() collapse déjà les "..", donc la chaîne
        // n'en contenait plus. Remplacé par assertSafeProjectPath qui rejette
        // les zones système critiques (C:\Windows, /etc, etc.).
        if (input.outputPath) {
          try {
            assertSafeProjectPath(input.outputPath);
          } catch (e) {
            return {
              success: false,
              error: {
                code: "VALIDATION_ERROR",
                message:
                  "Chemin de sortie invalide : " +
                  (e instanceof Error ? e.message : "path traversal détecté"),
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
      } finally {
        // Bug fix : fermer la DB de traçage pour éviter la fuite de connexion
        // à chaque export (WAL/handles).
        if (traceDb) {traceDb.close();}
        exportEngine.setDatabase(null as never);
      }
    },
  );

  // SDD §13.6 : Export par lots de plusieurs chapitres
  ipcMain.handle(
    "export:batch",
    async (_event, payload): Promise<ExportBatchResult> => {
      let db: ProjectDatabase | null = null;
      try {
        const input = exportBatchSchema.parse(payload);

        // P0-5 fix (consolidation PRs sentinel) : l'ancien check
        // `resolvedDir.includes("..")` était inopérant (path.resolve collapse
        // déjà les ".."). Remplacé par assertSafeProjectPath qui rejette les
        // zones système + le bypass URL-encoded (%2e%2e). Cohérent avec le
        // handler export:run (cf. plus haut dans ce fichier).
        try {
          assertSafeProjectPath(input.outputDir);
        } catch (e) {
          return {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              message:
                "Chemin de sortie invalide : " +
                (e instanceof Error ? e.message : "path traversal détecté"),
            },
          };
        }

        // Bug fix : une seule connexion DB partagée entre le traçage (via
        // setDatabase) et la lecture des chapitres/paragraphes. L'ancien code
        // ouvrait 2 connexions dont une fuyait à chaque appel.
        const projectPath = resolveProjectPath(input.projectId);
        db = createProjectDatabase(projectPath);
        exportEngine.setDatabase(db);
        const chapterRepo = new ChapterRepository(db);
        const paragraphRepo = new ParagraphRepository(db);

        // T9 fix : lire la targetLanguage du projet pour l'export EPUB multi-chapitre
        // (sinon epub-gen-memory déclare lang="fr" en dur, SDD §13.3).
        const projectRepo = new ProjectRepository(db);
        const project = projectRepo.getById(input.projectId);
        const targetLanguage = project?.targetLanguage;

        const chapters = [];
        for (const chapterId of input.chapterIds) {
          const chapter = chapterRepo.getById(chapterId);
          if (!chapter) {
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

        // Propager la targetLanguage dans les options pour toEpubMultiChapter
        const optionsWithLang = {
          ...input.options,
          ...(targetLanguage ? { targetLanguage } : {}),
        };

        const result = await exportEngine.exportBatch(
          input.projectId,
          input.projectTitle,
          input.author,
          chapters,
          input.format,
          input.outputDir,
          optionsWithLang,
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
      } finally {
        // Bug fix : fermer l'unique DB et libérer le singleton pour éviter la
        // fuite de connexion et la race sur this.db.
        if (db) {db.close();}
        exportEngine.setDatabase(null as never);
      }
    },
  );
}
