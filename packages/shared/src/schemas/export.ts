import { z } from "zod";

/**
 * Formats d'export supportés.
 */
export const exportFormatSchema = z.enum([
  "markdown",
  "txt",
  "html",
  "docx",
  "epub",
]);

/**
 * Schéma d'un paragraphe pour l'export — version simplifiée.
 * Ne nécessite pas tous les champs de Paragraph, seulement ceux utilisés par ExportEngine.
 */
const exportParagraphSchema = z.object({
  id: z.string().uuid(),
  chapterId: z.string().uuid(),
  sourceText: z.string(),
  translatedText: z.string().optional(),
  indexInChapter: z.number().int().min(0),
  status: z.enum(["pending", "translated", "reviewed"]),
});

/**
 * Schéma pour la requête `export:run` — aligné avec l'interface ExportInput du SDD §13.2.
 */
export const exportRunSchema = z.object({
  projectId: z.string().uuid(),
  chapterId: z.string().uuid().optional(),
  title: z.string().min(1),
  author: z.string().optional(),
  paragraphs: z.array(exportParagraphSchema).min(1),
  format: exportFormatSchema,
  outputPath: z.string().min(1),
  options: z
    .object({
      includeTitle: z.boolean().optional(),
      includeParagraphNumbers: z.boolean().optional(),
      bilingual: z.boolean().optional(),
    })
    .optional(),
});

export type ExportRunInput = z.infer<typeof exportRunSchema>;

/**
 * Type de retour standardisé pour le handler export:run — conforme SDD §16.7.
 * Union discriminée : succès avec métadonnées ou échec avec erreur structurée.
 */
export const exportRunResultSchema = z.discriminatedUnion("success", [
  z.object({
    success: z.literal(true),
    path: z.string(),
    size: z.number(),
    format: exportFormatSchema,
  }),
  z.object({
    success: z.literal(false),
    error: z.object({
      code: z.string(),
      message: z.string(),
      details: z.string().optional(),
    }),
  }),
]);

export type ExportRunResult = z.infer<typeof exportRunResultSchema>;
