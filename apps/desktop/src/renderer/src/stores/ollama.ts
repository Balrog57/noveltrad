import { defineStore } from "pinia";
import { ref } from "vue";
import type { OllamaModelInfo } from "@shared/types/index.js";

/**
 * Structure retournée par le handler IPC `ollama:is-available`.
 * `error`/`errorKind` ne sont présents qu'en cas d'échec, pour permettre
 * à l'UI d'afficher la cause réelle (ex: ECONNREFUSED ::1 → IPv6 suspecté).
 */
interface OllamaAvailability {
  available: boolean;
  host: string;
  error?: string;
  errorKind?: "network" | "timeout" | "http" | "parse" | "unknown";
}

export const useOllamaStore = defineStore("ollama", () => {
  const available = ref(false);
  const models = ref<OllamaModelInfo[]>([]);
  const loading = ref(false);
  /** Cause lisible du dernier échec (null si succès ou pas encore testé). */
  const error = ref<string | null>(null);
  /** Catégorie d'erreur du dernier échec. */
  const errorKind = ref<OllamaAvailability["errorKind"] | null>(null);
  /** Host effectivement testé lors du dernier check. */
  const host = ref<string>("");

  async function check(hostArg?: string) {
    loading.value = true;
    try {
      if (hostArg) {
        await window.novelTradAPI.invoke("settings:set", "ollamaHost", hostArg);
      }
      if (import.meta.env.DEV) {
        console.log("[Ollama store] Calling ollama:is-available...");
      }
      const result = await window.novelTradAPI.invoke<OllamaAvailability>(
        "ollama:is-available",
      );
      if (import.meta.env.DEV) {
        console.log("[Ollama store] available =", result.available);
      }
      available.value = result.available;
      host.value = result.host;
      if (result.available) {
        error.value = null;
        errorKind.value = null;
        models.value = await window.novelTradAPI.invoke("ollama:list-models");
        if (import.meta.env.DEV) {
          console.log("[Ollama store] models =", models.value.length);
        }
      } else {
        error.value = result.error ?? "Raison inconnue";
        errorKind.value = result.errorKind ?? "unknown";
      }
    } catch (e) {
      console.error("[Ollama store] IPC failed:", e);
      available.value = false;
      error.value = e instanceof Error ? e.message : "Erreur IPC";
      errorKind.value = "unknown";
    } finally {
      loading.value = false;
    }
  }

  return { available, models, loading, error, errorKind, host, check };
});
