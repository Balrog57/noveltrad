import { z } from "zod";

/**
 * Schéma d'un paragraphe — aligné avec l'interface Paragraph du SDD.
 */
export const paragraphSchema = z.object({
  id: z.string().uuid(),
  chapterId: z.string().uuid(),
  indexInChapter: z.number().int().min(0),
  sourceText: z.string(),
  translatedText: z.string().optional(),
  preTranslatedText: z.string().optional(),
  status: z.enum(["pending", "translated", "reviewed"]),
  metadata: z.record(z.unknown()).optional(),
});

/**
 * Schéma pour la requête `chapter:get-paragraphs`.
 */
export const getParagraphsSchema = z.object({
  chapterId: z.string().uuid(),
});

/**
 * Schéma pour la requête `chapter:save`.
 * Reçoit un chapitre et la liste complète des paragraphes à sauvegarder.
 */
export const saveChapterSchema = z.object({
  chapterId: z.string().uuid(),
  paragraphs: z.array(paragraphSchema),
});
