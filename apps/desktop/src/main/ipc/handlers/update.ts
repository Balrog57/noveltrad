import { ipcMain } from "electron";
import { z } from "zod";
import { UpdateManager } from "../../managers/UpdateManager.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { BrowserWindow } from "electron";

// ── Schémas de validation Zod (SDD §16.3) ──────────────────────────────

const channelSchema = z.enum(["latest", "beta", "alpha"], {
  message: "Canal invalide. Valeurs acceptées : latest, beta, alpha",
});

const settings = new SettingsManager();

function getMainWindow(): BrowserWindow | null {
  const wins = BrowserWindow.getAllWindows();
  return wins[0] ?? null;
}

const updateManager = new UpdateManager("latest", getMainWindow);

export function registerUpdateHandlers(): void {
  ipcMain.handle("update:check", async () => {
    await updateManager.check();
    return { ok: true };
  });

  ipcMain.handle("update:download", async () => {
    await updateManager.download();
    return { ok: true };
  });

  ipcMain.handle("update:install", async () => {
    updateManager.install();
    return { ok: true };
  });

  ipcMain.handle("update:set-channel", async (_event, channel: unknown) => {
    const parsed = channelSchema.parse(channel);
    updateManager.setChannel(parsed);
    settings.set("updateChannel", parsed);
    return { ok: true };
  });
}
