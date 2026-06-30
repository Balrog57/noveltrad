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
  | "split"
  | "pre_translate"
  | "translate"
  | "consistency"
  | "lexicon"
  | "grammar"
  | "style"
  | "polish"
  | "qa"
  | "export";

export interface WorkflowOptions {
  sourceLanguage?: string;
  targetLanguage?: string;
  qualityThreshold?: number;
  parallelAgents?: number;
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
  metrics: Array<{ name: string; source: number; target: number; ok: boolean }>;
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
  updateChannel: "latest" | "beta" | "alpha";
  ragEnabled: boolean;
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

export interface AiProvider {
  readonly id: string;
  readonly name: string;
  readonly model: string;
  readonly host?: string;
  readonly apiKey?: string;
  listModels(): Promise<string[]>;
  chat(messages: ChatMessage[], options?: ChatOptions): Promise<string>;
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
