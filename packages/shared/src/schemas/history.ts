import { z } from "zod";

/**
 * Schéma pour lister les snapshots d'un projet ou d'un chapitre.
 */
export const historyListSchema = z.object({
  projectId: z.string().uuid(),
  chapterId: z.string().uuid().optional(),
});

/**
 * Schéma pour créer un snapshot manuel.
 */
export const historyCreateSchema = z.object({
  projectId: z.string().uuid(),
  chapterId: z.string().uuid(),
  stage: z.string(),
  paragraphs: z.array(
    z.object({
      id: z.string().uuid(),
      chapterId: z.string().uuid(),
      indexInChapter: z.number().int().min(0),
      sourceText: z.string(),
      translatedText: z.string().optional(),
      preTranslatedText: z.string().optional(),
      status: z.enum(["pending", "translated", "reviewed"]),
      metadata: z.record(z.unknown()).optional(),
    }),
  ),
  jobId: z.string().uuid().optional(),
  stepId: z.string().uuid().optional(),
  triggeredBy: z.enum(["workflow", "manual", "rollback"]),
});

/**
 * Schéma pour la requête de rollback.
 * Restaure les paragraphes d'un snapshot donné.
 */
export const historyRollbackSchema = z.object({
  projectId: z.string().uuid(),
  chapterId: z.string().uuid(),
  snapshotId: z.string().uuid(),
});

/**
 * Schéma pour la requête de diff entre deux snapshots.
 */
export const historyDiffSchema = z.object({
  projectId: z.string().uuid(),
  snapshotIdA: z.string().uuid(),
  snapshotIdB: z.string().uuid(),
});

export type HistoryListInput = z.infer<typeof historyListSchema>;
export type HistoryCreateInput = z.infer<typeof historyCreateSchema>;
export type HistoryRollbackInput = z.infer<typeof historyRollbackSchema>;
export type HistoryDiffInput = z.infer<typeof historyDiffSchema>;
