<script setup lang="ts">
import { onMounted, onUnmounted, watch, ref, computed } from "vue";
import { useSettingsStore } from "../stores/settings";
import { useOllamaStore } from "../stores/ollama";
import { useUpdateStore } from "../stores/update";
import type { ConsistencyTolerance } from "@shared/types/index.js";

const settings = useSettingsStore();
const ollama = useOllamaStore();
const update = useUpdateStore();

const themeValue = ref<string>(settings.data.theme ?? "system");
const saved = ref(false);

// SDD §11.4 : paires de langues prédéfinies pour les tolérances
const LANGUAGE_PAIRS = [
  { key: "zh-fr", label: "Chinois → Français" },
  { key: "ja-fr", label: "Japonais → Français" },
  { key: "ko-fr", label: "Coréen → Français" },
  { key: "en-fr", label: "Anglais → Français" },
  { key: "zh-en", label: "Chinois → Anglais" },
  { key: "ja-en", label: "Japonais → Anglais" },
];

// Tolérances par défaut (SDD §11.4)
const DEFAULT_TOLERANCE: ConsistencyTolerance = {
  sentenceRatioMin: 0.7,
  sentenceRatioMax: 1.5,
  lengthRatioMin: 0.6,
  lengthRatioMax: 1.8,
  ignoreNumbersInDialogues: false,
  ignorePunctuationMismatch: false,
};

// Paire de langues sélectionnée pour l'édition des tolérances
const selectedPair = ref<string>("zh-fr");

// Tolérances éditables (copie locale)
const tolerances = ref<Record<string, ConsistencyTolerance>>({});

// Initialise les tolérances depuis les settings
function initTolerances(): void {
  const stored = settings.data.consistencyTolerances ?? {};
  const result: Record<string, ConsistencyTolerance> = {};
  for (const pair of LANGUAGE_PAIRS) {
    result[pair.key] = stored[pair.key]
      ? { ...stored[pair.key] }
      : { ...DEFAULT_TOLERANCE };
  }
  tolerances.value = result;
}

// Tolérance de la paire actuellement sélectionnée
const currentTolerance = computed({
  get: () => tolerances.value[selectedPair.value] ?? { ...DEFAULT_TOLERANCE },
  set: (val: ConsistencyTolerance) => {
    tolerances.value = { ...tolerances.value, [selectedPair.value]: val };
  },
});

function updateTolerance(
  field: keyof ConsistencyTolerance,
  value: number | boolean,
): void {
  const current = tolerances.value[selectedPair.value] ?? {
    ...DEFAULT_TOLERANCE,
  };
  tolerances.value = {
    ...tolerances.value,
    [selectedPair.value]: { ...current, [field]: value },
  };
}

async function saveSettings(): Promise<void> {
  saved.value = false;
  const keys = [
    "ollamaHost",
    "defaultModel",
    "defaultPreTranslateModel",
    "sourceLanguage",
    "targetLanguage",
    "defaultProjectsPath",
    "updateChannel",
    "ragEnabled",
    "qualityThreshold",
  ] as const;
  for (const key of keys) {
    const value = settings.data[key];
    if (value !== undefined) {
      await settings.set(key, value as never);
    }
  }
  // Sauvegarder les tolérances
  await settings.set("consistencyTolerances", tolerances.value as never);
  saved.value = true;
  setTimeout(() => {
    saved.value = false;
  }, 2000);
}

// SDD §4.14 — Appliquer le thème sur l'élément <html>
function applyTheme(theme: "dark" | "light" | "system"): void {
  const root = document.documentElement;
  if (theme === "light") {
    root.classList.add("theme-light");
  } else if (theme === "dark") {
    root.classList.remove("theme-light");
  } else {
    // system : détecter la préférence OS
    const prefersDark = window.matchMedia(
      "(prefers-color-scheme: dark)",
    ).matches;
    if (prefersDark) {
      root.classList.remove("theme-light");
    } else {
      root.classList.add("theme-light");
    }
  }
}

// Media query listener pour le mode système
let mediaQuery: MediaQueryList | null = null;

function setupSystemThemeListener(): void {
  mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  const handler = () => {
    if ((settings.data.theme ?? themeValue.value) === "system") {
      applyTheme("system");
    }
  };
  mediaQuery.addEventListener("change", handler);
}

