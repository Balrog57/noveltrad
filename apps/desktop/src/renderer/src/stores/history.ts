import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { HistorySnapshot, DiffResult } from "@shared/types/index.js";

/**
 * Store de l'historique des versions.
 * Gère la liste des snapshots, la comparaison (diff), le rollback complet
 * et le rollback partiel (SDD §14.5).
 */
export const useHistoryStore = defineStore("history", () => {
  const snapshots = ref<HistorySnapshot[]>([]);
  const selectedSnapshot = ref<HistorySnapshot | null>(null);
  const diffResult = ref<DiffResult | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /** Snapshots triés par version décroissante */
  const sortedSnapshots = computed(() => {
    return [...snapshots.value].sort(
      (a, b) => (b.versionNumber ?? 0) - (a.versionNumber ?? 0),
    );
  });

  /** Paragraphes du snapshot sélectionné (pour rollback partiel) */
  const snapshotParagraphs = ref<
    Array<{ id: string; index: number; sourceText: string; translatedText?: string; selected: boolean }>
  >([]);

  /** IDs des paragraphes sélectionnés pour le rollback partiel */
  const selectedParagraphIds = ref<Set<string>>(new Set());

  /** État du dialogue de sélection de paragraphes */
  const showParagraphSelector = ref(false);

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

  /** Charge les paragraphes d'un snapshot (reconstruction) */
  async function loadSnapshotParagraphs(
    projectId: string,
    snapshotId: string,
  ): Promise<void> {
    try {
      const paragraphs = await window.novelTradAPI.invoke<
        Array<{ id: string; indexInChapter: number; sourceText: string; translatedText?: string }>
      >("history:get-paragraphs", { projectId, snapshotId });
      snapshotParagraphs.value = paragraphs.map((p) => ({
        id: p.id,
        index: p.indexInChapter,
        sourceText: p.sourceText,
        translatedText: p.translatedText,
        selected: false,
      }));
      selectedParagraphIds.value = new Set();
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors du chargement des paragraphes du snapshot";
    }
  }

  /** Bascule la sélection d'un paragraphe */
  function toggleParagraph(id: string): void {
    const set = new Set(selectedParagraphIds.value);
    if (set.has(id)) {
      set.delete(id);
    } else {
      set.add(id);
    }
    selectedParagraphIds.value = set;
    // Mettre à jour le tableau pour l'UI
    snapshotParagraphs.value = snapshotParagraphs.value.map((p) =>
      p.id === id ? { ...p, selected: set.has(id) } : p,
    );
  }

  /** Sélectionne ou désélectionne tous les paragraphes */
  function toggleAllParagraphs(selected: boolean): void {
    if (selected) {
      selectedParagraphIds.value = new Set(
        snapshotParagraphs.value.map((p) => p.id),
      );
    } else {
      selectedParagraphIds.value = new Set();
    }
    snapshotParagraphs.value = snapshotParagraphs.value.map((p) => ({
      ...p,
      selected,
    }));
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

  /** Restaure tous les paragraphes depuis un snapshot (rollback complet) */
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
      await loadHistory(projectId, chapterId);
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : "Erreur lors du rollback";
    } finally {
      loading.value = false;
    }
  }

  /** Restaure uniquement certains paragraphes depuis un snapshot (rollback partiel, SDD §14.5) */
  async function rollbackPartial(
    projectId: string,
    chapterId: string,
    snapshotId: string,
    paragraphIds: string[],
  ): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await window.novelTradAPI.invoke("history:rollback-partial", {
        projectId,
        chapterId,
        snapshotId,
        paragraphIds,
      });
      showParagraphSelector.value = false;
      await loadHistory(projectId, chapterId);
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors du rollback partiel";
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
    snapshotParagraphs,
    selectedParagraphIds,
    showParagraphSelector,
    loadHistory,
    loadDiff,
    rollback,
    rollbackPartial,
    createManualSnapshot,
    loadSnapshotParagraphs,
    toggleParagraph,
    toggleAllParagraphs,
  };
});
