import path from "node:path";
import os from "node:os";
import fs from "node:fs";
import type { z } from "zod";
import { appSettingsSchema } from "@shared/schemas/index.js";

export type AppSettings = z.infer<typeof appSettingsSchema>;

export class SettingsManager {
  // Le '!' est justifié : quand le constructeur retourne l'instance singleton
  // existante (return anticipé), this.configPath n'est pas réassigné mais
  // l'objet retourné l'a déjà été lors de sa création initiale.
  private readonly configPath!: string;

  constructor() {
    // P1-4 fix : singleton transparent. Avant, chaque handler IPC faisait
    // `new SettingsManager()` (12+ instances) qui relisaient config.json à
    // chaque get/set. Désormais le constructeur retourne toujours la même
    // instance process-wide. Les mocks de tests remplacent ce constructeur
    // via vi.mock et ne sont pas affectés (ils instancient leur propre faux).
    if (_settingsSingleton) {
      return _settingsSingleton;
    }
    const appData = process.env.APPDATA || path.join(os.homedir(), ".config");
    const configDir = path.join(appData, "NovelTrad");
    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
    }
    this.configPath = path.join(configDir, "config.json");
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    _settingsSingleton = this;
  }

  getAll(): AppSettings {
    if (!fs.existsSync(this.configPath)) {
      return appSettingsSchema.parse({});
    }
    const raw = fs.readFileSync(this.configPath, "utf-8");
    return appSettingsSchema.parse(JSON.parse(raw));
  }

  get<K extends keyof AppSettings>(key: K): AppSettings[K] {
    return this.getAll()[key];
  }

  set<K extends keyof AppSettings>(key: K, value: AppSettings[K]): void {
    const current = this.getAll();
    const next = { ...current, [key]: value };
    appSettingsSchema.parse(next);
    fs.writeFileSync(this.configPath, JSON.stringify(next, null, 2), "utf-8");
  }
}

/**
 * Singleton process-wide du SettingsManager (Workstream D / P1-4 fix).
 * Le constructeur `new SettingsManager()` retourne aussi cette instance
 * (singleton transparent — cf. commentaire dans le constructeur).
 */
let _settingsSingleton: SettingsManager | null = null;

export function getSettingsManager(): SettingsManager {
  if (!_settingsSingleton) {
    _settingsSingleton = new SettingsManager();
  }
  return _settingsSingleton;
}

/**
 * Force une instance spécifique (tests / injection). Remet le singleton à
 * null si on passe `null` (utile pour isoler les tests).
 */
export function setSettingsManagerInstance(sm: SettingsManager | null): void {
  _settingsSingleton = sm;
}
