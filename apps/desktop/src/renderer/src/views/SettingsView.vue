<script setup lang="ts">
import { onMounted, onUnmounted, watch, ref, computed, onBeforeMount } from "vue";
import { useSettingsStore } from "../stores/settings";
import { useOllamaStore } from "../stores/ollama";
import { useUpdateStore } from "../stores/update";
import { useRouter } from "vue-router";
import { toPlain } from "../utils/toPlain";
import type { ConsistencyTolerance } from "@shared/types/index.js";
import { SOURCE_LANGUAGES, TARGET_LANGUAGES } from "@shared/constants/languages.js";

const settings = useSettingsStore();
const ollama = useOllamaStore();
const update = useUpdateStore();
const router = useRouter();

const themeValue = ref<string>(settings.data.theme ?? "system");
const saved = ref(false);
const appVersion = ref("");

/** Options pour le select des modèles Ollama (depuis ollama.models détectés). */
const modelOptions = computed(() =>
  ollama.models.map((m) => ({
    value: m.name,
    label: m.parameterSize ? `${m.name} (${m.parameterSize})` : m.name,
  })),
);

/** Le modèle actuellement saisi n'est pas dans la liste détectée → l'ajouter. */
const defaultModelInList = computed(
  () => !settings.data.defaultModel || ollama.models.some((m) => m.name === settings.data.defaultModel),
);
const preTranslateModelInList = computed(
  () =>
    !settings.data.defaultPreTranslateModel ||
    ollama.models.some((m) => m.name === settings.data.defaultPreTranslateModel),
);

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
    "reviewLoopEnabled",
    "summarizerEnabled",
  ] as const;
  for (const key of keys) {
    const value = settings.data[key];
    if (value !== undefined) {
      await settings.set(key, value as never);
    }
  }
  // Sauvegarder les tolérances (tolerances.value est réactif → toPlain)
  await settings.set("consistencyTolerances", toPlain(tolerances.value) as never);
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

async function resetPreferences(): Promise<void> {
  if (confirm("Voulez-vous vraiment reinitialiser toutes les preferences ?")) {
    // Recharger les valeurs par defaut en reinitialisant le store
    await settings.set("ollamaHost", "http://localhost:11434");
    await settings.set("theme", "dark");
    await settings.set("updateChannel", "latest");
    await settings.set("ragEnabled", true);
    await settings.set("qualityThreshold", 70);
    await settings.set("activeProvider", "ollama");
    await settings.set("fallbackProvider", "");
    await settings.set("apiKey", "");
    await settings.set("uiLanguage", "fr");
    await settings.set("editorFontSize", 14);
    await settings.set("logLevel", "info");
    await settings.set("autoUpdateCheck", true);
    await settings.load();
    saved.value = true;
    setTimeout(() => {
      saved.value = false;
    }, 2000);
  }
}

async function restartWizard(): Promise<void> {
  await settings.set("firstRunCompleted", false);
  router.push("/wizard");
}

