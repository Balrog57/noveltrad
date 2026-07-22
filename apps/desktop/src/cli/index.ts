#!/usr/bin/env node
/**
 * CLI Noveltrad — pilotable par un agent IA.
 *
 * Usage général :
 *   noveltrad <command> [options]
 *
 * Commandes (détails dans docs/cli.md) :
 *   create     Crée un projet (DE→FR par défaut)
 *   list       Liste les projets récents
 *   import     Importe un fichier (epub/docx/txt/md) dans un projet
 *   chapters   Liste les chapitres d'un projet
 *   translate  Lance le workflow de traduction (nécessite Ollama)
 *   export     Exporte un chapitre traduit (md/txt/docx/epub)
 *   status     Consulte l'état d'un job de traduction
 *   doctor     Diagnostique la configuration (Ollama, settings, modèles)
 *
 * Toutes les commandes acceptent --json pour un output structuré.
 * Le progrès du workflow (translate) est émis sur stderr en NDJSON.
 *
 * Exit codes sémantiques : 0 OK / 1 user / 2 Ollama / 3 DB / 4 traduction / 5 inconnu.
 */

import { Command } from "commander";
import { getSettingsManager } from "../main/managers/SettingsManager.js";
import { ProjectManager } from "../main/managers/ProjectManager.js";
import { ProjectPathResolver } from "../main/managers/ProjectPathResolver.js";
import { createProjectDatabase } from "../main/db/connection.js";
import { ChapterRepository } from "../main/db/repositories/ChapterRepository.js";
import { ParagraphRepository } from "../main/db/repositories/ParagraphRepository.js";
import {
  printResult,
  ok,
  err,
  errorCodeToExit,
  EXIT_CODES,
  type Result,
} from "./output.js";

const program = new Command();

program
  .name("noveltrad")
  .description("Traduction littéraire assistée par IA (CLI pilotable par agent)")
  .version("3.0.1");

// ── Option globale --json ────────────────────────────────────────────────
let jsonMode = false;
program.option("--json", "Sortie JSON structurée (pour consommation agent IA)", false);

program.hook("preAction", (cmd) => {
  jsonMode = cmd.opts().json ?? false;
});

// ════════════════════════════════════════════════════════════════════════
// create — créer un projet
// ════════════════════════════════════════════════════════════════════════
program
  .command("create")
  .description("Crée un nouveau projet de traduction")
  .requiredOption("-n, --name <name>", "Nom du projet")
  .option("-s, --src <lang>", "Langue source (code ISO 2 lettres)", "de")
  .option("-t, --tgt <lang>", "Langue cible (code ISO 2 lettres)", "fr")
  .option("-p, --parent <path>", "Dossier parent (défaut: ~/NovelTrad Projects)")
  .action(async (opts: { name: string; src: string; tgt: string; parent?: string }) => {
    await runCommand(async () => {
      const settings = getSettingsManager();
      const pm = new ProjectManager(settings);
      const parentPath = opts.parent ?? (settings.get("defaultProjectsPath") as string);
      const project = await pm.create({
        name: opts.name,
        sourceLanguage: opts.src,
        targetLanguage: opts.tgt,
        parentPath,
      });
      return ok({
        id: project.id,
        name: project.name,
        path: project.path,
        sourceLanguage: project.sourceLanguage,
        targetLanguage: project.targetLanguage,
      });
    });
  });

// ════════════════════════════════════════════════════════════════════════
// list — projets récents
// ════════════════════════════════════════════════════════════════════════
program
  .command("list")
  .description("Liste les projets récents")
  .action(async () => {
    await runCommand(async () => {
      const settings = getSettingsManager();
      const pm = new ProjectManager(settings);
      const projects = await pm.listRecent();
      return ok(
        projects.map((p) => ({
          id: p.id,
          name: p.name,
          sourceLanguage: p.sourceLanguage,
          targetLanguage: p.targetLanguage,
          path: p.path,
        })),
      );
    });
  });

