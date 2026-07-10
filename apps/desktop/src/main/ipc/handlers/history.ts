import { ipcMain } from "electron";
import type { Database as SqliteDatabase } from "node-sqlite3-wasm";
import { SettingsManager } from "../../managers/SettingsManager.js";
import {
  createProjectDatabase,
  runMigrations,
} from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";
import { HistoryRepository } from "../../db/repositories/HistoryRepository.js";
import { ChapterRepository } from "../../db/repositories/ChapterRepository.js";
import { ParagraphRepository } from "../../db/repositories/ParagraphRepository.js";
import { AuditService } from "../../services/AuditService.js";
import {
  historyListSchema,
  historyRollbackSchema,
  historyRollbackPartialSchema,
  historyCreateSchema,
  historyDiffSchema,
  historyGetParagraphsSchema,
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
  const recent =
    (settings.get("recentProjects") as string[] | undefined) ?? [];
  const projectPath = recent.find((p) => {
    if (!fs.existsSync(path.join(p, "project.db"))) {return false;}
    const db = createProjectDatabase(p);
    const found = new ProjectRepository(db).getById(projectId);
    db.close();
    return found !== undefined;
  });
  if (!projectPath) {throw new Error(`Projet non trouvé : ${projectId}`);}
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
      if (db) {db.close();}
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

      const paragraphsA = repo.getFullParagraphs(snapshotIdA);
      const paragraphsB = repo.getFullParagraphs(snapshotIdB);

      // Bug fix : un snapshot existant peut légitimement avoir 0 paragraphes
      // (chapitre vide au moment du snapshot). L'ancien code confondait
      // "snapshot manquant" et "snapshot vide" — vérifions l'existence via
      // getById avant de lancer.
      if (!repo.getById(snapshotIdA)) {
        throw new Error(`Snapshot introuvable : ${snapshotIdA}`);
      }
      if (!repo.getById(snapshotIdB)) {
        throw new Error(`Snapshot introuvable : ${snapshotIdB}`);
      }

      return computeDiff(paragraphsA, paragraphsB);
    } finally {
      if (db) {db.close();}
    }
  });

  // ─── history:rollback (complet) ───
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
      const audit = new AuditService(db);

      const snapshot = historyRepo.getById(snapshotId);
      if (!snapshot) {
        throw new Error(`Snapshot introuvable : ${snapshotId}`);
      }

      // Restaurer tous les paragraphes
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

      // Journal d'audit
      audit.log({
        projectId,
        action: "rollback:full",
        entityType: "chapter",
        entityId: chapterId,
        details: {
          sourceSnapshotId: snapshotId,
          restoredVersion: snapshot.versionNumber,
          paragraphCount: snapshot.paragraphs.length,
        },
      });

      return { success: true, snapshotId: rollbackSnapshotId };
    } finally {
      if (db) {db.close();}
    }
  });

  // ─── history:rollback-partial (SDD §14.5) ───
  ipcMain.handle("history:rollback-partial", async (_event, payload) => {
    const { projectId, chapterId, snapshotId, paragraphIds } =
      historyRollbackPartialSchema.parse(payload);
    const projectPath = resolveProjectPath(projectId);
    let db: SqliteDatabase | null = null;

    try {
      db = createProjectDatabase(projectPath);
      runMigrations(db, migrationsDir);

      const historyRepo = new HistoryRepository(db);
      const paragraphRepo = new ParagraphRepository(db);
      const chapterRepo = new ChapterRepository(db);
      const audit = new AuditService(db);

      // Charger le snapshot source
      const snapshot = historyRepo.getFullParagraphs(snapshotId);
      if (!snapshot.length) {
        throw new Error(`Snapshot introuvable : ${snapshotId}`);
      }

      // Bug fix : les paragraphes des snapshots incrémentaux sont reconstruits
      // avec un ID synthétique (reconstructed-<baseSnapshotId>-<index>) qui
      // ne correspond à aucun UUID réel de la table paragraphs. L'ancien code
      // filtrait par p.id → aucun match pour les paragraphes ajoutés via un
      // snapshot incrémental → partial rollback silencieusement vide.
      // On résout ces IDs synthétiques en IDs réels via (chapterId, indexInChapter).
      const currentParagraphs = paragraphRepo.listByChapter(chapterId);
      const byIndex = new Map(
        currentParagraphs.map((p) => [p.indexInChapter, p]),
      );
      const resolvedParagraphs = snapshot
        .filter((p) => paragraphIds.includes(p.id))
        .map((p) => {
          if (p.id.startsWith("reconstructed-")) {
            const real = byIndex.get(p.indexInChapter);
            return real ?? p; // si pas trouvé, garde l'ID synthétique (sera ignoré par updateMany)
          }
          return p;
        });

      const selectedParagraphs = resolvedParagraphs.filter(
        (p) => !p.id.startsWith("reconstructed-"),
      );
      if (!selectedParagraphs.length) {
        throw new Error("Aucun paragraphe valide trouvé dans ce snapshot.");
      }

      // Restaurer seulement ces paragraphes
      paragraphRepo.updateMany(selectedParagraphs);

      // Vérifier si le chapitre est maintenant complètement traduit
      const allParagraphs = paragraphRepo.listByChapter(chapterId);
      const allTranslated = allParagraphs.every(
        (p) => p.status === "translated" || p.status === "reviewed",
      );
      if (allTranslated) {
        chapterRepo.updateStatus(chapterId, "completed");
      }

      // Créer un nouveau snapshot de rollback avec l'état COMPLET du chapitre
      // (pas seulement les paragraphes restaurés — sinon la chaîne incrémentale perd les paragraphes non sélectionnés)
      const rollbackSnapshotId = crypto.randomUUID();
      historyRepo.create({
        id: rollbackSnapshotId,
        projectId,
        chapterId,
        stage: "rollback_partial",
        paragraphs: allParagraphs,
        triggeredBy: "rollback",
      });

      // Journal d'audit
      audit.log({
        projectId,
        action: "rollback:partial",
        entityType: "chapter",
        entityId: chapterId,
        details: {
          sourceSnapshotId: snapshotId,
          paragraphCount: selectedParagraphs.length,
          paragraphIds,
        },
      });

      return {
        success: true,
        snapshotId: rollbackSnapshotId,
        restoredCount: selectedParagraphs.length,
      };
    } finally {
      if (db) {db.close();}
    }
  });

  // ─── history:get-paragraphs (reconstruit les paragraphes d'un snapshot) ───
  ipcMain.handle("history:get-paragraphs", async (_event, payload) => {
    const { projectId, snapshotId } =
      historyGetParagraphsSchema.parse(payload);
    const projectPath = resolveProjectPath(projectId);
    let db: SqliteDatabase | null = null;

    try {
      db = createProjectDatabase(projectPath);
      runMigrations(db, migrationsDir);

      const repo = new HistoryRepository(db);
      const paragraphs = repo.getFullParagraphs(snapshotId);

      return paragraphs;
    } finally {
      if (db) {db.close();}
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
        const audit = new AuditService(db);
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

        // Journal d'audit pour snapshot manuel
        if (input.triggeredBy === "manual") {
          audit.log({
            projectId: input.projectId,
            action: "snapshot:manual",
            entityType: "chapter",
            entityId: input.chapterId,
            details: {
              snapshotId,
              stage: input.stage,
            },
          });
        }

        const created = repo.getById(snapshotId);
        if (!created) {throw new Error("Échec de création du snapshot.");}
        return created;
      } finally {
        if (db) {db.close();}
      }
    },
  );

  // ─── audit:list ───
  ipcMain.handle("audit:list", async (_event, payload) => {
    const { projectId, limit } = payload as {
      projectId?: string;
      limit?: number;
    };
    const projectPath = resolveProjectPath(projectId ?? "");
    let db: SqliteDatabase | null = null;

    try {
      db = createProjectDatabase(projectPath);
      runMigrations(db, migrationsDir);
      const audit = new AuditService(db);

      const entries = projectId
        ? audit.list(projectId, limit ?? 100)
        : audit.listAll(limit ?? 100);

      return entries;
    } finally {
      if (db) {db.close();}
    }
  });
}
