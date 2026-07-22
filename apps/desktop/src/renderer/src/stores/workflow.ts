import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { WorkflowStage } from "@shared/types/index.js";

/**
 * v3 : payload de progression du SimpleWorkflowRunner.
 * Remplace l'ancien WorkflowProgressPayload (basé sur Step/totalSteps) —
 * le runner v3 ne persiste plus de jobs/steps, il émet un payload allégé
 * par stage.
 */
export interface SimpleProgressPayload {
  jobId: string;
  projectId: string;
  chapterId?: string;
  stage: WorkflowStage;
  stageIndex: number;
  totalStages: number;
  batchChapterIndex?: number;
  batchTotalChapters?: number;
  status: "running" | "completed" | "failed";
}

/** Les 4 stages v3, dans l'ordre (pour l'inspecteur d'agents). */
const PIPELINE_STAGES: WorkflowStage[] = [
  "translate",
  "proofread",
  "glossary",
  "validate",
];

export const useWorkflowStore = defineStore("workflow", () => {
  /** JobId du run courant (null si aucun run actif). */
  const activeJobId = ref<string | null>(null);
  /** Dernier event de progression reçu. */
  const progress = ref<SimpleProgressPayload | null>(null);
  /** Erreur éventuelle. */
  const error = ref<string | null>(null);
  /** Chapitres sélectionnés pour un batch. */
  const selectedChapterIds = ref<string[]>([]);

  // Écoute des events de progression du main process.
  window.novelTradAPI.on("workflow:progress", (payload: unknown) => {
    progress.value = payload as SimpleProgressPayload;
  });

  /**
   * Lance la traduction d'un chapitre unique.
   * Retourne le jobId (le run est fire-and-forget côté main).
   */
  async function start(projectPath: string, chapterId: string): Promise<string> {
    error.value = null;
    try {
      const job = await window.novelTradAPI.invoke<{ id: string }>(
        "workflow:start",
        projectPath,
        chapterId,
      );
      activeJobId.value = job.id;
      return job.id;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Erreur lors du démarrage";
      throw err;
    }
  }

  /** Lance la traduction d'un batch de chapitres. */
  async function startBatch(projectPath: string, chapterIds: string[]): Promise<string> {
    error.value = null;
    try {
      const job = await window.novelTradAPI.invoke<{ id: string }>(
        "workflow:start-batch",
        projectPath,
        chapterIds,
      );
      activeJobId.value = job.id;
      return job.id;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Erreur lors du démarrage du batch";
      throw err;
    }
  }

  /** Annule le run courant. */
  async function cancel(): Promise<void> {
    if (!activeJobId.value) {
      return;
    }
    try {
      await window.novelTradAPI.invoke("workflow:cancel", activeJobId.value);
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Erreur lors de l'annulation";
    }
  }

  /**
   * Statut calculé de chaque stage du pipeline (pour l'inspecteur d'agents).
   * Déduit depuis le dernier event de progression :
   *   - "completed" si l'event status=completed a été vu pour ce stage.
   *   - "running" si c'est le stage courant.
   *   - "pending" sinon.
   */
  const stageStatuses = computed<Record<string, "pending" | "running" | "completed" | "failed">>(() => {
    const result: Record<string, "pending" | "running" | "completed" | "failed"> = {};
    for (const s of PIPELINE_STAGES) {
      result[s] = "pending";
    }
    if (!progress.value) {
      return result;
    }
    const p = progress.value;
    // Les stages avant le courant sont completed ; le courant a son status.
    for (let i = 0; i < p.stageIndex; i++) {
      result[PIPELINE_STAGES[i]] = "completed";
    }
    result[p.stage] = p.status === "running" ? "running" : p.status;
    if (p.status === "completed" && p.stageIndex === p.totalStages - 1) {
      // Dernier stage complété → tout est completed.
      for (const s of PIPELINE_STAGES) {
        result[s] = "completed";
      }
    }
    return result;
  });

  /** True si un run est en cours (stage courant en cours). */
  const isRunning = computed(() => {
    return progress.value?.status === "running" && activeJobId.value !== null;
  });

  // ── Sélection de chapitres (pour le batch) ──

  function toggleChapterSelection(chapterId: string): void {
    const idx = selectedChapterIds.value.indexOf(chapterId);
    if (idx >= 0) {
      selectedChapterIds.value.splice(idx, 1);
    } else {
      selectedChapterIds.value.push(chapterId);
    }
  }

  function selectAll(chapterIds: string[]): void {
    selectedChapterIds.value = [...chapterIds];
  }

  function clearSelection(): void {
    selectedChapterIds.value = [];
  }

  function isSelected(chapterId: string): boolean {
    return selectedChapterIds.value.includes(chapterId);
  }

  /** Réinitialise l'état du run (après fin/annulation). */
  function reset(): void {
    activeJobId.value = null;
    progress.value = null;
  }

  return {
    activeJobId,
    progress,
    error,
    selectedChapterIds,
    stageStatuses,
    isRunning,
    start,
    startBatch,
    cancel,
    toggleChapterSelection,
    selectAll,
    clearSelection,
    isSelected,
    reset,
  };
});
