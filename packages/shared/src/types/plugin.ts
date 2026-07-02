/**
 * SDD Volume 15 — Types du système de plugins NovelTrad
 *
 * Architecture inspirée du VS Code Extension Host :
 * - NovelTradPlugin : interface principale que chaque plugin doit exporter
 * - PluginContext : contexte passé à activate(), avec registre et abonnements
 * - Disposable / CompositeDisposable : gestion du cycle de vie des ressources
 * - PluginManifest : métadonnées du plugin (validé par Zod)
 * - PluginContribution : contributions déclarées dans le manifest
 */

// ── PluginManifest ────────────────────────────────────────────────────────────

export type PluginType =
  | "provider"
  | "agent"
  | "export"
  | "prompt-pack"
  | "workflow"
  | "ui-theme"
  | "parser"
  | "tool";

export type PluginPermission =
  | "ai"
  | "lexicon"
  | "project-read"
  | "project-write"
  | "fs-read"
  | "fs-write"
  | "network"
  | "ui";

/** Permissions considérées comme sensibles — nécessitent confirmation utilisateur */
export const SENSITIVE_PERMISSIONS: readonly PluginPermission[] = [
  "project-write",
  "fs-write",
  "network",
] as const;

export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  author?: string;
  description?: string;
  type: PluginType;
  entry: string;
  permissions: PluginPermission[];
  contributions?: PluginContributions;
  configSchema?: Record<string, unknown>;
}

export interface AgentContribution {
  stage: string;
  name: string;
  description?: string;
}

export interface ExportContribution {
  format: string;
  name: string;
  description?: string;
}

export interface ProviderContribution {
  id: string;
  name: string;
  description?: string;
}

export interface ParserContribution {
  extension: string;
  name: string;
  description?: string;
}

export interface PromptContribution {
  id: string;
  name: string;
  description?: string;
}

export interface CommandContribution {
  id: string;
  name: string;
  handler?: string;
}

export interface PluginContributions {
  agents?: AgentContribution[];
  exports?: ExportContribution[];
  providers?: ProviderContribution[];
  parsers?: ParserContribution[];
  prompts?: PromptContribution[];
  commands?: CommandContribution[];
}

// ── Abstractions minimales pour PluginContext ────────────────────────────────
// Ces interfaces permettent aux plugins d'appeler le chat IA et le lexique
// sans dépendre des classes concrètes du main process.

export interface PluginAiRouter {
  chat(providerId: string, messages: unknown[], options?: unknown): Promise<string>;
  streamChat(providerId: string, messages: unknown[], options?: unknown): AsyncIterable<string>;
}

export interface PluginLexiconEngine {
  apply(text: string, entries?: unknown[]): { text: string; substitutions: Array<{ before: string; after: string; locked: boolean }> };
}

export interface Logger {
  info(message: string, ...args: unknown[]): void;
  warn(message: string, ...args: unknown[]): void;
  error(message: string, ...args: unknown[]): void;
  debug(message: string, ...args: unknown[]): void;
}

export interface ConfigChangeListener {
  (config: Record<string, unknown>): void;
}

// ── NovelTradPlugin (interface principale) ───────────────────────────────────

export interface NovelTradPlugin {
  readonly manifest: PluginManifest;
  readonly apiVersion: string;
  activate(context: PluginContext): void | Promise<void>;
  deactivate(): void | Promise<void>;
}

// ── PluginContext (contexte passé à activate) ───────────────────────────────

export interface PluginContext {
  readonly pluginId: string;
  readonly projectId: string | null;
  readonly aiRouter: PluginAiRouter;
  readonly lexiconEngine: PluginLexiconEngine;
  readonly logger: Logger;

  registerAgent(stage: string, factory: unknown): void;
  registerExport(format: string, exporter: unknown): void;
  registerProvider(id: string, provider: unknown): void;
  registerPrompt(id: string, prompt: unknown): void;
  registerParser(extension: string, parser: unknown): void;
  registerCommand(id: string, handler: unknown): void;
  registerConfigChangeListener(listener: ConfigChangeListener): void;

  getConfig<T>(): T;
  setConfig<T>(config: T): void;

  readonly subscriptions: CompositeDisposable;
}

// ── Disposable (gestion cycle de vie) ───────────────────────────────────────

export interface Disposable {
  dispose(): void | Promise<void>;
}

export class CompositeDisposable {
  private disposables: Disposable[] = [];

  add(disposable: Disposable): void {
    this.disposables.push(disposable);
  }

  async dispose(): Promise<void> {
    for (const d of this.disposables) {
      try {
        await d.dispose();
      } catch (err) {
        console.error("[CompositeDisposable] Error during dispose:", err);
      }
    }
    this.disposables = [];
  }

  get size(): number {
    return this.disposables.length;
  }
}

// ── PluginServices (services passés au PluginHost) ──────────────────────────

export interface PluginServices {
  aiRouter: PluginAiRouter;
  lexiconEngine: PluginLexiconEngine;
  logger: Logger;
}

// ── LoadedPlugin (plugin chargé en mémoire) ─────────────────────────────────

export type PluginStatus = "inactive" | "active" | "error";

export interface LoadedPlugin {
  manifest: PluginManifest;
  path: string;
  instance: NovelTradPlugin;
  status: PluginStatus;
  errorMessage?: string;
}
