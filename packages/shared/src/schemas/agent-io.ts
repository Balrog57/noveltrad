import { z } from "zod";

// ---------------------------------------------------------------------------
// Shared paragraph shape (used in both input and output schemas)
// ---------------------------------------------------------------------------

const paragraphShape = z.object({
  id: z.string().min(1),
  chapterId: z.string().min(1),
  indexInChapter: z.number().int().min(0),
  sourceText: z.string(),
  translatedText: z.string().optional(),
  preTranslatedText: z.string().optional(),
  status: z.enum(["pending", "translated", "reviewed"]),
  metadata: z.record(z.unknown()).optional(),
});

// ---------------------------------------------------------------------------
// Agent input schemas
// ---------------------------------------------------------------------------

/** Schéma d'entrée générique (utilisé par tous les agents) */
export const agentInputSchema = z.object({
  projectId: z.string().min(1),
  chapterId: z.string().optional(),
  paragraphs: z.array(paragraphShape).optional(),
  text: z.string().optional(),
  previousOutput: z.string().optional(),
  lexicon: z
    .array(
      z.object({
        id: z.string(),
        projectId: z.string(),
        term: z.string(),
        translation: z.string(),
        aliases: z.array(z.string()).default([]),
        locked: z.boolean().default(false),
        priority: z.number().int().min(0).default(0),
      }),
    )
    .optional(),
  memoryMatches: z
    .array(
      z.object({
        sourceText: z.string(),
        targetText: z.string(),
        similarity: z.number().min(0).max(1),
        usageCount: z.number().int().min(0),
      }),
    )
    .optional(),
  options: z.record(z.unknown()).optional(),
});

// ---------------------------------------------------------------------------
// Agent output schemas — un par type d'agent
// ---------------------------------------------------------------------------

/** Sortie texte uniquement (GrammarAgent, StyleAgent, PolishAgent) */
export const textOutputSchema = z.object({
  text: z.string(),
  metadata: z.record(z.unknown()).optional(),
});

/** Sortie avec paragraphes (SplitAgent, PreTranslateAgent, TranslateAgent) */
export const paragraphsOutputSchema = z.object({
  paragraphs: z.array(paragraphShape),
  metadata: z.record(z.unknown()).optional(),
});

/** Sortie de l'agent de cohérence (ConsistencyAgent) */
export const consistencyOutputSchema = z.object({
  report: z.object({
    metrics: z.array(
      z.object({
        name: z.string(),
        source: z.number(),
        target: z.number(),
        ok: z.boolean(),
      }),
    ),
    warnings: z.array(
      z.object({
        severity: z.enum(["low", "medium", "high"]),
        message: z.string(),
      }),
    ),
    globalScore: z.number().min(0).max(100),
  }),
});

/** Sortie de l'agent lexique (LexiconAgent) */
export const lexiconOutputSchema = z.object({
  text: z.string(),
  substitutions: z.array(
    z.object({
      before: z.string(),
      after: z.string(),
      locked: z.boolean(),
    }),
  ),
});

/** Sortie de l'agent QA (QaAgent) */
export const qaOutputSchema = z.object({
  report: z.object({
    consistency: z.number().min(0).max(100),
    grammar: z.number().min(0).max(100),
    fluency: z.number().min(0).max(100),
    style: z.number().min(0).max(100),
    lexicon: z.number().min(0).max(100),
    hallucination: z.number().min(0).max(100),
    length: z.number().min(0).max(100),
    dialogue: z.number().min(0).max(100),
    globalScore: z.number().min(0).max(100),
    comments: z.string(),
  }),
  score: z.number().min(0).max(100),
});

/** Sortie de l'agent export (ExportAgent) */
export const exportOutputSchema = z.object({
  metadata: z
    .object({
      exportPath: z.string(),
    })
    .passthrough(),
});

// ---------------------------------------------------------------------------
// v1.4 — Schémas des nouveaux agents (review / revise / summarizer)
// ---------------------------------------------------------------------------

/** Sortie de l'agent Review (ReviewAgent) — rapport de corrections ciblées */
export const reviewOutputSchema = z.object({
  report: z.object({
    issues: z.array(
      z.object({
        paragraphIndex: z.number().int().min(0),
        severity: z.enum(["high", "medium", "low"]),
        category: z.enum([
          "fidelity",
          "fluency",
          "terminology",
          "style",
          "consistency",
        ]),
        original: z.string(),
        suggestion: z.string(),
        reason: z.string(),
      }),
    ),
    summary: z.string(),
  }),
  metadata: z.record(z.unknown()).optional(),
});

/** Sortie de l'agent Revise (ReviseAgent) — texte révisé */
export const reviseOutputSchema = z.object({
  text: z.string(),
  metadata: z.record(z.unknown()).optional(),
});

/** Sortie de l'agent Summarizer (SummarizerAgent) — résumés chapitre + roman */
export const summarizerOutputSchema = z.object({
  metadata: z
    .object({
      chapterSummary: z.string(),
      novelSummary: z.string(),
    })
    .passthrough(),
});
