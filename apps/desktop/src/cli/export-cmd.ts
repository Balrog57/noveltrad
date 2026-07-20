/**
 * Sous-commande `noveltrad export` — exporte un chapitre traduit.
 *
 * Pilote ExportEngine directement (sans IPC). L'export ne nécessite pas
 * Ollama — il lit les paragraphes déjà traduits en DB et génère le fichier
 * au format demandé.
 *
 * Si un chapitre n'a pas été traduit (paragraphes en status 'pending'),
 * l'export échoue avec un message clair (code NOT_TRANSLATED).
 */

import path from "node:path";
import type { ExportInput, ExportFormat, Paragraph } from "@shared/types/index.js";
import { getSettingsManager } from "../main/managers/SettingsManager.js";
import { ProjectPathResolver } from "../main/managers/ProjectPathResolver.js";
import { ExportEngine } from "../main/services/ExportEngine.js";
import { createProjectDatabase } from "../main/db/connection.js";
import { ChapterRepository } from "../main/db/repositories/ChapterRepository.js";
import { ParagraphRepository } from "../main/db/repositories/ParagraphRepository.js";
import { ProjectRepository } from "../main/db/repositories/ProjectRepository.js";
import { ok, err, type Result } from "./output.js";

export interface ExportOptions {
  format: string;
  chapter?: string;
  out?: string;
}

/** Alias courts acceptés par la CLI → nom ExportFormat canonique. */
const FORMAT_ALIASES: Record<string, ExportFormat> = {
  md: "markdown",
  markdown: "markdown",
  txt: "txt",
  text: "txt",
  docx: "docx",
  epub: "epub",
  html: "html",
};

export async function runExport(
  projectId: string,
  opts: ExportOptions,
): Promise<Result<unknown>> {
  const canonical = FORMAT_ALIASES[opts.format.toLowerCase()];
  if (!canonical) {
    return err(
      "INVALID_ARGS",
      `Format invalide: '${opts.format}'. Formats supportés: md, txt, docx, epub, html`,
    );
  }
  const format: ExportFormat = canonical;

  const settings = getSettingsManager();
  const resolver = new ProjectPathResolver(settings);
  const projectPath = resolver.resolve(projectId);
  const outDir = opts.out ?? path.join(projectPath, "exports");

  const db = createProjectDatabase(projectPath);
  try {
    const chapterRepo = new ChapterRepository(db);
    const paragraphRepo = new ParagraphRepository(db);
    const projectRepo = new ProjectRepository(db);
    const project = projectRepo.getById(projectId);
    if (!project) {
      return err("NOT_FOUND", `Projet introuvable en DB : ${projectId}`);
    }

    const allChapters = chapterRepo.listByProject(projectId);
    if (allChapters.length === 0) {
      return err("INVALID_ARGS", "Aucun chapitre à exporter — importez d'abord un fichier.");
    }

    // Filtrer les chapitres à exporter
    const targets = opts.chapter
      ? allChapters.filter((c) => c.id === opts.chapter)
      : allChapters;
    if (opts.chapter && targets.length === 0) {
      return err("NOT_FOUND", `Chapitre introuvable : ${opts.chapter}`);
    }

    // Vérifier qu'au moins un chapitre a du contenu traduit
    for (const c of targets.slice(0, 3)) {
      const paras = paragraphRepo.listByChapter(c.id);
      const translated = paras.filter((p) => p.translatedText);
      if (translated.length === 0) {
        return err(
          "NOT_TRANSLATED",
          `Le chapitre '${c.title}' n'a pas de paragraphes traduits. Lancez 'noveltrad translate ${projectId} -c ${c.id}' d'abord.`,
        );
      }
    }

    // ExportEngine.export prend un ExportInput par chapitre (title + paragraphs).
    // Pour le batch, on boucle sur les chapitres traduits.
    const exportEngine = new ExportEngine();
    exportEngine.setDatabase(db);

    const exportedPaths: string[] = [];
    try {
      for (const chapter of targets) {
        const paragraphs = paragraphRepo.listByChapter(chapter.id);
        // Skip les chapitres vides ou non traduits en mode batch
        if (!paragraphs.some((p) => p.translatedText)) {continue;}

        const input: ExportInput = {
          projectId,
          chapterId: chapter.id,
          title: chapter.title ?? "Chapitre",
          author: project.author,
          paragraphs: paragraphs as Paragraph[],
          format,
          outputPath: outDir,
        };
        const resultPath = await exportEngine.export(input);
        exportedPaths.push(resultPath);
      }

      if (exportedPaths.length === 0) {
        return err("NOT_TRANSLATED", "Aucun chapitre traduit à exporter.");
      }

      return ok({
        projectId,
        format,
        exportedChapters: exportedPaths.length,
        paths: exportedPaths,
      });
    } catch (e) {
      return err("EXPORT_FAILED", e instanceof Error ? e.message : String(e));
    } finally {
      exportEngine.setDatabase(null as never);
    }
  } finally {
    db.close();
  }
}
