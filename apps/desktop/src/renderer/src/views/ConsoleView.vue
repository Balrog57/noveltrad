<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from "vue";
import { useLogsStore, type LogLevel } from "../stores/logs";

const logsStore = useLogsStore();
const logsContainer = ref<HTMLElement | null>(null);
const toastMessage = ref("");
const showToast = ref(false);

const levels: Array<{ value: LogLevel | "all"; label: string }> = [
  { value: "all", label: "Tous" },
  { value: "debug", label: "Debug" },
  { value: "info", label: "Info" },
  { value: "warn", label: "Avertissement" },
  { value: "error", label: "Erreur" },
];

/** Nombre de logs par niveau */
const counts = computed(() => {
  const c = { debug: 0, info: 0, warn: 0, error: 0 };
  for (const e of logsStore.entries) {
    c[e.level]++;
  }
  return c;
});

/** Auto-scroll en bas quand de nouveaux logs arrivent */
watch(
  () => logsStore.filtered.length,
  async () => {
    await nextTick();
    if (logsContainer.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight;
    }
  },
);

/** Formater le timestamp */
function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/** Classe CSS pour le niveau */
function levelClass(level: LogLevel): string {
  return `log-${level}`;
}

/** Copier les logs filtr\u00E9s dans le presse-papiers */
async function exportLogs(): Promise<void> {
  const text = logsStore.filtered
    .map(
      (e) =>
        `[${formatTime(e.timestamp)}] [${e.level.toUpperCase()}] ${e.message}${e.source ? ` (${e.source})` : ""}`,
    )
    .join("\n");

  try {
    await navigator.clipboard.writeText(text);
    toastMessage.value = `${logsStore.filtered.length} logs copi\u00E9s dans le presse-papiers`;
    showToast.value = true;
    setTimeout(() => {
      showToast.value = false;
    }, 3000);
  } catch {
    toastMessage.value = "Erreur lors de la copie";
    showToast.value = true;
    setTimeout(() => {
      showToast.value = false;
    }, 3000);
  }
}
</script>

<template>
  <div class="console-view">
    <header class="console-header">
      <h1>Console</h1>
      <p class="console-subtitle">
        Journal en temps r\u00E9el de l'application
      </p>
    </header>

    <!-- Toolbar -->
    <div class="console-toolbar">
      <div class="filter-group">
        <button
          v-for="lvl in levels"
          :key="lvl.value"
          class="filter-btn"
          :class="{
            'filter-btn--active': logsStore.filter === lvl.value,
          }"
          @click="logsStore.filter = lvl.value"
        >
          {{ lvl.label }}
          <span v-if="lvl.value !== 'all'" class="filter-count">
            {{ counts[lvl.value as LogLevel] }}
          </span>
        </button>
      </div>

      <div class="toolbar-actions">
        <input
          v-model="logsStore.search"
          class="search-input"
          type="text"
          placeholder="Rechercher..."
          aria-label="Rechercher dans les logs"
        />
        <button
          class="btn-secondary"
          aria-label="Effacer les logs"
          @click="logsStore.clear()"
        >
          Effacer
        </button>
        <button
          class="btn-secondary"
          aria-label="Exporter les logs"
          @click="exportLogs"
        >
          Copier
        </button>
      </div>
    </div>

    <!-- Conteneur de logs -->
    <div ref="logsContainer" class="logs-container">
      <div v-if="logsStore.filtered.length === 0" class="logs-empty">
        Aucun log disponible.
      </div>
      <div
        v-for="entry in logsStore.filtered"
        :key="entry.id"
        class="log-entry"
        :class="levelClass(entry.level)"
      >
        <span class="log-time">{{ formatTime(entry.timestamp) }}</span>
        <span class="log-level">{{ entry.level.toUpperCase() }}</span>
        <span class="log-message">{{ entry.message }}</span>
        <span v-if="entry.source" class="log-source">
          ({{ entry.source }})
        </span>
      </div>
    </div>

    <!-- Toast -->
    <Transition name="toast-slide">
      <div v-if="showToast" class="toast">
        {{ toastMessage }}
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.console-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.console-header {
  margin-bottom: 16px;
}

.console-header h1 {
  margin: 0;
  font-size: 24px;
  color: var(--text-primary);
}

.console-subtitle {
  margin: 4px 0 0;
  font-size: 14px;
  color: var(--text-secondary);
}

/* Toolbar */
.console-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  gap: 4px;
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--border-radius);
  border: 1px solid var(--bg-tertiary);
  background-color: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition:
    background-color 0.15s,
    color 0.15s;
}

.filter-btn:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.filter-btn--active {
  background-color: var(--accent);
  color: #0f172a;
  border-color: var(--accent);
}

.filter-btn--active:hover {
  background-color: var(--accent-hover);
}

.filter-count {
  font-size: 11px;
  opacity: 0.8;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-input {
  padding: 6px 12px;
  border-radius: var(--border-radius);
  border: 1px solid var(--bg-tertiary);
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 13px;
  width: 200px;
  outline: none;
}

.search-input::placeholder {
  color: var(--text-secondary);
}

.search-input:focus {
  border-color: var(--accent);
}

.btn-secondary {
  padding: 6px 12px;
  border-radius: var(--border-radius);
  border: 1px solid var(--bg-tertiary);
  background-color: transparent;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.15s;
  white-space: nowrap;
}

.btn-secondary:hover {
  background-color: var(--bg-tertiary);
}

/* Conteneur de logs */
.logs-container {
  flex: 1;
  overflow-y: auto;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 12px;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
}

.logs-empty {
  color: var(--text-secondary);
  font-style: italic;
  padding: 40px;
  text-align: center;
}

.log-entry {
  display: flex;
  gap: 8px;
  padding: 2px 0;
  border-bottom: 1px solid var(--bg-tertiary);
}

.log-entry:last-child {
  border-bottom: none;
}

.log-time {
  color: var(--text-secondary);
  flex-shrink: 0;
  min-width: 70px;
}

.log-level {
  font-weight: 600;
  flex-shrink: 0;
  min-width: 60px;
}

.log-message {
  color: var(--text-primary);
  flex: 1;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-source {
  color: var(--text-secondary);
  flex-shrink: 0;
}

/* Couleurs par niveau */
.log-debug .log-level {
  color: var(--text-secondary);
}

.log-debug .log-message {
  color: var(--text-secondary);
}

.log-info .log-level {
  color: var(--accent);
}

.log-info .log-message {
  color: var(--text-primary);
}

.log-warn .log-level {
  color: var(--warning);
}

.log-warn .log-message {
  color: var(--warning);
}

.log-error .log-level {
  color: var(--error);
}

.log-error .log-message {
  color: var(--error);
}

/* Toast */
.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  padding: 10px 20px;
  border-radius: var(--border-radius);
  font-size: 13px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  z-index: 2000;
}

.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: all 0.3s ease;
}

.toast-slide-enter-from,
.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
</style>
