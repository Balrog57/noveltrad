<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted } from "vue";

/** Niveau de log */
export type LogLevel = "debug" | "info" | "warn" | "error";

/** Entrée de log */
export interface LogEntry {
  /** Niveau de gravité */
  level: LogLevel;
  /** Message de log */
  message: string;
  /** Horodatage ISO ou lisible */
  timestamp?: string;
}

const props = withDefaults(
  defineProps<{
    /** Liste des entrées de log */
    entries: LogEntry[];
    /** Active le scroll automatique vers le bas sur ajout d'entrées */
    autoScroll?: boolean;
    /** Hauteur maximale du conteneur (CSS value, ex: "300px") */
    maxHeight?: string;
  }>(),
  { autoScroll: true, maxHeight: "300px" },
);

/** Référence du conteneur scrollable */
const scrollRef = ref<HTMLElement | null>(null);

/** Timer de debounce pour le scroll auto */
let scrollTimer: ReturnType<typeof setTimeout> | null = null;

/** Fait défiler vers le bas si autoScroll est activé */
function scrollToBottom(): void {
  if (!props.autoScroll || !scrollRef.value) return;
  scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
}

/** Surveille les changements d'entrées pour défiler */
watch(
  () => props.entries.length,
  () => {
    if (scrollTimer) clearTimeout(scrollTimer);
    scrollTimer = setTimeout(() => {
      nextTick(scrollToBottom);
    }, 0);
  },
);

onUnmounted(() => {
  if (scrollTimer) clearTimeout(scrollTimer);
});

/** Classe CSS selon le niveau */
function levelClass(level: LogLevel): string {
  return `nt-log-entry--${level}`;
}

/** Préfixe affiché selon le niveau */
function levelPrefix(level: LogLevel): string {
  switch (level) {
    case "debug":
      return "DEBUG";
    case "info":
      return "INFO";
    case "warn":
      return "WARN";
    case "error":
      return "ERROR";
  }
}
</script>

<template>
  <div
    ref="scrollRef"
    class="nt-log-viewer"
    :style="{ maxHeight }"
    role="log"
    aria-live="polite"
    aria-label="Journal des événements"
  >
    <div v-if="entries.length === 0" class="nt-log-empty">
      Aucun log à afficher.
    </div>
    <div
      v-for="(entry, idx) in entries"
      :key="idx"
      class="nt-log-entry"
      :class="levelClass(entry.level)"
    >
      <span v-if="entry.timestamp" class="nt-log-time">{{
        entry.timestamp
      }}</span>
      <span class="nt-log-level">{{ levelPrefix(entry.level) }}</span>
      <span class="nt-log-message">{{ entry.message }}</span>
    </div>
  </div>
</template>

<style scoped>
.nt-log-viewer {
  overflow-y: auto;
  background-color: var(--bg-primary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  padding: 8px;
  font-family: "Consolas", "Monaco", "Courier New", monospace;
  font-size: 13px;
  line-height: 1.5;
}

.nt-log-empty {
  color: var(--text-secondary);
  font-style: italic;
  padding: 8px 4px;
}

.nt-log-entry {
  display: flex;
  gap: 8px;
  padding: 2px 4px;
  border-radius: 3px;
  white-space: pre-wrap;
  word-break: break-word;
}

.nt-log-entry--debug {
  color: var(--text-secondary);
}

.nt-log-entry--info {
  color: var(--accent);
}

.nt-log-entry--warn {
  color: var(--warning);
}

.nt-log-entry--error {
  color: var(--error);
}

.nt-log-time {
  color: var(--text-secondary);
  flex-shrink: 0;
  opacity: 0.7;
}

.nt-log-level {
  flex-shrink: 0;
  font-weight: 700;
  min-width: 48px;
}

.nt-log-message {
  flex: 1;
  min-width: 0;
}
</style>
