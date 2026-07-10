import { defineStore } from "pinia";
import { ref } from "vue";
import type { Job, Step, WorkflowStage } from "@shared/types/index.js";
import { toPlain } from "../utils/toPlain";

export interface WorkflowProgressPayload {
  jobId: string;
  projectId: string;
  chapterId?: string;
  step: Step;
  totalSteps: number;
  batchChapterIndex?: number;
  batchTotalChapters?: number;
}

export const useWorkflowStore = defineStore("workflow", () => {
  const activeJobs = ref<Job[]>([]);
  const progress = ref<WorkflowProgressPayload | null>(null);
  const loading = ref(false);
  /** SDD §7.9 : IDs des chapitres sélectionnés pour le batch */
  const selectedChapterIds = ref<string[]>([]);

  window.novelTradAPI.on("workflow:progress", (payload: unknown) => {
    const p = payload as WorkflowProgressPayload;
    progress.value = p;
  });

  async function start(projectPath: string, chapterId?: string): Promise<Job> {
    loading.value = true;
    try {
      const job = await window.novelTradAPI.invoke<Job>(
        "workflow:start",
        projectPath,
        chapterId,
      );
      activeJobs.value = [job, ...activeJobs.value];
      return job;
    } finally {
      loading.value = false;
    }
  }

  async function startBatch(
    projectPath: string,
    chapterIds: string[],
  ): Promise<Job> {
    loading.value = true;
    try {
      const job = await window.novelTradAPI.invoke<Job>(
        "workflow:start-batch",
        projectPath,
        chapterIds,
      );
      activeJobs.value = [job, ...activeJobs.value];
      return job;
    } finally {
      loading.value = false;
    }
  }

  async function pause(jobId: string): Promise<void> {
    await window.novelTradAPI.invoke("workflow:pause", jobId);
  }

  async function resume(jobId: string): Promise<void> {
    await window.novelTradAPI.invoke("workflow:resume", jobId);
  }

  async function cancel(jobId: string): Promise<void> {
    await window.novelTradAPI.invoke("workflow:cancel", jobId);
  }

  async function list(projectPath: string): Promise<Job[]> {
    return window.novelTradAPI.invoke<Job[]>("workflow:list", projectPath);
  }

  /** SDD §7.11 : liste les jobs en cours (running/paused) pour la reprise */
  async function listActive(projectPath: string): Promise<Job[]> {
    return window.novelTradAPI.invoke<Job[]>(
      "workflow:list-active",
      projectPath,
    );
  }

  /** SDD §7.11 : reprend un job batch interrompu */
  async function resumeBatch(projectPath: string, job: Job): Promise<void> {
    await window.novelTradAPI.invoke("workflow:resume-batch", projectPath, toPlain(job));
  }

  async function retryStep(jobId: string, stepId: string): Promise<void> {
    await window.novelTradAPI.invoke("workflow:retry-step", jobId, stepId);
  }

  async function retryFrom(jobId: string, stage: WorkflowStage): Promise<void> {
    await window.novelTradAPI.invoke("workflow:retry-from", jobId, stage);
  }

  // --- SDD §7.9 : gestion de la sélection multiple de chapitres ---

  /** Bascule la sélection d'un chapitre */
  function toggleChapterSelection(chapterId: string): void {
    const idx = selectedChapterIds.value.indexOf(chapterId);
    if (idx >= 0) {
      selectedChapterIds.value.splice(idx, 1);
    } else {
      selectedChapterIds.value.push(chapterId);
    }
  }

  /** Sélectionne tous les chapitres donnés */
  function selectAll(chapterIds: string[]): void {
    selectedChapterIds.value = [...chapterIds];
  }

  /** Désélectionne tous les chapitres */
  function clearSelection(): void {
    selectedChapterIds.value = [];
  }

  /** Vérifie si un chapitre est sélectionné */
  function isSelected(chapterId: string): boolean {
    return selectedChapterIds.value.includes(chapterId);
  }

  return {
    activeJobs,
    progress,
    loading,
    selectedChapterIds,
    start,
    startBatch,
    pause,
    resume,
    cancel,
    list,
    listActive,
    resumeBatch,
    retryStep,
    retryFrom,
    toggleChapterSelection,
    selectAll,
    clearSelection,
    isSelected,
  };
});
