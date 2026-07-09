import { ipcMain } from "electron";
import { z } from "zod";
import type { UpdateManager } from "../../managers/UpdateManager.js";
import { SettingsManager } from "../../managers/SettingsManager.js";

// ── Schémas de validation Zod (SDD §16.3) ──────────────────────────────

const channelSchema = z.enum(["latest", "beta", "alpha"], {
  message: "Canal invalide. Valeurs acceptées : latest, beta, alpha",
});

const settings = new SettingsManager();

/**
 * Instance partagée d'UpdateManager, injectée depuis index.ts via setUpdateManager().
 * On évite ainsi une double instantiation qui doublonnait chaque event autoUpdater
 * (update-available, update-downloaded, etc.) et ouvrait des dialogues en double.
 */
let updateManager: UpdateManager | null = null;

/** Injecte l'instance unique d'UpdateManager créée dans index.ts. */
export function setUpdateManager(manager: UpdateManager): void {
  updateManager = manager;
}

export function registerUpdateHandlers(): void {
  ipcMain.handle("update:check", async () => {
    if (!updateManager) {return { ok: false, error: "UpdateManager not initialized" };}
    await updateManager.check();
    return { ok: true };
  });

  ipcMain.handle("update:download", async () => {
    if (!updateManager) {return { ok: false, error: "UpdateManager not initialized" };}
    await updateManager.download();
    return { ok: true };
  });

  ipcMain.handle("update:install", async () => {
    if (!updateManager) {return { ok: false, error: "UpdateManager not initialized" };}
    updateManager.install();
    return { ok: true };
  });

  ipcMain.handle("update:set-channel", async (_event, channel: unknown) => {
    if (!updateManager) {return { ok: false, error: "UpdateManager not initialized" };}
    const parsed = channelSchema.parse(channel);
    updateManager.setChannel(parsed);
    settings.set("updateChannel", parsed);
    return { ok: true };
  });
}
