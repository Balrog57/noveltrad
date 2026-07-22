export * from "./plugin.js";

export interface Project {
  id: string;
  name: string;
  author?: string;
  sourceLanguage: string;
  targetLanguage: string;
  path: string;
  createdAt: string;
  updatedAt: string;
}

export interface Chapter {
  id: string;
  projectId: string;
  title?: string;
  sourcePath?: string;
  orderIndex: number;
  status: "pending" | "processing" | "completed" | "error";
  createdAt: string;
  updatedAt: string;
}

export interface Paragraph {
  id: string;
  chapterId: string;
  indexInChapter: number;
  sourceText: string;
  translatedText?: string;
  preTranslatedText?: string;
  status: "pending" | "translated" | "reviewed";
  metadata?: Record<string, unknown>;
}

export interface LexiconEntry {
  id: string;
  projectId: string;
  term: string;
  translation: string;
  category: string;
  aliases: string[];
  locked: boolean;
  forbidden?: string[];
  priority: number;
  description?: string;
  notes?: string;
  gender?: string;
  pronunciation?: string;
  metadata?: Record<string, unknown>;
}

export interface CandidateTerm {
  term: string;
  occurrences: number;
  suggestedCategory?: string;
}

export interface TranslationMemoryMatch {
  sourceText: string;
  targetText: string;
  similarity: number;
  usageCount: number;
}

export type WorkflowStage =
  // ── v3 : pipeline simplifié 4-stages (translate → proofread → glossary → validate) ──
  | "translate"
  | "proofread"
  | "glossary"
  | "validate"
  // ── stages historiques (conservés pour la transition v3 ; supprimés en Phase 3) ──
  | "split"
  | "pre_translate"
  | "consistency"
  | "lexicon"
  | "grammar"
  | "style"
  | "polish"
  | "review" // v1.4 : boucle de révision pro
  | "revise" // v1.4 : applique les corrections du ReviewReport
  | "qa"
  | "export";

export interface WorkflowOptions {
  sourceLanguage?: string;
  targetLanguage?: string;
  qualityThreshold?: number;
  parallelAgents?: number;
  stepTimeoutMs?: number;
  [key: string]: unknown;
}

export interface Job {
  id: string;
  projectId: string;
  chapterId?: string;
  chapterIds?: string[];
  type: "single" | "batch";
  status:
    "pending" | "running" | "paused" | "completed" | "failed" | "cancelled";
  startedAt?: string;
  finishedAt?: string;
  errorMessage?: string;
  options?: WorkflowOptions;
  metadata?: Record<string, unknown>;
  costUsd?: number;
  /** Guards anti-boucle : compteur de retries QA automatiques (migration 017). */
  qaRetryCount?: number;
  createdAt: string;
}

export interface Step {
  id: string;
  jobId: string;
  agentId: string;
  name: string;
  stage: WorkflowStage;
  orderIndex: number;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  inputSnapshot?: Record<string, unknown>;
  outputSnapshot?: Record<string, unknown>;
  score?: number;
  tokensIn?: number;
  tokensOut?: number;
  durationMs?: number;
  stepTimeoutMs?: number;
  startedAt?: string;
  finishedAt?: string;
  errorMessage?: string;
  createdAt: string;
}

export interface AgentInput {
  projectId: string;
  chapterId?: string;
  paragraphs?: Paragraph[];
  text?: string;
  previousOutput?: string;
  lexicon?: LexiconEntry[];
  memoryMatches?: TranslationMemoryMatch[];
  options?: Record<string, unknown>;
}

export interface AgentOutput {
  text?: string;
  paragraphs?: Paragraph[];
  report?: unknown;
  score?: number;
  substitutions?: Array<{ before: string; after: string; locked: boolean }>;
  corrections?: Array<{ before: string; after: string; rule: string }>;
  metadata?: Record<string, unknown>;
}

export interface ConsistencyReport {
  metrics: Array<{ name: string; source: number; target: number; ok: boolean; score: number }>;
  warnings: Array<{ severity: "low" | "medium" | "high"; message: string }>;
  globalScore: number;
}

export interface QualityReport {
  consistency: number;
  grammar: number;
  fluency: number;
  style: number;
  lexicon: number;
  hallucination: number;
  length: number;
  dialogue: number;
  globalScore: number;
  comments: string;
  /** QA per-sentence : phrases suspectes avec score individuel (optionnel, rétrocompatible). */
  suspectSentences?: Array<{ sentence: string; score: number; issue: string }>;
  /** QA per-sentence : instructions de retry ciblées si globalScore < seuil (vide sinon). */
  retryInstructions?: string;
}

