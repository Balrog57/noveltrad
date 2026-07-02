/**
 * SDD Volume 15 — PluginHost
 *
 * Hôte de plugins : découverte, chargement, activation, registre des contributions.
 *
 * Architecture inspirée du VS Code Extension Host :
 * - Découverte des plugins dans `app.getPath('userData') + '/plugins'`
 * - Validation du manifest.json via Zod
 * - Chargement ESM dynamique avec cache busting en dev (`?t=${Date.now()}`)
 * - Activation/désactivation avec isolation des erreurs (try/catch)
 * - Registre des contributions : agents, exports, providers, parsers, prompts, commands
 * - Flux de permissions différé : les plugins avec permissions sensibles
 *   (project-write, fs-write, network) nécessitent confirmation utilisateur
 *   avant activation
 */

import fs from "node:fs";
import path from "node:path";
import { app } from "electron";
import { pluginManifestSchema } from "@shared/schemas/plugin.js";
import type {
  PluginManifest,
  NovelTradPlugin,
  PluginPermission,
  PluginStatus,
} from "@shared/types/index.js";
import { SENSITIVE_PERMISSIONS } from "@shared/types/index.js";
import type { AiRouter } from "../services/AiRouter.js";
import type { LexiconEngine } from "../services/LexiconEngine.js";
import type { ExportEngine } from "../services/ExportEngine.js";
import { logger } from "../utils/logger.js";
import { assertWithinProject } from "../utils/paths.js";
import { PluginContext } from "./PluginContext.js";
import type { ContributionRegistry } from "./PluginContext.js";
import type { LoadedPlugin, PluginServices } from "./types.js";

export type { LoadedPlugin };

/** Callback pour les changements de hot-reload */
export type PluginChangeCallback = (pluginId: string, event: "change" | "add" | "unlink") => void;

export class PluginHost {
  /** Dossier où sont installés les plugins */
  readonly pluginDir: string;

  /** Services partagés injectés */
  private services: PluginServices;

  /** Référence à l'ExportEngine (optionnelle, pour registerRenderer) */
  private exportEngine?: ExportEngine;

  /** Plugins chargés en mémoire */
  private plugins: Map<string, LoadedPlugin> = new Map();

  /** Registre des contributions par catégorie */
  private registry: ContributionRegistry = {
    agents: new Map(),
    exports: new Map(),
    providers: new Map(),
    parsers: new Map(),
    prompts: new Map(),
    commands: new Map(),
  };

  /** IDs des plugins activés (persistés via SettingsManager) */
  private enabledPluginIds: Set<string> = new Set();

  /** Plugins en attente de confirmation de permissions */
  private pendingPermissionPlugins: LoadedPlugin[] = [];

  /** Watcher pour le hot-reload (dev) */
  private watcher: fs.FSWatcher | null = null;

  /** Callbacks de hot-reload */
  private changeCallbacks: PluginChangeCallback[] = [];

  constructor(services: PluginServices, exportEngine?: ExportEngine) {
    this.pluginDir = path.join(app.getPath("userData"), "plugins");
    this.services = services;
    this.exportEngine = exportEngine;
  }

  // ── Découverte et chargement ─────────────────────────────────────────

  /**
   * Découvre les plugins dans le dossier plugins/.
   * Lit et valide chaque manifest.json.
   * @returns Liste des manifests valides trouvés
   */
  discover(): PluginManifest[] {
    const manifests: PluginManifest[] = [];

    if (!fs.existsSync(this.pluginDir)) {
      fs.mkdirSync(this.pluginDir, { recursive: true });
      logger.info(`[PluginHost] Dossier plugins créé : ${this.pluginDir}`);
      return manifests;
    }

    const entries = fs.readdirSync(this.pluginDir, { withFileTypes: true });
    const dirs = entries.filter((e) => e.isDirectory());

    for (const dir of dirs) {
      const manifestPath = path.join(this.pluginDir, dir.name, "manifest.json");
      if (!fs.existsSync(manifestPath)) {
        logger.warn(`[PluginHost] Plugin "${dir.name}" : pas de manifest.json`);
        continue;
      }

      try {
        const raw = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
        const manifest = pluginManifestSchema.parse(raw);
        manifests.push(manifest);
        logger.info(`[PluginHost] Plugin découvert : ${manifest.id} v${manifest.version}`);
      } catch (err) {
        logger.error(`[PluginHost] Plugin "${dir.name}" : manifest invalide`, err);
      }
    }

    return manifests;
  }

