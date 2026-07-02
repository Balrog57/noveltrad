/**
 * SDD Volume 15 — Handlers IPC pour les plugins
 *
 * Canaux :
 * - plugin:list                → liste des plugins chargés
 * - plugin:enable              → active un plugin
 * - plugin:disable             → désactive un plugin
 * - plugin:uninstall           → supprime un plugin
 * - plugin:install             → retourne "non supporté en v1.0"
 * - plugin:get-config          → récupère la config d'un plugin
 * - plugin:set-config          → modifie la config d'un plugin
 * - plugin:request-permissions → demande les permissions des plugins sensibles
 * - plugin:confirm-permissions → confirme les permissions utilisateur
 */

import { ipcMain } from "electron";
import { z } from "zod";
import { PluginHost } from "../../plugins/PluginHost.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { logger } from "../../utils/logger.js";

// ── Schémas de validation Zod (SDD §21.3) ──────────────────────────────

/** Validation d'un pluginId (même format que le manifest) */
const pluginIdSchema = z.string().min(1, { message: "pluginId requis" });

/** Validation pour plugin:set-config */
const setConfigSchema = z.object({
  pluginId: pluginIdSchema,
  config: z.unknown(),
});

/** Validation pour plugin:confirm-permissions */
const confirmPermissionsSchema = z.object({
  approvedIds: z.array(pluginIdSchema, {
    message: "approvedIds doit être un tableau d'IDs",
  }),
  nonce: z.string().min(1, { message: "nonce requis" }),
});

// Ces instances seront injectées par le router
let pluginHost: PluginHost | null = null;
let settingsManager: SettingsManager | null = null;

export function setPluginHost(host: PluginHost): void {
  pluginHost = host;
}

export function setSettingsManager(sm: SettingsManager): void {
  settingsManager = sm;
}

type SensitivePluginInfo = Array<{
  id: string;
  name: string;
  permissions: string[];
  version: string;
}>;

let pendingPermissions: SensitivePluginInfo = [];

export function registerPluginHandlers(): void {
  ipcMain.handle("plugin:list", () => {
    if (!pluginHost) return [];
    return pluginHost.list().map((p) => ({
      id: p.manifest.id,
      name: p.manifest.name,
      version: p.manifest.version,
      author: p.manifest.author,
      description: p.manifest.description,
      type: p.manifest.type,
      permissions: p.manifest.permissions || [],
      status: p.status,
      errorMessage: p.errorMessage,
      configSchema: p.manifest.configSchema || undefined,
    }));
  });

  ipcMain.handle("plugin:enable", async (_event, pluginId: unknown) => {
    const id = pluginIdSchema.parse(pluginId);
    if (!pluginHost) throw new Error("PluginHost non initialisé");
    const plugin = pluginHost.get(id);
    if (!plugin) throw new Error(`Plugin inconnu : ${id}`);

    try {
      await pluginHost.activatePlugin(id);
      // Persister l'état
      if (settingsManager) {
        const settings = settingsManager.getAll();
        const enabled = [...new Set([...settings.enabledPlugins, id])];
        settingsManager.set("enabledPlugins", enabled);
      }
      return { success: true };
    } catch (err) {
      logger.error(`[IPC] Erreur activation plugin "${id}" :`, err);
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle("plugin:disable", async (_event, pluginId: unknown) => {
    const id = pluginIdSchema.parse(pluginId);
    if (!pluginHost) throw new Error("PluginHost non initialisé");
    try {
      await pluginHost.deactivatePlugin(id);
      // Persister l'état
      if (settingsManager) {
        const settings = settingsManager.getAll();
        const enabled = settings.enabledPlugins.filter((eid: string) => eid !== id);
        settingsManager.set("enabledPlugins", enabled);
      }
      return { success: true };
    } catch (err) {
      logger.error(`[IPC] Erreur désactivation plugin "${id}" :`, err);
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle("plugin:uninstall", async (_event, pluginId: unknown) => {
    const id = pluginIdSchema.parse(pluginId);
    if (!pluginHost) throw new Error("PluginHost non initialisé");
    try {
      await pluginHost.uninstallPlugin(id);
      if (settingsManager) {
        const settings = settingsManager.getAll();
        const enabled = settings.enabledPlugins.filter((eid: string) => eid !== id);
        settingsManager.set("enabledPlugins", enabled);
      }
      return { success: true };
    } catch (err) {
      logger.error(`[IPC] Erreur suppression plugin "${id}" :`, err);
      return { success: false, error: String(err) };
    }
  });

  // SDD §15.8 : installation manuelle uniquement en v1.0
  ipcMain.handle("plugin:install", async () => {
    return {
      success: false,
      error: "non supporté en v1.0",
    };
  });

  ipcMain.handle("plugin:get-config", async (_event, pluginId: unknown) => {
    const id = pluginIdSchema.parse(pluginId);
    if (!pluginHost) throw new Error("PluginHost non initialisé");
    try {
      const plugin = pluginHost.get(id);
      const config = pluginHost.getPluginConfig(id);
      return {
        success: true,
        config,
        configSchema: plugin?.manifest.configSchema || {},
      };
    } catch (err) {
      logger.error(`[IPC] Erreur get-config pour "${id}" :`, err);
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle("plugin:set-config", async (_event, pluginId: unknown, config: unknown) => {
    const parsed = setConfigSchema.parse({ pluginId, config });
    if (!pluginHost) throw new Error("PluginHost non initialisé");
    try {
      pluginHost.setPluginConfig(parsed.pluginId, parsed.config as Record<string, unknown>);
      return { success: true };
    } catch (err) {
      logger.error(`[IPC] Erreur set-config pour "${parsed.pluginId}" :`, err);
      return { success: false, error: String(err) };
    }
  });

  /**
   * Retourne la liste des plugins sensibles en attente de confirmation.
   * Inclut un nonce CSRF pour sécuriser la confirmation (Sécurité #5).
   */
  ipcMain.handle("plugin:request-permissions", () => {
    if (!pluginHost) return { plugins: [], nonce: "" };
    const sensitive = pluginHost.getPendingPermissionPlugins();
    const nonce = pluginHost.generatePermissionNonce();
    pendingPermissions = sensitive.map((p) => ({
      id: p.manifest.id,
      name: p.manifest.name,
      permissions: p.manifest.permissions || [],
      version: p.manifest.version,
    }));
    return { plugins: pendingPermissions, nonce };
  });

  /**
   * Reçoit la confirmation utilisateur et active les plugins approuvés.
   * Valide le nonce CSRF pour empêcher les confirmations non sollicitées.
   */
  ipcMain.handle("plugin:confirm-permissions", async (_event, payload: unknown) => {
    const parsed = confirmPermissionsSchema.parse(payload);
    if (!pluginHost) throw new Error("PluginHost non initialisé");

    // Valider le nonce CSRF
    if (!pluginHost.validatePermissionNonce(parsed.nonce)) {
      throw new Error("Nonce invalide ou expiré — veuillez redemander les permissions");
    }

    await pluginHost.activateApproved(parsed.approvedIds);
    pluginHost.clearPermissionNonce();
    pendingPermissions = [];
    return { success: true };
  });
}