// ── v1.4 : Boucle de révision pro (review / revise) ───────────────────────

/**
 * Catégorie de problème identifié par l'agent Review.
 * SDD §8.10 (v1.4)
 */
export type ReviewCategory =
  | "fidelity"
  | "fluency"
  | "terminology"
  | "style"
  | "consistency";

/**
 * Une correction ciblée produite par le ReviewAgent.
 * SDD §8.10 (v1.4) — inspiration honya (Reviewer), LaTeXTrans (Validator).
 */
export interface ReviewIssue {
  /** Index (0-based) du paragraphe concerné dans la séquence traduite */
  paragraphIndex: number;
  severity: "high" | "medium" | "low";
  category: ReviewCategory;
  /** Extrait du texte à corriger */
  original: string;
  /** Correction proposée */
  suggestion: string;
  /** Justification courte */
  reason: string;
}

/**
 * Rapport produit par le ReviewAgent, consommé par le ReviseAgent.
 * Persisté dans la table `review_reports` (migration 014).
 */
export interface ReviewReport {
  issues: ReviewIssue[];
  /** Synthèse globale du réviseur */
  summary: string;
}

// ── v1.4 : Summarizer transverse (cohérence cross-chapitre) ──────────────

/**
 * Résumé d'un chapitre, produit par le SummarizerAgent.
 * SDD §8.12 (v1.4) — inspiration LaTeXTrans (Summarizer), TransAgents.
 */
export interface ChapterSummary {
  id: string;
  chapterId: string;
  projectId: string;
  summary: string;
  tokenCount?: number;
  createdAt: string;
}

/**
 * Résumé incrémental du roman entier, maintenu au fil des chapitres
 * et injecté dans le contexte des stages translate/style/polish.
 */
export interface NovelSummary {
  id: string;
  projectId: string;
  summary: string;
  version: number;
  updatedAt: string;
}

export type ExportFormat = "markdown" | "txt" | "html" | "docx" | "epub";

export interface ExportInput {
  chapterId?: string;
  projectId: string;
  title: string;
  author?: string;
  paragraphs: Paragraph[];
  format: ExportFormat;
  outputPath?: string;
  options?: {
    includeTitle?: boolean;
    includeParagraphNumbers?: boolean;
    bilingual?: boolean;
  };
}

export interface OllamaModelInfo {
  name: string;
  size?: number;
  parameterSize?: string;
  quantizationLevel?: string;
}

export interface AiProviderConfig {
  id: string;
  provider:
    | "ollama"
    | "openai"
    | "anthropic"
    | "gemini"
    | "openrouter"
    | "lmstudio"
    | "custom";
  name: string;
  model: string;
  host?: string;
  apiKey?: string;
  isDefault: boolean;
  isFallback: boolean;
}

export interface RagMatch {
  paragraphId: string;
  sourceText: string;
  translatedText: string;
  similarity: number;
}

