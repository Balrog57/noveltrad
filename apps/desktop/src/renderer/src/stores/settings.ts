import { defineStore } from "pinia";
import { ref } from "vue";
import type { AppSettings } from "@shared/types/index.js";

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
  consistencyTolerances: {},
  enabledPlugins: [],
  activeProvider: "ollama",
  fallbackProvider: "",
  apiKey: "",
  uiLanguage: "fr",
  editorFontSize: 14,
  logLevel: "info",
  useWorkerThreads: true,
  autoUpdateCheck: true,
};

export const useSettingsStore = defineStore("settings", () => {
  const data = ref<Partial<AppSettings>>({});
  const loading = ref(false);

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
    data.value = await window.novelTradAPI.invoke("settings:set", key, value);
  }

  return { data, loading, load, set };
});