// ════════════════════════════════════════════════════════════════════════
// import — importer un fichier
// ════════════════════════════════════════════════════════════════════════
program
  .command("import <projectId> <file>")
  .description("Importe un fichier (epub/docx/txt/md) dans un projet")
  .action(async (projectId: string, file: string) => {
    await runCommand(async () => {
      const fs = await import("node:fs");
      if (!fs.existsSync(file)) {
        return err("FILE_NOT_FOUND", `Fichier introuvable : ${file}`);
      }
      const settings = getSettingsManager();
      const pm = new ProjectManager(settings);
      const chapters = await pm.importSource(projectId, file);
      return ok({
        projectId,
        importedChapters: chapters.length,
        chapters: chapters.map((c) => ({
          id: c.id,
          title: c.title,
          orderIndex: c.orderIndex,
          status: c.status,
        })),
      });
    });
  });

// ════════════════════════════════════════════════════════════════════════
// chapters — lister les chapitres d'un projet
// ════════════════════════════════════════════════════════════════════════
program
  .command("chapters <projectId>")
  .description("Liste les chapitres d'un projet")
  .option("--with-paragraphs", "Inclut le nombre de paragraphes et caractères par chapitre")
  .action(async (projectId: string, opts: { withParagraphs?: boolean }) => {
    await runCommand(async () => {
      const settings = getSettingsManager();
      const resolver = new ProjectPathResolver(settings);
      const projectPath = resolver.resolve(projectId);
      const db = createProjectDatabase(projectPath);
      try {
        const chapterRepo = new ChapterRepository(db);
        const paragraphRepo = new ParagraphRepository(db);
        const chapters = chapterRepo.listByProject(projectId);
        const result = [];
        for (const c of chapters) {
          const entry: Record<string, unknown> = {
            id: c.id,
            title: c.title,
            orderIndex: c.orderIndex,
            status: c.status,
          };
          if (opts.withParagraphs) {
            const paras = paragraphRepo.listByChapter(c.id);
            entry.paragraphs = paras.length;
            entry.characters = paras.reduce((s, p) => s + p.sourceText.length, 0);
            entry.translatedParagraphs = paras.filter((p) => p.status === "translated").length;
          }
          result.push(entry);
        }
        return ok({ projectId, chapterCount: chapters.length, chapters: result });
      } finally {
        db.close();
      }
    });
  });

// ════════════════════════════════════════════════════════════════════════
// status — consulter l'état des chapitres d'un projet
// ════════════════════════════════════════════════════════════════════════
program
  .command("status <projectId>")
  .description("Consulte l'état de traduction des chapitres d'un projet")
  .action(async (projectId: string) => {
    await runCommand(async () => {
      const settings = getSettingsManager();
      const resolver = new ProjectPathResolver(settings);
      const projectPath = resolver.resolve(projectId);
      const db = createProjectDatabase(projectPath);
      try {
        // v3 : plus de jobs table. On rapporte le statut des chapitres
        // (pending/processing/completed/error) — reflet direct de l'avancement.
        const chapterRepo = new ChapterRepository(db);
        const chapters = chapterRepo.listByProject(projectId);
        const summary = {
          total: chapters.length,
          completed: chapters.filter((c) => c.status === "completed").length,
          pending: chapters.filter((c) => c.status === "pending").length,
          processing: chapters.filter((c) => c.status === "processing").length,
          error: chapters.filter((c) => c.status === "error").length,
        };
        return ok({
          projectId,
          summary,
          chapters: chapters.map((c) => ({
            id: c.id,
            title: c.title,
            orderIndex: c.orderIndex,
            status: c.status,
          })),
        });
      } finally {
        db.close();
      }
    });
  });

// ════════════════════════════════════════════════════════════════════════
// doctor — diagnostiquer la configuration
// ════════════════════════════════════════════════════════════════════════
program
  .command("doctor")
  .description("Diagnostique la configuration (Ollama, settings, modèles)")
  .action(async () => {
    await runCommand(async () => {
      const settings = getSettingsManager();
      const all = settings.getAll();

      // Check Ollama availability
      let ollama: { available: boolean; host: string; models?: string[]; error?: string };
      try {
        const { OllamaManager } = await import("../main/managers/OllamaManager.js");
        const mgr = new OllamaManager(settings);
        const result = await mgr.isAvailable();
        let models: string[] | undefined;
        if (result.available) {
          try {
            const modelInfos = await mgr.listModels();
            models = modelInfos.map((m: { name: string }) => m.name);
          } catch {
            models = undefined;
          }
        }
        ollama = {
          available: result.available,
          host: all.ollamaHost,
          models,
          error: result.error,
        };
      } catch (e) {
        ollama = {
          available: false,
          host: all.ollamaHost,
          error: e instanceof Error ? e.message : String(e),
        };
      }

      return ok({
        version: "2.3.0",
        ollama,
        settings: {
          defaultModel: all.defaultModel,
          defaultPreTranslateModel: all.defaultPreTranslateModel,
          sourceLanguage: all.sourceLanguage,
          targetLanguage: all.targetLanguage,
          qualityThreshold: all.qualityThreshold,
          maxConcurrentJobs: all.maxConcurrentJobs,
          ragEnabled: all.ragEnabled,
          reviewLoopEnabled: all.reviewLoopEnabled,
          useWorkerThreads: all.useWorkerThreads,
        },
        recentProjects: (all.recentProjects as string[]).length,
        recommendations: generateDoctorRecommendations(ollama, all),
      });
    });
  });