export interface AppSettings {
  firstRunCompleted: boolean;
  ollamaHost: string;
  defaultModel: string;
  defaultPreTranslateModel: string;
  sourceLanguage: string;
  targetLanguage: string;
  defaultProjectsPath: string;
  theme: "dark" | "light" | "system";
  recentProjects: string[];
  updateChannel: "latest" | "beta" | "alpha";
  ragEnabled: boolean;
  /** SDD §7.9 : concurrence des jobs batch (défaut 1 pour Ollama local) */
  maxConcurrentJobs: number;
  /** SDD §12.5 : seuil de qualité minimum (défaut 70) */
  qualityThreshold: number;
  /** SDD §7.10 : timeout par étape en ms (défaut 120000 = 2 min) */
  stepTimeoutMs: number;
  /** SDD §11.4 : tolérances de cohérence par paire de langues */
  consistencyTolerances: Record<string, ConsistencyTolerance>;
  /** SDD §3.8 : coût par modèle (clé = model id). Vide = pas de suivi (Ollama local). */
  modelCosts: Record<string, { costPerInputToken: number; costPerOutputToken: number }>;
  /** SDD §15 : plugins activés (liste des IDs) */
  enabledPlugins: string[];
  /** SDD §4.11.1 : provider IA actif */
  activeProvider: "ollama" | "openai" | "anthropic" | "gemini" | "openrouter" | "lmstudio";
  /** SDD §4.11.1 : provider de fallback */
  fallbackProvider: "" | "ollama" | "openai" | "anthropic" | "gemini" | "openrouter" | "lmstudio";
  /** SDD §4.11.1 : clé API pour les providers cloud */
  apiKey: string;
  /** SDD §4.11.4 : langue de l'interface */
  uiLanguage: "fr" | "en";
  /** SDD §4.11.4 : taille de police dans l'éditeur */
  editorFontSize: number;
  /** SDD §4.11.5 : niveau de log */
  logLevel: "debug" | "info" | "warn" | "error";
  /** SDD §22.2 : utiliser les Worker threads pour les agents CPU-bound */
  useWorkerThreads: boolean;
  /** v1.4 SDD §7.12 : activer la boucle de révision pro (review/revise) */
  reviewLoopEnabled: boolean;
  /** v1.4 SDD §7.13 : activer le Summarizer transverse (cohérence cross-chapitre) */
  summarizerEnabled: boolean;
  /** SDD §17.9 : vérification automatique des mises à jour */
  autoUpdateCheck: boolean;
  /** Guards anti-boucle : nb max de retries QA automatiques par chapitre (défaut 3). */
  maxQaRetries: number;
  /** Guards anti-boucle : plafond de tokens cumulés par job, 0 = désactivé (défaut 50000). */
  maxJobTokens: number;
}