  /**
   * Charge un plugin à partir de son dossier.
   * 1. Lit et valide le manifest
   * 2. Importe dynamiquement le module ESM
   * 3. Vérifie que le module exporte un NovelTradPlugin
   * 4. Crée le PluginContext
   * 5. Appelle activate()
   * 6. Enregistre les contributions
   */
  async load(pluginPath: string): Promise<LoadedPlugin> {
    const manifestPath = path.join(pluginPath, "manifest.json");
    if (!fs.existsSync(manifestPath)) {
      throw new Error(`Plugin introuvable : ${manifestPath}`);
    }

    const raw = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
    const manifest = pluginManifestSchema.parse(raw);

    // Vérifier si déjà chargé
    if (this.plugins.has(manifest.id)) {
      throw new Error(`Plugin déjà chargé : ${manifest.id}`);
    }

    // Construire le chemin absolu du point d'entrée
    const entryPath = path.resolve(pluginPath, manifest.entry);

    // SDD §21.3 — Protection contre le path traversal
    assertWithinProject(pluginPath, entryPath);

    // Cache busting en dev
    const isDev = !!process.env.VITE_DEV_SERVER_URL;
    const moduleKey = isDev ? `${entryPath}?t=${Date.now()}` : entryPath;

    // Importer le module ESM
    const mod = await import(moduleKey);
    const defaultExport = mod.default;
    if (!defaultExport || typeof defaultExport.activate !== "function") {
      throw new Error(
        `Le plugin "${manifest.id}" doit exporter un default avec une méthode activate()`,
      );
    }

    const instance: NovelTradPlugin = defaultExport;

    const loaded: LoadedPlugin = {
      manifest,
      path: pluginPath,
      instance,
      status: "inactive",
      moduleKey,
    };

    this.plugins.set(manifest.id, loaded);
    logger.info(`[PluginHost] Plugin chargé : ${manifest.id}`);

    return loaded;
  }

  /**
   * Active un plugin : crée le contexte, appelle activate(), enregistre les contributions.
   * Lève une exception en cas d'erreur (le caller doit try/catch).
   */
  async activatePlugin(pluginId: string): Promise<void> {
    const loaded = this.plugins.get(pluginId);
    if (!loaded) {
      throw new Error(`Plugin inconnu : ${pluginId}`);
    }

    if (loaded.status === "active") {
      logger.warn(`[PluginHost] Plugin déjà actif : ${pluginId}`);
      return;
    }

    // Créer le contexte avec config par défaut
    const config = loaded.manifest.configSchema
      ? this.getDefaultConfig(loaded.manifest.configSchema)
      : {};

    const context = new PluginContext(
      loaded.instance,
      this.services.aiRouter,
      this.services.lexiconEngine,
      this.services.logger,
      this.registry,
      config,
      this.exportEngine,
    );

    // Stocker les abonnements pour les disposer à la désactivation
    loaded.disposables = context.subscriptions;

    // Enregistrer les contributions du manifest avant activate()
    // Les enregistrements dynamiques dans activate() peuvent ensuite les surcharger
    this.registerContributions(loaded.manifest, loaded.instance);

    // Appeler activate()
    try {
      await loaded.instance.activate(context);
    } catch (err) {
      loaded.status = "error";
      loaded.errorMessage = String(err);
      logger.error(`[PluginHost] Erreur activate() pour "${pluginId}" :`, err);
      return;
    }

    loaded.status = "active";
    logger.info(`[PluginHost] Plugin activé : ${pluginId}`);
  }

