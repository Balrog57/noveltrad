import { ipcMain, app } from "electron";
import { z } from "zod";
import { SettingsManager } from "../../managers/SettingsManager.js";

// ── Schémas de validation Zod (SDD §16.3) ──────────────────────────────

const settingsKeySchema = z.string().min(1, { message: "settings key requise" });

const settings = new SettingsManager();

export function registerSettingsHandlers(): void {
  ipcMain.handle("settings:get", async (_event, key?: unknown) => {
    const parsed = z
      .object({ key: settingsKeySchema.optional() })
      .parse({ key });
    if (parsed.key)
      return settings.get(parsed.key as keyof ReturnType<typeof settings.getAll>);
    return settings.getAll();
  });

  ipcMain.handle("settings:set", async (_event, key: unknown, value: unknown) => {
    const parsed = z
      .object({ key: settingsKeySchema, value: z.unknown() })
      .parse({ key, value });
    settings.set(
      parsed.key as keyof ReturnType<typeof settings.getAll>,
      parsed.value as never,
    );
    return settings.getAll();
  });

  ipcMain.handle("app:get-version", async () => {
    return app.getVersion();
  });
}