// ── translate / export : commandes plus complexes, dans un module séparé ──
// Pour limiter la taille de ce fichier. Importées paresseusement (l'import
// direct déclencherait le chargement de WorkflowEngine qui peut être lourd).
program
  .command("translate <projectId>")
  .description("Lance le workflow de traduction (nécessite Ollama)")
  .option("-c, --chapter <id>", "Traduit un seul chapitre (sinon: batch)")
  .option("--no-wait", "Renvoie le jobId immédiatement sans attendre la fin")
  .action(async (projectId: string, opts: { chapter?: string; wait?: boolean }) => {
    await runCommand(async () => {
      const { runTranslate } = await import("./translate.js");
      return runTranslate(projectId, { chapterId: opts.chapter, wait: opts.wait ?? true }, jsonMode);
    });
  });

program
  .command("export <projectId>")
  .description("Exporte un chapitre traduit (md/txt/docx/epub)")
  .requiredOption("-f, --format <format>", "Format: md, txt, docx, epub")
  .option("-c, --chapter <id>", "Un seul chapitre (sinon: batch complet)")
  .option("-o, --out <path>", "Dossier de sortie (défaut: <project>/exports)")
  .action(async (projectId: string, opts: { format: string; chapter?: string; out?: string }) => {
    await runCommand(async () => {
      const { runExport } = await import("./export-cmd.js");
      return runExport(projectId, opts);
    });
  });

// ════════════════════════════════════════════════════════════════════════
// Helpers
// ════════════════════════════════════════════════════════════════════════

async function runCommand(fn: () => Promise<Result<unknown>>): Promise<void> {
  try {
    const result = await fn();
    printResult(result, jsonMode);
    if (!result.ok) {
      process.exitCode = errorCodeToExit(result.error.code);
    }
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    const result = err("UNKNOWN", message);
    printResult(result, jsonMode);
    process.exitCode = EXIT_CODES.UNKNOWN;
  }
}

function generateDoctorRecommendations(
  ollama: { available: boolean; models?: string[]; error?: string },
  settings: { defaultModel: string; defaultPreTranslateModel: string },
): string[] {
  const recs: string[] = [];
  if (!ollama.available) {
    recs.push("Ollama n'est pas accessible — démarrez 'ollama serve' ou vérifiez le host.");
    return recs;
  }
  if (ollama.models && !ollama.models.includes(settings.defaultModel)) {
    recs.push(
      `Le modèle par défaut '${settings.defaultModel}' n'est pas installé. Installez-le: 'ollama pull ${settings.defaultModel}'.`,
    );
  }
  if (ollama.models && !ollama.models.includes(settings.defaultPreTranslateModel)) {
    recs.push(
      `Le modèle de pré-traduction '${settings.defaultPreTranslateModel}' n'est pas installé. Installez-le: 'ollama pull ${settings.defaultPreTranslateModel}'.`,
    );
  }
  if (recs.length === 0) {
    recs.push("Configuration OK — prêt à traduire.");
  }
  return recs;
}

// Par défaut (sans sous-commande), afficher l'aide.
if (process.argv.length <= 2) {
  program.outputHelp();
} else {
  program.parseAsync(process.argv).catch((e) => {
    process.stderr.write(`Erreur fatale: ${e instanceof Error ? e.message : String(e)}\n`);
    process.exit(EXIT_CODES.UNKNOWN);
  });
}