  /**
   * Désactive un plugin : appelle deactivate(), nettoie les abonnements
   * et les contributions. Le plugin reste dans la Map pour pouvoir être
   * réactivé (contrairement à uninstallPlugin qui le supprime).
   */
  async deactivatePlugin(pluginId: string): Promise<void> {
    const loaded = this.plugins.get(pluginId);
    if (!loaded) return;

    // Appeler deactivate()
    try {
      if (loaded.status === "active") {
        await loaded.instance.deactivate();
      }
    } catch (err) {
      logger.error(`[PluginHost] Erreur deactivate() pour "${pluginId}" :`, err);
    }

    // Disposer les abonnements du contexte (nettoie les enregistrements
    // dynamiques, y compris le désenregistrement d'ExportEngine)
    if (loaded.disposables) {
      try {
        await loaded.disposables.dispose();
      } catch (err) {
        logger.error(`[PluginHost] Erreur dispose subscriptions pour "${pluginId}" :`, err);
      }
      loaded.disposables = undefined;
    }

    // Désenregistrer les contributions du manifest
    this.unregisterContributions(loaded.manifest);

    loaded.status = "inactive";

    logger.info(`[PluginHost] Plugin désactivé : ${pluginId}`);
  }

  /**
   * Désinstalle complètement un plugin : désactive, supprime de la Map
   * et efface le dossier du disque.
   */
  async uninstallPlugin(pluginId: string): Promise<void> {
    const loaded = this.plugins.get(pluginId);
    if (!loaded) {
      logger.warn(`[PluginHost] Plugin introuvable pour désinstallation : ${pluginId}`);
      return;
    }

    // Désactiver d'abord
    await this.deactivatePlugin(pluginId);

    // Supprimer de la Map
    this.plugins.delete(pluginId);

    // Supprimer le dossier du disque
    const pluginDir = loaded.path;
    if (fs.existsSync(pluginDir)) {
      try {
        fs.rmSync(pluginDir, { recursive: true, force: true });
        logger.info(`[PluginHost] Dossier plugin supprimé : ${pluginDir}`);
      } catch (err) {
        logger.error(`[PluginHost] Erreur suppression dossier plugin "${pluginDir}" :`, err);
      }
    }

    logger.info(`[PluginHost] Plugin désinstallé : ${pluginId}`);
  }

  /**
   * Initialisation complète au démarrage de l'application.
   * 1. Découvre les plugins
   * 2. Charge ceux qui sont activés ET sans permissions sensibles
   * 3. Retourne la liste des plugins nécessitant confirmation utilisateur
   *
   * @param enabledPluginIds IDs des plugins activés (depuis SettingsManager)
   * @returns Plugins en attente de confirmation de permissions
   */
  async init(enabledPluginIds: string[]): Promise<LoadedPlugin[]> {
    this.enabledPluginIds = new Set(enabledPluginIds);
    this.pendingPermissionPlugins = [];

    const manifests = this.discover();
    const sensitivePlugins: LoadedPlugin[] = [];

    for (const manifest of manifests) {
      const pluginDir = path.join(this.pluginDir, this.getPluginFolderName(manifest));

      try {
        const loaded = await this.load(pluginDir);

        // Si le plugin a des permissions sensibles et n'est pas encore activé
        const hasSensitive = manifest.permissions?.some((p: PluginPermission) =>
          (SENSITIVE_PERMISSIONS as readonly PluginPermission[]).includes(p),
        );

        if (hasSensitive && this.enabledPluginIds.has(manifest.id)) {
          // Ne pas activer tout de suite — attendre confirmation utilisateur
          sensitivePlugins.push(loaded);
          this.pendingPermissionPlugins.push(loaded);
        } else if (this.enabledPluginIds.has(manifest.id)) {
          // Activer immédiatement (pas de permissions sensibles)
          await this.activatePlugin(manifest.id);
        }
      } catch (err) {
        logger.error(`[PluginHost] Erreur chargement plugin "${manifest.id}" :`, err);
      }
    }

    return sensitivePlugins;
  }