onBeforeMount(async () => {
  try {
    appVersion.value = await window.novelTradAPI.invoke<string>("app:get-version");
  } catch {
    appVersion.value = "inconnue";
  }
});

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
        <input v-model="settings.data.ollamaHost">
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
      <p v-if="!ollama.models.length" class="hint">
        Cliquez sur « Tester » pour détecter les modèles disponibles.
      </p>
      <label class="label-mt">
        Modèle par défaut
        <select v-if="ollama.models.length" v-model="settings.data.defaultModel">
          <option v-if="!defaultModelInList" :value="settings.data.defaultModel">
            {{ settings.data.defaultModel }} (non détecté)
          </option>
          <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <input v-else v-model="settings.data.defaultModel" placeholder="qwen3.5:9b">
      </label>
      <label class="label-mt">
        Modèle de pré-traduction
        <select v-if="ollama.models.length" v-model="settings.data.defaultPreTranslateModel">
          <option v-if="!preTranslateModelInList" :value="settings.data.defaultPreTranslateModel">
            {{ settings.data.defaultPreTranslateModel }} (non détecté)
          </option>
          <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <input v-else v-model="settings.data.defaultPreTranslateModel" placeholder="qwen3.5:4b">
      </label>
    </section>

    <section class="card">
      <h2>Langues par défaut</h2>
      <label>
        Source
        <select v-model="settings.data.sourceLanguage">
          <option v-for="lang in SOURCE_LANGUAGES" :key="lang.code" :value="lang.code">
            {{ lang.label }}
          </option>
        </select>
      </label>
      <label>
        Cible
        <select v-model="settings.data.targetLanguage">
          <option v-for="lang in TARGET_LANGUAGES" :key="lang.code" :value="lang.code">
            {{ lang.label }}
          </option>
        </select>
      </label>
    </section>

    <section class="card">
      <h2>Projets</h2>
      <label>
        Dossier par defaut
        <input
          v-model="settings.data.defaultProjectsPath"
          placeholder="~/NovelTrad Projects"
        >
      </label>
      <label class="form-checkbox">
        <input v-model="settings.data.ragEnabled" type="checkbox">
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
        >
      </label>
      <p class="hint">
        Le workflow met en pause si le score de qualite est inferieur a ce
        seuil.
      </p>

      <label class="form-checkbox">
        <input v-model="settings.data.reviewLoopEnabled" type="checkbox">
        <span>Boucle de révision pro (Review + Revise)</span>
      </label>
      <p class="hint">
        v1.4 — Ajoute deux passes de révision ciblée avant le QA : un agent
        Reviewer produit un rapport de corrections paragraphe-par-paragraphe,
        un agent Revise les applique. Rapproche d'une traduction révisée par
        un humain (inspiré de honya / LaTeXTrans).
      </p>

      <label class="form-checkbox">
        <input v-model="settings.data.summarizerEnabled" type="checkbox">
        <span>Summarizer (cohérence cross-chapitre)</span>
      </label>
      <p class="hint">
        v1.4 — Maintient un résumé incrémental du roman injecté dans le
        contexte des chapitres suivants. Garantit la cohérence des noms et de
        l'intrigue sur 500+ chapitres (inspiré de LaTeXTrans / TransAgents).
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
          >
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
          >
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
          >
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
          >
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
        >
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
        >
        <span>Ignorer les differences de ponctuation</span>
      </label>
    </section>

    <!-- SDD §4.11.1 : Section IA -->
    <section class="card">
      <h2>IA</h2>
      <p class="section-desc">
        Configuration du fournisseur d'intelligence artificielle.
      </p>

      <label>
        Provider actif
        <select v-model="settings.data.activeProvider">
          <option value="ollama">Ollama (local)</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="gemini">Gemini</option>
          <option value="openrouter">OpenRouter</option>
          <option value="lmstudio">LM Studio</option>
        </select>
      </label>

      <label>
        Provider de fallback
        <select v-model="settings.data.fallbackProvider">
          <option value="">Aucun</option>
          <option value="ollama">Ollama (local)</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="gemini">Gemini</option>
          <option value="openrouter">OpenRouter</option>
          <option value="lmstudio">LM Studio</option>
        </select>
      </label>

      <div v-if="settings.data.activeProvider && settings.data.activeProvider !== 'ollama' && settings.data.activeProvider !== 'lmstudio'">
        <label>
          Cle API
          <input
            v-model="settings.data.apiKey"
            type="password"
            placeholder="sk-..."
          >
        </label>
      </div>
    </section>

    <!-- SDD §4.11.4 : Section Interface -->
    <section class="card">
      <h2>Interface</h2>

      <label>
        Langue de l'interface
        <select v-model="settings.data.uiLanguage">
          <option value="fr">Francais</option>
          <option value="en">English</option>
        </select>
      </label>

      <label>
        Taille de police (editeur)
        <select v-model.number="settings.data.editorFontSize">
          <option :value="12">12</option>
          <option :value="14">14</option>
          <option :value="16">16</option>
          <option :value="18">18</option>
          <option :value="20">20</option>
        </select>
      </label>
    </section>

    <!-- SDD §4.11.5 : Section Avance -->
    <section class="card">
      <h2>Avance</h2>

      <label>
        Niveau de log
        <select v-model="settings.data.logLevel">
          <option value="debug">Debug</option>
          <option value="info">Info</option>
          <option value="warn">Warning</option>
          <option value="error">Error</option>
        </select>
      </label>

      <button class="btn-danger" style="margin-top: 12px;" @click="resetPreferences">
        Reinitialiser les preferences
      </button>

      <button class="btn-danger" style="margin-top: 8px;" @click="restartWizard">
        Relancer le wizard de premier demarrage
      </button>
    </section>

    <section class="card">
      <h2>Mises a jour</h2>
      <p class="section-desc">
        Version actuelle : <strong>{{ appVersion }}</strong>
      </p>

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

      <label class="form-checkbox">
        <input
          v-model="settings.data.autoUpdateCheck"
          type="checkbox"
          @change="settings.set('autoUpdateCheck', settings.data.autoUpdateCheck ?? true)"
        >
        <span>Verification automatique</span>
      </label>

      <p v-if="update.info?.version && update.info.version !== appVersion" class="hint">
        Derniere version connue : {{ update.info.version }}
      </p>

      <button class="btn-primary" :disabled="update.checking" @click="update.check">
        {{ update.checking ? "Vérification..." : "Vérifier maintenant" }}
      </button>
      <p v-if="update.checking" class="hint">
        Recherche de mises à jour en cours…
      </p>
      <p v-if="update.notAvailable" class="ok">
        ✅ NovelTrad est à jour (version {{ appVersion }}).
      </p>
      <p v-if="update.available" class="ok">
        🔄 Nouvelle version disponible : {{ update.info?.version }}
      </p>
      <button
        v-if="update.available && !update.downloaded"
        class="btn-primary"
        :disabled="update.progress != null"
        @click="update.download"
      >
        {{ update.progress ? `Téléchargement ${Math.round(update.progress.percent)}%` : "Télécharger" }}
      </button>
      <button
        v-if="update.downloaded"
        class="btn-primary"
        @click="update.install"
      >
        Installer et redémarrer
      </button>
      <p v-if="update.error" class="error">⚠️ Erreur : {{ update.error }}</p>
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

.btn-danger {
  background-color: var(--error, #e74c3c);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: var(--border-radius);
  cursor: pointer;
  display: block;
  width: 100%;
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
