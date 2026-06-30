import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { HistorySnapshot, DiffResult } from "@shared/types/index.js";

/**
 * Store de l'historique des versions.
 * Gère la liste des snapshots, la comparaison (diff) et le rollback.
 */
export const useHistoryStore = defineStore("history", () => {
  const snapshots = ref<HistorySnapshot[]>([]);
  const selectedSnapshot = ref<HistorySnapshot | null>(null);
  const diffResult = ref<DiffResult | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /** Snapshots triés par version décroissante (numéro déjà dérivé du backend) */
  const sortedSnapshots = computed(() => {
    return [...snapshots.value].sort(
      (a, b) => (b.versionNumber ?? 0) - (a.versionNumber ?? 0),
    );
  });

  /** Charge l'historique pour un projet (et optionnellement un chapitre) */
  async function loadHistory(
    projectId: string,
    chapterId?: string,
  ): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      snapshots.value = await window.novelTradAPI.invoke<HistorySnapshot[]>(
        "history:list",
        { projectId, chapterId },
      );
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors du chargement de l'historique";
      snapshots.value = [];
    } finally {
      loading.value = false;
    }
  }

  /** Calcule le diff entre le snapshot sélectionné et le plus récent */
  async function loadDiff(
    snapshotIdA: string,
    snapshotIdB: string,
  ): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      diffResult.value = await window.novelTradAPI.invoke<DiffResult>(
        "history:diff",
        {
          projectId: snapshots.value[0]?.projectId ?? "",
          snapshotIdA,
          snapshotIdB,
        },
      );
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors de la comparaison des versions";
      diffResult.value = null;
    } finally {
      loading.value = false;
    }
  }

  /** Restaure les paragraphes depuis un snapshot (rollback) */
  async function rollback(
    projectId: string,
    chapterId: string,
    snapshotId: string,
  ): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await window.novelTradAPI.invoke("history:rollback", {
        projectId,
        chapterId,
        snapshotId,
      });
      // Recharger l'historique après rollback
      await loadHistory(projectId, chapterId);
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : "Erreur lors du rollback";
    } finally {
      loading.value = false;
    }
  }

  /** Crée un snapshot manuel de l'état actuel */
  async function createManualSnapshot(
    projectId: string,
    chapterId: string,
    paragraphs: HistorySnapshot["paragraphs"],
  ): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await window.novelTradAPI.invoke("history:create-snapshot", {
        projectId,
        chapterId,
        stage: "manual",
        paragraphs,
        triggeredBy: "manual",
      });
      await loadHistory(projectId, chapterId);
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors de la création du snapshot";
    } finally {
      loading.value = false;
    }
  }

  return {
    snapshots,
    selectedSnapshot,
    diffResult,
    loading,
    error,
    sortedSnapshots,
    loadHistory,
    loadDiff,
    rollback,
    createManualSnapshot,
  };
});