  /**
   * Active les plugins dont les permissions ont été approuvées par l'utilisateur.
   * Appelé après le flux de confirmation IPC.
   */
  async activateApproved(approvedIds: string[]): Promise<void> {
    for (const pluginId of approvedIds) {
      const loaded = this.plugins.get(pluginId);
      if (loaded && loaded.status === "inactive") {
        await this.activatePlugin(pluginId);
      }
    }
    // Nettoyer la liste d'attente
    this.pendingPermissionPlugins = this.pendingPermissionPlugins.filter(
      (p) => !approvedIds.includes(p.manifest.id),
    );
  }

  /** Retourne la liste des plugins en attente de confirmation */
  getPendingPermissionPlugins(): LoadedPlugin[] {
    return [...this.pendingPermissionPlugins];
  }

  /** Vérifie si des plugins nécessitent confirmation */
  hasPendingPermissions(): boolean {
    return this.pendingPermissionPlugins.length > 0;
  }

  // ── Registre des contributions ───────────────────────────────────────

  /** Retourne la factory d'agent pour un stage donné (plugin d'abord) */
  getAgent(stage: string): unknown | undefined {
    return this.registry.agents.get(stage);
  }

  /** Retourne l'exporteur pour un format donné (plugin d'abord) */
  getExport(format: string): unknown | undefined {
    return this.registry.exports.get(format);
  }

  /** Retourne le provider pour un ID donné */
  getProvider(id: string): unknown | undefined {
    return this.registry.providers.get(id);
  }

  /** Retourne le parser pour une extension donnée */
  getParser(extension: string): unknown | undefined {
    return this.registry.parsers.get(extension);
  }

  /** Retourne le prompt pour un ID donné */
  getPrompt(id: string): unknown | undefined {
    return this.registry.prompts.get(id);
  }

  /** Retourne la commande pour un ID donné */
  getCommand(id: string): unknown | undefined {
    return this.registry.commands.get(id);
  }

  /** Liste tous les plugins chargés */
  list(): LoadedPlugin[] {
    return Array.from(this.plugins.values());
  }

  /** Retourne un plugin par son ID */
  get(pluginId: string): LoadedPlugin | undefined {
    return this.plugins.get(pluginId);
  }

  // ── Hot-reload (dev) ─────────────────────────────────────────────────

  /**
   * Démarre la surveillance du dossier plugins/ en mode développement.
   * Débounce de 500ms pour éviter les reloads multiples.
   */
  watch(callback?: PluginChangeCallback): void {
    if (!process.env.VITE_DEV_SERVER_URL) return; // Désactivé en production

    if (callback) {
      this.changeCallbacks.push(callback);
    }

    if (this.watcher) return; // Déjà en cours

    let debounceTimer: NodeJS.Timeout | null = null;

    this.watcher = fs.watch(this.pluginDir, { recursive: true }, (eventType, filename) => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(async () => {
        if (!filename) return;

        // Déterminer quel plugin est concerné
        const parts = filename.split(path.sep);
        const pluginFolder = parts[0];

        // Trouver le plugin par son dossier
        const pluginId = this.findPluginIdByFolder(pluginFolder);
        if (!pluginId) return;

        logger.info(`[PluginHost] Hot-reload détecté pour "${pluginFolder}"`);

        // Notifier les callbacks
        const event =
          eventType === "rename"
            ? fs.existsSync(path.join(this.pluginDir, pluginFolder))
              ? "add"
              : "unlink"
            : "change";
        for (const cb of this.changeCallbacks) {
          try {
            cb(pluginId, event);
          } catch (e) {
            logger.error("[PluginHost] Erreur callback hot-reload :", e);
          }
        }

        // Recharger le plugin
        try {
          // Désactiver sans supprimer la Map (pour nettoyer les subscriptions)
          await this.deactivatePlugin(pluginId);
          // Supprimer de la Map pour permettre le re-load
          this.plugins.delete(pluginId);
          const pluginPath = path.join(this.pluginDir, pluginFolder);
          if (fs.existsSync(pluginPath)) {
            await this.load(pluginPath);
            if (this.enabledPluginIds.has(pluginId)) {
              await this.activatePlugin(pluginId);
            }
          }
        } catch (err) {
          logger.error(`[PluginHost] Erreur hot-reload pour "${pluginFolder}" :`, err);
        }
      }, 500);
    });

