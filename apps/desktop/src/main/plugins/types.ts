/**
 * Types internes du PluginHost.
 * Étend les types partagés avec les interfaces concrètes du main process.
 */

import type {
  PluginManifest,
  NovelTradPlugin,
  PluginStatus,
  PluginAiRouter,
  PluginLexiconEngine,
  Logger,
  CompositeDisposable,
} from "@shared/types/index.js";
import type { AiRouter } from "../services/AiRouter.js";
import type { LexiconEngine } from "../services/LexiconEngine.js";

/** Services concrets passés au PluginHost par l'application hôte */
export interface PluginServices {
  aiRouter: AiRouter;
  lexiconEngine: LexiconEngine;
  logger: Logger;
}

/** Plugin chargé en mémoire, avec état et métadonnées */
export interface LoadedPlugin {
  manifest: PluginManifest;
  path: string;
  instance: NovelTradPlugin;
  status: PluginStatus;
  errorMessage?: string;
  /** Nom du module pour le cache busting */
  moduleKey?: string;
  /** Abonnements du PluginContext (disposés à la désactivation) */
  disposables?: CompositeDisposable;
  /** Référence au PluginContext (pour getConfig/setConfig via IPC) */
  context?: unknown;
}

/** Adaptateur PluginAiRouter vers AiRouter concret */
export function createPluginAiRouter(realRouter: AiRouter): PluginAiRouter {
  return {
    chat: (providerId, messages, options) => realRouter.chat(providerId, messages as Parameters<AiRouter["chat"]>[1], options as Parameters<AiRouter["chat"]>[2]),
    streamChat: (providerId, messages, options) => realRouter.streamChat(providerId, messages as Parameters<AiRouter["streamChat"]>[1], options as Parameters<AiRouter["streamChat"]>[2]),
  };
}

/** Adaptateur PluginLexiconEngine vers LexiconEngine concret */
export function createPluginLexiconEngine(realEngine: LexiconEngine): PluginLexiconEngine {
  return {
    apply: (text, entries) => realEngine.apply(text, entries as Parameters<LexiconEngine["apply"]>[1]),
  };
}
