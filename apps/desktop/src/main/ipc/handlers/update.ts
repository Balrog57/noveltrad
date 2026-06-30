import { ipcMain } from "electron";
import { UpdateManager } from "../../managers/UpdateManager.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { BrowserWindow } from "electron";

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

  ipcMain.handle("update:set-channel", async (_event, channel: string) => {
    if (!["latest", "beta", "alpha"].includes(channel))
      throw new Error("Canal invalide");

    updateManager.setChannel(channel);
    settings.set("updateChannel", channel as "latest" | "beta" | "alpha");
    return { ok: true };
  });
}