    logger.info("[PluginHost] Surveillance hot-reload activée");
  }

  /** Arrête la surveillance */
  unwatch(): void {
    if (this.watcher) {
      this.watcher.close();
      this.watcher = null;
      logger.info("[PluginHost] Surveillance hot-reload désactivée");
    }
  }

  // ── Méthodes privées ─────────────────────────────────────────────────

  /**
   * Enregistre les contributions déclarées dans le manifest.
   */
  private registerContributions(manifest: PluginManifest, instance: NovelTradPlugin): void {
    if (!manifest.contributions) return;

    // Agents
    if (manifest.contributions.agents) {
      for (const agent of manifest.contributions.agents) {
        this.registry.agents.set(agent.stage, instance);
      }
    }

    // Exports — les exports sont enregistrés dynamiquement via
    // context.registerExport() dans activate(), qui interconnecte
    // automatiquement avec ExportEngine. On ne surcharge pas ici.
    // Les manifest.exports déclarent juste les formats supportés.

    // Providers
    if (manifest.contributions.providers) {
      for (const prov of manifest.contributions.providers) {
        this.registry.providers.set(prov.id, instance);
      }
    }

    // Parsers
    if (manifest.contributions.parsers) {
      for (const parser of manifest.contributions.parsers) {
        this.registry.parsers.set(parser.extension, instance);
      }
    }

    // Prompts
    if (manifest.contributions.prompts) {
      for (const prompt of manifest.contributions.prompts) {
        this.registry.prompts.set(prompt.id, instance);
      }
    }

    // Commands
    if (manifest.contributions.commands) {
      for (const cmd of manifest.contributions.commands) {
        this.registry.commands.set(cmd.id, instance);
      }
    }
  }

  /**
   * Désenregistre les contributions d'un plugin.
   */
  private unregisterContributions(manifest: PluginManifest): void {
    if (!manifest.contributions) return;

    if (manifest.contributions.agents) {
      for (const agent of manifest.contributions.agents) {
        this.registry.agents.delete(agent.stage);
      }
    }
    if (manifest.contributions.exports) {
      for (const exp of manifest.contributions.exports) {
        this.registry.exports.delete(exp.format);
      }
    }
    if (manifest.contributions.providers) {
      for (const prov of manifest.contributions.providers) {
        this.registry.providers.delete(prov.id);
      }
    }
    if (manifest.contributions.parsers) {
      for (const parser of manifest.contributions.parsers) {
        this.registry.parsers.delete(parser.extension);
      }
    }
    if (manifest.contributions.prompts) {
      for (const prompt of manifest.contributions.prompts) {
        this.registry.prompts.delete(prompt.id);
      }
    }
    if (manifest.contributions.commands) {
      for (const cmd of manifest.contributions.commands) {
        this.registry.commands.delete(cmd.id);
      }
    }
  }

  /**
   * Déduit le nom du dossier à partir de l'ID du plugin.
   * Par défaut, utilise l'ID comme nom de dossier.
   */
  private getPluginFolderName(manifest: PluginManifest): string {
    return manifest.id;
  }

  /**
   * Trouve l'ID d'un plugin à partir de son nom de dossier.
   */
  private findPluginIdByFolder(folderName: string): string | undefined {
    for (const [id, loaded] of this.plugins) {
      const expectedFolder = this.getPluginFolderName(loaded.manifest);
      if (expectedFolder === folderName) return id;
    }
    return undefined;
  }

  /**
   * Génère une configuration par défaut à partir du configSchema du manifest.
   */
  private getDefaultConfig(configSchema: Record<string, unknown>): Record<string, unknown> {
    const config: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(configSchema)) {
      if (typeof value === "object" && value !== null && "default" in value) {
        config[key] = (value as { default: unknown }).default;
      }
    }
    return config;
  }
}