async function onThemeChange(value: string): Promise<void> {
  const theme = value as "dark" | "light" | "system";
  themeValue.value = theme;
  applyTheme(theme);
  await settings.set("theme", theme);
}

watch(
  () => settings.data.theme,
  (newTheme) => {
    if (newTheme) {
      themeValue.value = newTheme;
      applyTheme(newTheme);
    }
  },
);

onMounted(() => {
  applyTheme((settings.data.theme as "dark" | "light" | "system") ?? "system");
  setupSystemThemeListener();
  initTolerances();
});

onUnmounted(() => {
  if (mediaQuery) {
    mediaQuery.removeEventListener("change", () => {});
  }
});
</script>

<template>
  <div class="settings">
    <h1>Parametres</h1>

    <div class="save-bar">
      <button class="btn-primary" @click="saveSettings">Sauvegarder</button>
      <span v-if="saved" class="saved-msg">Parametres enregistres.</span>
    </div>

    <section class="card">
      <h2>Theme</h2>
      <label>
        Apparence
        <select
          :value="themeValue"
          @change="onThemeChange(($event.target as HTMLSelectElement).value)"
        >
          <option value="system">Systeme (auto)</option>
          <option value="dark">Sombre</option>
          <option value="light">Clair</option>
        </select>
      </label>
    </section>

    <section class="card">
      <h2>Ollama</h2>
      <label>
        Hote Ollama
        <input v-model="settings.data.ollamaHost" />
      </label>
      <button
        class="btn-primary"
        @click="ollama.check(settings.data.ollamaHost)"
      >
        Tester
      </button>
      <p :class="{ ok: ollama.available }">
        {{ ollama.available ? "Connecte" : "Non disponible" }}
      </p>
      <ul v-if="ollama.models.length">
        <li v-for="m in ollama.models" :key="m.name">
          {{ m.name }}
        </li>
      </ul>
      <label class="label-mt">
        Modele par defaut
        <input v-model="settings.data.defaultModel" placeholder="qwen3.5:9b" />
      </label>
      <label class="label-mt">
        Modele de pre-traduction
        <input
          v-model="settings.data.defaultPreTranslateModel"
          placeholder="qwen3.5:4b"
        />
      </label>
    </section>

    <section class="card">
      <h2>Langues par defaut</h2>
      <label>
        Source
        <input v-model="settings.data.sourceLanguage" />
      </label>
      <label>
        Cible
        <input v-model="settings.data.targetLanguage" />
      </label>
    </section>

    <section class="card">
      <h2>Projets</h2>
      <label>
        Dossier par defaut
        <input
          v-model="settings.data.defaultProjectsPath"
          placeholder="~/NovelTrad Projects"
        />
      </label>
      <label class="form-checkbox">
        <input v-model="settings.data.ragEnabled" type="checkbox" />
        <span>Activer RAG (memoire contextuelle)</span>
      </label>
    </section>

    <section class="card">
      <h2>Workflow</h2>
      <p class="section-desc">
        Seuils de qualite et tolerances de coherence configurables.
      </p>

      <label>
        Seuil de qualite minimum (0-100)
        <input
          v-model.number="settings.data.qualityThreshold"
          type="number"
          min="0"
          max="100"
          placeholder="70"
        />
      </label>
      <p class="hint">
        Le workflow met en pause si le score de qualite est inferieur a ce
        seuil.
      </p>

      <h3 class="subsection">Tolerances de coherence par paire de langues</h3>
      <p class="hint">
        Ajustez les ratios acceptes pour chaque paire source-cible. Les langues
        asiatiques (zh, ja, ko) ont des ratios plus eloignes de 1.
      </p>

      <label>
        Paire de langues
        <select v-model="selectedPair">
          <option
            v-for="pair in LANGUAGE_PAIRS"
            :key="pair.key"
            :value="pair.key"
          >
            {{ pair.label }}
          </option>
        </select>
      </label>

      <div class="tolerance-grid">
        <label>
          Ratio phrases min
          <input
            :value="currentTolerance.sentenceRatioMin"
            type="number"
            step="0.1"
            min="0"
            max="5"
            @input="
              updateTolerance(
                'sentenceRatioMin',
                parseFloat(($event.target as HTMLInputElement).value),
              )
            "
          />
        </label>
        <label>
          Ratio phrases max
          <input
            :value="currentTolerance.sentenceRatioMax"
            type="number"
            step="0.1"
            min="0"
            max="10"
            @input="
              updateTolerance(
                'sentenceRatioMax',
                parseFloat(($event.target as HTMLInputElement).value),
              )
            "
          />
        </label>
        <label>
          Ratio longueur min
          <input
            :value="currentTolerance.lengthRatioMin"
            type="number"
            step="0.1"
            min="0"
            max="5"
            @input="
              updateTolerance(
                'lengthRatioMin',
                parseFloat(($event.target as HTMLInputElement).value),
              )
            "
          />
        </label>
        <label>
          Ratio longueur max
          <input
            :value="currentTolerance.lengthRatioMax"
            type="number"
            step="0.1"
            min="0"
            max="10"
            @input="
              updateTolerance(
                'lengthRatioMax',
                parseFloat(($event.target as HTMLInputElement).value),
              )
            "
          />
        </label>
      </div>

      <label class="form-checkbox">
        <input
          :checked="currentTolerance.ignoreNumbersInDialogues"
          type="checkbox"
          @change="
            updateTolerance(
              'ignoreNumbersInDialogues',
              ($event.target as HTMLInputElement).checked,
            )
          "
        />
        <span>Ignorer les nombres dans les dialogues</span>
      </label>
      <label class="form-checkbox">
        <input
          :checked="currentTolerance.ignorePunctuationMismatch"
          type="checkbox"
          @change="
            updateTolerance(
              'ignorePunctuationMismatch',
              ($event.target as HTMLInputElement).checked,
            )
          "
        />
        <span>Ignorer les differences de ponctuation</span>
      </label>
    </section>

    <section class="card">
      <h2>Mises a jour</h2>
      <label>
        Canal
        <select
          v-model="settings.data.updateChannel"
          @change="update.setChannel(settings.data.updateChannel ?? 'latest')"
        >
          <option value="latest">Stable</option>
          <option value="beta">Beta</option>
          <option value="alpha">Alpha</option>
        </select>
      </label>
      <button class="btn-primary" @click="update.check">
        Verifier maintenant
      </button>
      <p v-if="update.available" class="ok">
        Nouvelle version disponible :
        {{ update.info?.version }}
      </p>
      <button
        v-if="update.available && !update.downloaded"
        class="btn-primary"
        @click="update.download"
      >
        Telecharger
      </button>
      <button
        v-if="update.downloaded"
        class="btn-primary"
        @click="update.install"
      >
        Installer et redemarrer
      </button>
      <p v-if="update.error" class="error">Erreur : {{ update.error }}</p>
    </section>
  </div>
