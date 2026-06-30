import { ipcMain } from "electron";
import type { Database as SqliteDatabase } from "node-sqlite3-wasm";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { createProjectDatabase, runMigrations } from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";
import { HistoryRepository } from "../../db/repositories/HistoryRepository.js";
import { ChapterRepository } from "../../db/repositories/ChapterRepository.js";
import { ParagraphRepository } from "../../db/repositories/ParagraphRepository.js";
import {
  historyListSchema,
  historyRollbackSchema,
  historyCreateSchema,
  historyDiffSchema,
} from "@shared/schemas/history.js";
import type {
  HistorySnapshot,
  DiffResult,
  ParagraphChange,
  Paragraph,
} from "@shared/types/index.js";
import path from "node:path";
import fs from "node:fs";

const settings = new SettingsManager();
const migrationsDir = path.join(__dirname, "../../db/migrations");

/**
 * Résout le chemin du dossier projet à partir de `projectId`.
 */
function resolveProjectPath(projectId: string): string {
  const recent = (settings.get("recentProjects") as string[] | undefined) ?? [];
  const projectPath = recent.find((p) => {
    if (!fs.existsSync(path.join(p, "project.db"))) return false;
    const db = createProjectDatabase(p);
    const found = new ProjectRepository(db).getById(projectId);
    db.close();
    return found !== undefined;
  });
  if (!projectPath) throw new Error(`Projet non trouvé : ${projectId}`);
  return projectPath;
}

/**
 * Calcule le diff entre deux listes de paragraphes.
 * Comparaison basée sur l'index et le contenu.
 */
function computeDiff(
  beforeParagraphs: Paragraph[],
  afterParagraphs: Paragraph[],
): DiffResult {
  const changes: ParagraphChange[] = [];
  const maxIndex = Math.max(beforeParagraphs.length, afterParagraphs.length);

  for (let i = 0; i < maxIndex; i++) {
    const before = beforeParagraphs[i];
    const after = afterParagraphs[i];

    if (!before && after) {
      changes.push({
        index: after.indexInChapter,
        type: "added",
        sourceAfter: after.sourceText,
        targetAfter: after.translatedText,
      });
    } else if (before && !after) {
      changes.push({
        index: before.indexInChapter,
        type: "removed",
        sourceBefore: before.sourceText,
        targetBefore: before.translatedText,
      });
    } else if (before && after) {
      const sourceChanged = before.sourceText !== after.sourceText;
      const targetChanged = before.translatedText !== after.translatedText;
      if (sourceChanged || targetChanged) {
        changes.push({
          index: after.indexInChapter,
          type: "modified",
          sourceBefore: sourceChanged ? before.sourceText : undefined,
          sourceAfter: sourceChanged ? after.sourceText : undefined,
          targetBefore: targetChanged ? before.translatedText : undefined,
          targetAfter: targetChanged ? after.translatedText : undefined,
        });
      }
    }
  }

  return { changes };
}

export function registerHistoryHandlers(): void {
  // ─── history:list ───
  ipcMain.handle("history:list", async (_event, payload) => {
    const { projectId, chapterId } = historyListSchema.parse(payload);
    const projectPath = resolveProjectPath(projectId);
    let db: SqliteDatabase | null = null;

    try {
      db = createProjectDatabase(projectPath);
      runMigrations(db, migrationsDir);
      const repo = new HistoryRepository(db);

      if (chapterId) {
        return repo.listByChapter(chapterId);
      }
      return repo.listByProject(projectId);
    } finally {
      if (db) db.close();
    }
  });

  // ─── history:diff ───
  ipcMain.handle("history:diff", async (_event, payload) => {
    const { projectId, snapshotIdA, snapshotIdB } =
      historyDiffSchema.parse(payload);
    const projectPath = resolveProjectPath(projectId);
    let db: SqliteDatabase | null = null;

    try {
      db = createProjectDatabase(projectPath);
      runMigrations(db, migrationsDir);
      const repo = new HistoryRepository(db);

      const snapshotA = repo.getById(snapshotIdA);
      const snapshotB = repo.getById(snapshotIdB);

      if (!snapshotA || !snapshotB) {
        throw new Error(
          `Snapshot introuvable : ${!snapshotA ? snapshotIdA : snapshotIdB}`,
        );
      }

      return computeDiff(snapshotA.paragraphs, snapshotB.paragraphs);
    } finally {
      if (db) db.close();
    }
  });

  // ─── history:rollback ───
  ipcMain.handle("history:rollback", async (_event, payload) => {
    const { projectId, chapterId, snapshotId } =
      historyRollbackSchema.parse(payload);
    const projectPath = resolveProjectPath(projectId);
    let db: SqliteDatabase | null = null;

    try {
      db = createProjectDatabase(projectPath);
      runMigrations(db, migrationsDir);

      const historyRepo = new HistoryRepository(db);
      const paragraphRepo = new ParagraphRepository(db);
      const chapterRepo = new ChapterRepository(db);

      const snapshot = historyRepo.getById(snapshotId);
      if (!snapshot) {
        throw new Error(`Snapshot introuvable : ${snapshotId}`);
      }

      // Restaurer les paragraphes
      paragraphRepo.updateMany(snapshot.paragraphs);

      // Mettre à jour le statut du chapitre
      const allTranslated = snapshot.paragraphs.every(
        (p) => p.status === "translated" || p.status === "reviewed",
      );
      const newStatus = allTranslated
        ? ("completed" as const)
        : ("processing" as const);
      chapterRepo.updateStatus(chapterId, newStatus);

      // Créer un nouveau snapshot de rollback
      const rollbackSnapshotId = crypto.randomUUID();
      historyRepo.create({
        id: rollbackSnapshotId,
        projectId,
        chapterId,
        stage: "rollback",
        paragraphs: snapshot.paragraphs,
        triggeredBy: "rollback",
      });

      return { success: true, snapshotId: rollbackSnapshotId };
    } finally {
      if (db) db.close();
    }
  });

  // ─── history:create-snapshot ───
  ipcMain.handle(
    "history:create-snapshot",
    async (_event, payload): Promise<HistorySnapshot> => {
      const input = historyCreateSchema.parse(payload);
      const projectPath = resolveProjectPath(input.projectId);
      let db: SqliteDatabase | null = null;

      try {
        db = createProjectDatabase(projectPath);
        runMigrations(db, migrationsDir);

        const repo = new HistoryRepository(db);
        const snapshotId = crypto.randomUUID();

        repo.create({
          id: snapshotId,
          projectId: input.projectId,
          chapterId: input.chapterId,
          jobId: input.jobId,
          stepId: input.stepId,
          stage: input.stage,
          paragraphs: input.paragraphs as Paragraph[],
          triggeredBy: input.triggeredBy,
        });

        const created = repo.getById(snapshotId);
        if (!created) throw new Error("Échec de création du snapshot.");
        return created;
      } finally {
        if (db) db.close();
      }
    },
  );
}
