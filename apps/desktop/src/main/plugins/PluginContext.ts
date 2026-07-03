/**
 * SDD Volume 15 — Implémentation de PluginContext
 *
 * Contexte passé à chaque plugin lors de activate().
 * Fournit les services (AiRouter, LexiconEngine, Logger),
 * les méthodes d'enregistrement de contributions,
 * et la gestion des abonnements (subscriptions) via CompositeDisposable.
 *
 * Sécurité : les appels aux services sont filtrés par les permissions
 * déclarées dans le manifest du plugin. Un plugin sans la permission "ai"
 * ne peut pas appeler aiRouter.chat(), etc.
 */

import { EventEmitter } from "node:events";
import type {
  PluginContext as PluginContextInterface,
  NovelTradPlugin,
  PluginPermission,
  ConfigChangeListener,
} from "@shared/types/index.js";
import { CompositeDisposable } from "@shared/types/index.js";
import type { AiRouter } from "../services/AiRouter.js";
import type { LexiconEngine } from "../services/LexiconEngine.js";
import type { ExportEngine } from "../services/ExportEngine.js";
import type { Logger } from "@shared/types/index.js";
import { createPluginAiRouter, createPluginLexiconEngine } from "./types.js";

// Type pour le registre des contributions
export interface ContributionRegistry {
  agents: Map<string, unknown>;
  exports: Map<string, unknown>;
  providers: Map<string, unknown>;
  parsers: Map<string, unknown>;
  prompts: Map<string, unknown>;
  commands: Map<string, unknown>;
}

export class PluginContext implements PluginContextInterface {
  readonly pluginId: string;
  readonly projectId: string | null = null;

  readonly aiRouter;
  readonly lexiconEngine;
  readonly logger;

  readonly subscriptions: CompositeDisposable;

  private config: Record<string, unknown> = {};
  private configEmitter = new EventEmitter();
  private _registry: ContributionRegistry;
  private _exportEngine?: ExportEngine;
  private _permissions: readonly PluginPermission[];

  constructor(
    plugin: NovelTradPlugin,
    aiRouter: AiRouter,
    lexiconEngine: LexiconEngine,
    logger: Logger,
    registry: ContributionRegistry,
    config?: Record<string, unknown>,
    exportEngine?: ExportEngine,
    permissions?: PluginPermission[],
  ) {
    this.pluginId = plugin.manifest.id;
    this._permissions = permissions ?? plugin.manifest.permissions ?? [];
    this.aiRouter = this.createGuardedAiRouter(aiRouter);
    this.lexiconEngine = this.createGuardedLexiconEngine(lexiconEngine);
    this.logger = {
      info: (msg: string, ...args: unknown[]) => logger.info(`[${this.pluginId}] ${msg}`, ...args),
      warn: (msg: string, ...args: unknown[]) => logger.warn(`[${this.pluginId}] ${msg}`, ...args),
      error: (msg: string, ...args: unknown[]) =>
        logger.error(`[${this.pluginId}] ${msg}`, ...args),
      debug: (msg: string, ...args: unknown[]) =>
        logger.debug(`[${this.pluginId}] ${msg}`, ...args),
    };
    this.subscriptions = new CompositeDisposable();
    this._registry = registry;
    this._exportEngine = exportEngine;
    if (config) {
      this.config = config;
    }
  }

  // ── Permission guards ────────────────────────────────────────────────

  /**
   * Vérifie que le plugin possède la permission requise.
   * Lève une erreur si la permission n'est pas déclarée dans le manifest.
   */
  private assertPermission(required: PluginPermission): void {
    if (!this._permissions.includes(required)) {
      throw new Error(
        `Plugin "${this.pluginId}" n'a pas la permission "${required}". ` +
          `Permissions déclarées : [${this._permissions.join(", ")}]`,
      );
    }
  }

  /** Crée un aiRouter filtré par la permission "ai" */
  private createGuardedAiRouter(realRouter: AiRouter) {
    const self = this;
    return {
      chat: (providerId: string, messages: unknown[], options?: unknown) => {
        self.assertPermission("ai");
        return realRouter.chat(
          providerId,
          messages as Parameters<AiRouter["chat"]>[1],
          options as Parameters<AiRouter["chat"]>[2],
        );
      },
      streamChat: (providerId: string, messages: unknown[], options?: unknown) => {
        self.assertPermission("ai");
        return realRouter.streamChat(
          providerId,
          messages as Parameters<AiRouter["streamChat"]>[1],
          options as Parameters<AiRouter["streamChat"]>[2],
        );
      },
    };
  }