export interface CreateProjectPayload {
  name: string;
  author?: string;
  sourceLanguage: string;
  targetLanguage: string;
  parentPath: string;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatOptions {
  temperature?: number;
  maxTokens?: number;
  jsonMode?: boolean;
}

/**
 * SDD §3.8 : usage de tokens renvoyé par le provider après un appel chat().
 * Permet le suivi de consommation (job.costUsd, cap maxJobTokens).
 * Optionnel : les providers qui ne l'exposent pas renvoient undefined.
 */
export interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

/**
 * Résultat d'un appel chat() incluant l'usage de tokens.
 * `chat()` (hérité) retourne seulement le contenu string ; `chatWithUsage()`
 * retourne le contenu + l'usage pour le suivi de consommation.
 */
export interface ChatResult {
  content: string;
  usage?: TokenUsage;
}

export interface AiProvider {
  readonly id: string;
  readonly name: string;
  readonly model: string;
  readonly host?: string;
  readonly apiKey?: string;
  listModels(): Promise<string[]>;
  chat(messages: ChatMessage[], options?: ChatOptions): Promise<string>;
  /**
   * Variante de chat() qui retourne aussi l'usage de tokens (SDD §3.8).
   * L'implémentation par défaut peut déléguer à chat() et omettre l'usage.
   */
  chatWithUsage?(
    messages: ChatMessage[],
    options?: ChatOptions,
  ): Promise<ChatResult>;
  streamChat(
    messages: ChatMessage[],
    options?: ChatOptions,
  ): AsyncIterable<string>;
  embeddings(texts: string[]): Promise<number[][]>;
  isAvailable(): Promise<boolean>;
}

export interface Substitution {
  before: string;
  after: string;
  locked: boolean;
}

export interface LexiconApplyResult {
  text: string;
  substitutions: Array<{ before: string; after: string; locked: boolean }>;
}

/** Type de déclencheur d'un snapshot d'historique */
export type SnapshotTrigger = "workflow" | "manual" | "rollback";

/** Représente un snapshot de l'historique des versions */
export interface HistorySnapshot {
  id: string;
  projectId: string;
  chapterId?: string;
  jobId?: string;
  stepId?: string;
  stage: string;
  paragraphs: Paragraph[];
  qualityScore?: number;
  triggeredBy: SnapshotTrigger;
  createdAt: string;
  /** Numéro de version, dérivé de l'ordre chronologique (non stocké) */
  versionNumber?: number;
}

/** Résultat d'une comparaison entre deux snapshots */
export interface DiffResult {
  changes: ParagraphChange[];
}

/** Représente un changement au niveau d'un paragraphe */
export interface ParagraphChange {
  index: number;
  type: "added" | "removed" | "modified";
  sourceBefore?: string;
  sourceAfter?: string;
  targetBefore?: string;
  targetAfter?: string;
}

// ── Phase D : Qualité avancée (SDD §12.5, §12.6, §11.4) ──

/** SDD §12.5 : Calibration d'un modèle sur une dimension de qualité */
export interface ModelCalibration {
  model: string;
  dimension: string;
  slope: number;
  offset: number;
  sampleCount: number;
  updatedAt: string;
}

/** SDD §12.6 : Rapport de détection d'hallucination */
export interface HallucinationReport {
  /** Score d'hallucination (0 = beaucoup d'hallucinations, 100 = aucune) */
  score: number;
  /** Entités nommées présentes dans la cible mais absentes du source (potentiellement inventées) */
  inventedEntities: string[];
  /** Nombres de chapitres/personnages mentionnés dans la cible sans être dans le source */
  suspiciousReferences: string[];
  /** Avertissements détaillés */
  warnings: string[];
}

/** SDD §11.4 : Tolérances de cohérence configurables par paire de langues */
export interface ConsistencyTolerance {
  /** Ratio minimal du nombre de phrases (cible/source) */
  sentenceRatioMin: number;
  /** Ratio maximal du nombre de phrases (cible/source) */
  sentenceRatioMax: number;
  /** Ratio minimal de longueur (cible/source) */
  lengthRatioMin: number;
  /** Ratio maximal de longueur (cible/source) */
  lengthRatioMax: number;
  /** Ignorer les nombres dans les dialogues pour le calcul de cohérence */
  ignoreNumbersInDialogues: boolean;
  /** Ignorer les différences de ponctuation */
  ignorePunctuationMismatch: boolean;
}

/** Paire de langues au format "source-cible" (ex: "zh-fr", "ja-fr", "en-fr") */
export type LanguagePair = string;

// ── Phase F : Gestion de projets avancée (SDD §5.8, §5.10, §5.11) ──

/** Options de re-synchronisation source (SDD §5.8) */
export type RefreshStrategy = "replace" | "merge" | "new-version";

/** Informations de doublon détecté (SDD §5.10) */
export interface DuplicateInfo {
  /** ID du chapitre existant en conflit */
  existingChapterId: string;
  /** Titre du chapitre existant */
  existingTitle: string;
  /** Type de doublon détecté */
  type: "title" | "sha256" | "both";
  /** Hash SHA256 du fichier en cours d'import */
  fileHash: string;
  /** Hash SHA256 du fichier existant (si applicable) */
  existingHash?: string;
}

/** Map des tolérances par paire de langues */
export type ConsistencyTolerances = Record<LanguagePair, ConsistencyTolerance>;

// ── Phase E : Historique avancé (SDD §14.3, §14.5, §14.6) ──

/** Type de snapshot hybride : complet ou incrémental */
export type SnapshotStorageType = "full" | "incremental";

/** Métadonnées de snapshot enrichies (SDD §14.3) */
export interface SnapshotMetadata {
  triggeredBy: SnapshotTrigger;
  snapshotType?: SnapshotStorageType;
  isCompressed?: boolean;
  baseSnapshotId?: string;
  /** Numéro de version pour décider du type de snapshot */
  versionNumber?: number;
}

/** Changement incrémental entre deux snapshots */
export interface IncrementalChange {
  index: number;
  sourceText: string;
  translatedText?: string;
  status: Paragraph["status"];
}

/** Payload stocké dans la colonne paragraphs pour un snapshot incrémental */
export interface IncrementalPayload {
  _type: "incremental";
  baseSnapshotId: string;
  changes: IncrementalChange[];
}

// ── Phase H : Lexique avancé (SDD §10.9, §10.10) ──

/** Type de conflit lexical */
export type LexiconConflictType = "duplicate_term" | "overlap";

/** Conflit détecté entre deux entrées lexicales */
export interface LexiconConflict {
  type: LexiconConflictType;
  entryA: LexiconEntry;
  entryB: LexiconEntry;
  description: string;
  normalized?: string;
}

/** Suggestion IA pour un terme inconnu */
export interface LexiconSuggestion {
  translation: string;
  category: string;
  explanation: string;
}

/** Entrée du journal d'audit (SDD §14.6) */
export interface AuditEntry {
  id: string;
  projectId?: string;
  action: string;
  entityType?: string;
  entityId?: string;
  details?: Record<string, unknown>;
  createdAt: string;
}
