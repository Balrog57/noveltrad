import { defineStore } from "pinia";
import { ref, computed } from "vue";

export type LogLevel = "debug" | "info" | "warn" | "error";

export interface LogEntry {
  id: string;
  level: LogLevel;
  message: string;
  source?: string;
  timestamp: number;
}

export const useLogsStore = defineStore("logs", () => {
  const entries = ref<LogEntry[]>([]);
  const filter = ref<LogLevel | "all">("all");
  const search = ref("");

  let nextId = 0;

  /** Ajoute une entrée de log */
  function addEntry(
    entry: Omit<LogEntry, "id" | "timestamp"> & { timestamp?: number },
  ): void {
    entries.value.push({
      id: String(nextId++),
      timestamp: entry.timestamp ?? Date.now(),
      level: entry.level,
      message: entry.message,
      source: entry.source,
    });
  }

  /** Vide tous les logs */
  function clear(): void {
    entries.value = [];
  }

  /** Logs filtrés par niveau et recherche textuelle */
  const filtered = computed(() => {
    let result = entries.value;

    if (filter.value !== "all") {
      result = result.filter((e) => e.level === filter.value);
    }

    const q = search.value.trim().toLowerCase();
    if (q) {
      result = result.filter(
        (e) =>
          e.message.toLowerCase().includes(q) ||
          (e.source && e.source.toLowerCase().includes(q)),
      );
    }

    return result;
  });

  // Écouter les événements 'log' du main process
  window.novelTradAPI.on("log", (payload: unknown) => {
    const p = payload as {
      level: LogLevel;
      message: string;
      source?: string;
    };
    addEntry(p);
  });

  return {
    entries,
    filter,
    search,
    addEntry,
    clear,
    filtered,
  };
});
