import { ipcMain } from "electron";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { createProjectDatabase, runMigrations } from "../../db/connection.js";
import { ParagraphRepository } from "../../db/repositories/ParagraphRepository.js";
import { ChapterRepository } from "../../db/repositories/ChapterRepository.js";
import {
  getParagraphsSchema,
  saveChapterSchema,
} from "@shared/schemas/paragraph.js";
import type { Database as SqliteDatabase } from "node-sqlite3-wasm";
import path from "node:path";
import fs from "node:fs";

const settings = new SettingsManager();

export function registerParagraphHandlers(): void {
  // Récupérer les paragraphes d'un chapitre
  ipcMain.handle("chapter:get-paragraphs", async (_event, payload) => {
    const { chapterId } = getParagraphsSchema.parse(payload);

    // Récupérer le chapitre pour trouver son projet
    const recent =
      (settings.get("recentProjects") as string[] | undefined) ?? [];
    let paragraphRepo: ParagraphRepository | null = null;
    let foundDb: SqliteDatabase | null = null;

    for (const projectPath of recent) {
      if (!fs.existsSync(path.join(projectPath, "project.db"))) {continue;}
      const db = createProjectDatabase(projectPath);
      runMigrations(db);
      const chapter = new ChapterRepository(db).getById(chapterId);
      if (chapter) {
        paragraphRepo = new ParagraphRepository(db);
        foundDb = db;
        break;
      }
      db.close();
    }

    if (!paragraphRepo || !foundDb) {
      throw new Error(`Chapitre non trouvé : ${chapterId}`);
    }

    // Fix 3 : Fermer la connexion DB après usage (try/finally évite la fuite)
    try {
      return paragraphRepo.listByChapter(chapterId);
    } finally {
      foundDb.close();
    }
  });

  // Sauvegarder les paragraphes d'un chapitre
  ipcMain.handle("chapter:save", async (_event, payload) => {
    const { chapterId, paragraphs } = saveChapterSchema.parse(payload);

    // Récupérer le chapitre pour trouver son projet
    const recent =
      (settings.get("recentProjects") as string[] | undefined) ?? [];
    let paragraphRepo: ParagraphRepository | null = null;
    let chapterRepo: ChapterRepository | null = null;
    let foundDb: SqliteDatabase | null = null;

    for (const projectPath of recent) {
      if (!fs.existsSync(path.join(projectPath, "project.db"))) {continue;}
      const db = createProjectDatabase(projectPath);
      runMigrations(db);
      chapterRepo = new ChapterRepository(db);
      const chapter = chapterRepo.getById(chapterId);
      if (chapter) {
        paragraphRepo = new ParagraphRepository(db);
        foundDb = db;
        break;
      }
      db.close();
    }

    if (!paragraphRepo || !chapterRepo || !foundDb) {
      throw new Error(`Chapitre non trouvé : ${chapterId}`);
    }

    // Fix 3 : Fermer la connexion DB après usage (try/finally évite la fuite)
    try {
      // Sauvegarder tous les paragraphes
      paragraphRepo.updateMany(paragraphs);

      // Mettre à jour le statut du chapitre
      const allTranslated = paragraphs.every(
        (p) => p.status === "translated" || p.status === "reviewed",
      );
      // Fix 6 : Logique redondante simplifiée — anyReviewed ne servait à rien
      const newStatus = allTranslated ? "completed" : ("processing" as const);
      chapterRepo.updateStatus(chapterId, newStatus);
    } finally {
      foundDb.close();
    }
  });
}
