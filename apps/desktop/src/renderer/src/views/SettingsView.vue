<script setup lang="ts">
import { onMounted, onUnmounted, watch, ref } from "vue";
import { useSettingsStore } from "../stores/settings";
import { useOllamaStore } from "../stores/ollama";
import { useUpdateStore } from "../stores/update";

const settings = useSettingsStore();
const ollama = useOllamaStore();
const update = useUpdateStore();

const themeValue = ref<string>(
  settings.data.theme ?? "system",
);
const saved = ref(false);

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
  ] as const;
  for (const key of keys) {
    const value = settings.data[key];
    if (value !== undefined) {
      await settings.set(key, value as never);
    }
  }
  saved.value = true;
  setTimeout(() => { saved.value = false; }, 2000);
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
    if (
      (settings.data.theme ?? themeValue.value) === "system"
    ) {
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
  applyTheme(
    (settings.data.theme as "dark" | "light" | "system") ??
      "system",
  );
  setupSystemThemeListener();
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
      <button class="btn-primary" @click="saveSettings">
        Sauvegarder
      </button>
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
        {{
          ollama.available ? "Connecte" : "Non disponible"
        }}
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
        <input
          v-model="settings.data.ragEnabled"
          type="checkbox"
        />
        <span>Activer RAG (memoire contextuelle)</span>
      </label>
    </section>

    <section class="card">
      <h2>Mises a jour</h2>
      <label>
        Canal
        <select
          v-model="settings.data.updateChannel"
          @change="
            update.setChannel(
              settings.data.updateChannel ?? 'latest',
            )
          "
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
      <p v-if="update.error" class="error">
        Erreur : {{ update.error }}
      </p>
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
</style>