  /** Crée un lexiconEngine filtré par la permission "lexicon" */
  private createGuardedLexiconEngine(realEngine: LexiconEngine) {
    const self = this;
    return {
      apply: (text: string, entries?: unknown[]) => {
        self.assertPermission("lexicon");
        return realEngine.apply(text, entries as Parameters<LexiconEngine["apply"]>[1]);
      },
    };
  }

  // ── Registration methods ─────────────────────────────────────────────

  registerAgent(stage: string, factory: unknown): void {
    if (this._registry.agents.has(stage)) {
      this.logger.warn(`Agent déjà enregistré pour le stage "${stage}" — remplacement`);
    }
    this._registry.agents.set(stage, factory);
    // Auto-dispose quand le plugin est désactivé
    this.subscriptions.add({
      dispose: () => {
        const current = this._registry.agents.get(stage);
        if (current === factory) {
          this._registry.agents.delete(stage);
        }
      },
    });
  }

  registerExport(format: string, exporter: unknown): void {
    if (this._registry.exports.has(format)) {
      this.logger.warn(`Export déjà enregistré pour le format "${format}" — remplacement`);
    }
    this._registry.exports.set(format, exporter);

    // Connecter avec ExportEngine pour que le renderer soit appelé
    // lors de l'export (SDD §15, extensibilité ExportEngine)
    if (this._exportEngine) {
      this._exportEngine.registerRenderer(format, exporter as (input: unknown) => string | Buffer);
    }

    this.subscriptions.add({
      dispose: () => {
        const current = this._registry.exports.get(format);
        if (current === exporter) {
          this._registry.exports.delete(format);
        }
        // Nettoyer aussi dans ExportEngine
        if (this._exportEngine) {
          this._exportEngine.unregisterRenderer(format);
        }
      },
    });
  }

  registerProvider(id: string, provider: unknown): void {
    if (this._registry.providers.has(id)) {
      this.logger.warn(`Provider déjà enregistré pour l'id "${id}" — remplacement`);
    }
    this._registry.providers.set(id, provider);
    this.subscriptions.add({
      dispose: () => {
        const current = this._registry.providers.get(id);
        if (current === provider) {
          this._registry.providers.delete(id);
        }
      },
    });
  }

  registerPrompt(id: string, prompt: unknown): void {
    if (this._registry.prompts.has(id)) {
      this.logger.warn(`Prompt déjà enregistré pour l'id "${id}" — remplacement`);
    }
    this._registry.prompts.set(id, prompt);
    this.subscriptions.add({
      dispose: () => {
        const current = this._registry.prompts.get(id);
        if (current === prompt) {
          this._registry.prompts.delete(id);
        }
      },
    });
  }

  registerParser(extension: string, parser: unknown): void {
    if (this._registry.parsers.has(extension)) {
      this.logger.warn(`Parser déjà enregistré pour l'extension "${extension}" — remplacement`);
    }
    this._registry.parsers.set(extension, parser);
    this.subscriptions.add({
      dispose: () => {
        const current = this._registry.parsers.get(extension);
        if (current === parser) {
          this._registry.parsers.delete(extension);
        }
      },
    });
  }

  registerCommand(id: string, handler: unknown): void {
    if (this._registry.commands.has(id)) {
      this.logger.warn(`Commande déjà enregistrée pour l'id "${id}" — remplacement`);
    }
    this._registry.commands.set(id, handler);
    this.subscriptions.add({
      dispose: () => {
        const current = this._registry.commands.get(id);
        if (current === handler) {
          this._registry.commands.delete(id);
        }
      },
    });
  }

  registerConfigChangeListener(listener: ConfigChangeListener): void {
    this.configEmitter.on("config-change", listener);
    this.subscriptions.add({
      dispose: () => {
        this.configEmitter.off("config-change", listener);
      },
    });
  }

  // ── Config ───────────────────────────────────────────────────────────

  getConfig<T>(): T {
    return this.config as T;
  }

  setConfig<T>(config: T): void {
    this.config = config as Record<string, unknown>;
    this.configEmitter.emit("config-change", this.config);
  }
}