</template>

<style scoped>
.settings {
  max-width: 600px;
}

.save-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.saved-msg {
  color: var(--success);
  font-size: 13px;
}

.card {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 20px;
  margin-bottom: 20px;
}

.card h2 {
  margin-top: 0;
  font-size: 16px;
}

label {
  display: block;
  margin-bottom: 12px;
}

input,
select {
  width: 100%;
  margin-top: 4px;
  padding: 8px 12px;
  border-radius: var(--border-radius);
  border: 1px solid var(--bg-tertiary);
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.label-mt {
  margin-top: 12px;
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.form-checkbox input[type="checkbox"] {
  width: auto;
  accent-color: var(--accent);
}

.form-checkbox span {
  color: var(--text-primary);
}

.btn-primary {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: var(--border-radius);
  margin-right: 8px;
}

.ok {
  color: var(--success);
}

.error {
  color: var(--error);
}

.section-desc {
  color: var(--text-secondary);
  font-size: 13px;
  margin-top: 0;
  margin-bottom: 16px;
}

.subsection {
  font-size: 14px;
  margin-top: 20px;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.hint {
  color: var(--text-secondary);
  font-size: 12px;
  margin-top: -4px;
  margin-bottom: 12px;
}

.tolerance-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.tolerance-grid label {
  margin-bottom: 0;
}
</style>
