import { defineStore } from "pinia";
import { ref } from "vue";
import type { AppSettings } from "@shared/types/index.js";
import { toPlain } from "../utils/toPlain";

/** Valeurs par défaut utilisées si le handler settings échoue à charger */
const DEFAULT_SETTINGS: AppSettings = {
  firstRunCompleted: false,
  ollamaHost: "http://localhost:11434",
  defaultModel: "qwen3.5:9b",
  defaultPreTranslateModel: "qwen3.5:4b",
  sourceLanguage: "zh",
  targetLanguage: "fr",
  defaultProjectsPath: "~/NovelTrad Projects",
  theme: "dark",
  recentProjects: [],
  updateChannel: "latest",
  ragEnabled: true,
  maxConcurrentJobs: 1,
  qualityThreshold: 70,
  stepTimeoutMs: 120000,
  consistencyTolerances: {},
  modelCosts: {},
  enabledPlugins: [],
  activeProvider: "ollama",
  fallbackProvider: "",
  apiKey: "",
  uiLanguage: "fr",
  editorFontSize: 14,
  logLevel: "info",
  useWorkerThreads: true,
  reviewLoopEnabled: true,
  summarizerEnabled: true,
  autoUpdateCheck: true,
};

export const useSettingsStore = defineStore("settings", () => {
  const data = ref<Partial<AppSettings>>({});
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function load() {
    loading.value = true;
    try {
      const result = await window.novelTradAPI.invoke<Partial<AppSettings>>("settings:get");
      console.log("[Settings] IPC result:", result);
      data.value = result && Object.keys(result).length > 0 ? result : { ...DEFAULT_SETTINGS };
    } catch (e) {
      console.error("[Settings] IPC failed, using defaults:", e);
      data.value = { ...DEFAULT_SETTINGS };
    } finally {
      loading.value = false;
    }
  }

  async function set<K extends keyof AppSettings>(
    key: K,
    value: AppSettings[K],
  ) {
    try {
      // Bug fix : ne PAS écraser tout data.value avec le retour IPC.
      // Avant, settings:set retournait l'objet complet re-lu du disque
      // (getAll()), ce qui écrasait les modifications en mémoire pas encore
      // sauvées pendant la boucle saveSettings() (ex: defaultModel perdu
      // après la sauvegarde de ollamaHost). On merge uniquement la clé écrite.
      await window.novelTradAPI.invoke("settings:set", key, toPlain(value));
      data.value = { ...data.value, [key]: toPlain(value) };
    } catch (err) {
      error.value = err instanceof Error ? err.message : `Erreur lors de la sauvegarde de ${key}`;
    }
  }

  return { data, loading, error, load, set };
});
