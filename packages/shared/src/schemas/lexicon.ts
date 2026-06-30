import { z } from "zod";

/** Schéma de validation pour une entrée de lexique complète */
export const lexiconEntrySchema = z.object({
  id: z.string().uuid(),
  projectId: z.string().uuid(),
  term: z.string().min(1, "Le terme est requis"),
  translation: z.string().min(1, "La traduction est requise"),
  category: z.string().default("general"),
  aliases: z.array(z.string()).default([]),
  locked: z.boolean().default(false),
  forbidden: z.array(z.string()).optional(),
  priority: z.number().int().min(0).max(10).default(5),
  description: z.string().optional(),
  notes: z.string().optional(),
  gender: z.string().optional(),
  pronunciation: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type LexiconEntrySchema = z.infer<typeof lexiconEntrySchema>;

/** Payload pour sauvegarder une entrée de lexique */
export const lexiconSaveSchema = z.object({
  projectId: z.string().uuid(),
  entry: lexiconEntrySchema,
});

/** Payload pour supprimer une entrée de lexique */
export const lexiconDeleteSchema = z.object({
  projectId: z.string().uuid(),
  entryId: z.string().uuid(),
});

/** Payload pour lister les entrées d'un projet */
export const lexiconListSchema = z.object({
  projectId: z.string().uuid(),
});

/** Payload pour importer des entrées de lexique */
export const lexiconImportSchema = z.object({
  projectId: z.string().uuid(),
  format: z.enum(["csv", "json", "tsv"]),
  data: z.string(),
});

/** Payload pour exporter des entrées de lexique */
export const lexiconExportSchema = z.object({
  projectId: z.string().uuid(),
  format: z.enum(["csv", "json", "tsv"]),
});

/** Payload pour extraire des termes candidats */
export const lexiconExtractCandidatesSchema = z.object({
  text: z.string().min(1),
  language: z.string(),
});
