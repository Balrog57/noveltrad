import { defineStore } from "pinia";
import { ref } from "vue";
import type { Job, Step, WorkflowStage } from "@shared/types/index.js";

export interface WorkflowProgressPayload {
  jobId: string;
  projectId: string;
  chapterId?: string;
  step: Step;
  totalSteps: number;
}

export const useWorkflowStore = defineStore("workflow", () => {
  const activeJobs = ref<Job[]>([]);
  const progress = ref<WorkflowProgressPayload | null>(null);
  const loading = ref(false);

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

  async function retryStep(jobId: string, stepId: string): Promise<void> {
    await window.novelTradAPI.invoke("workflow:retry-step", jobId, stepId);
  }

  async function retryFrom(jobId: string, stage: WorkflowStage): Promise<void> {
    await window.novelTradAPI.invoke("workflow:retry-from", jobId, stage);
  }

  return {
    activeJobs,
    progress,
    loading,
    start,
    pause,
    resume,
    cancel,
    list,
    retryStep,
    retryFrom,
  };
});
