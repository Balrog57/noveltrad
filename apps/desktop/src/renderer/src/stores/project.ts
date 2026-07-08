import { defineStore } from "pinia";
import { ref } from "vue";
import type { Project, Chapter } from "@shared/types/index.js";

/** Statistiques d'un projet (SDD §4.6) */
export interface ProjectStats {
  chapterCount: number;
  totalParagraphs: number;
  translatedParagraphs: number;
  sourceWordCount: number;
  targetWordCount: number;
  averageQualityScore: number | null;
  lastWorkflowStatus: string | null;
}

export const useProjectStore = defineStore("project", () => {
  const recentProjects = ref<Project[]>([]);
  const currentProject = ref<Project | null>(null);
  const chapters = ref<Chapter[]>([]);
  const stats = ref<ProjectStats | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function loadRecent() {
    loading.value = true;
    error.value = null;
    try {
      recentProjects.value = await window.novelTradAPI.invoke(
        "project:list-recent",
      );
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Erreur inconnue";
    } finally {
      loading.value = false;
    }
  }

  async function create(payload: {
    name: string;
    sourceLanguage: string;
    targetLanguage: string;
    parentPath: string;
  }) {
    loading.value = true;
    error.value = null;
    try {
      const project = await window.novelTradAPI.invoke<Project>(
        "project:create",
        payload,
      );
      currentProject.value = project;
      await loadRecent();
      return project;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Erreur inconnue";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function open(projectPath: string) {
    loading.value = true;
    error.value = null;
    try {
      const project = await window.novelTradAPI.invoke<Project>(
        "project:open",
        projectPath,
      );
      currentProject.value = project;
      await loadRecent();
      return project;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Erreur inconnue";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Charge les statistiques du projet depuis la base de données.
   * SDD §4.6 — Tableau de bord projet.
   */
  async function loadStats(projectId: string): Promise<void> {
    try {
      stats.value = await window.novelTradAPI.invoke<ProjectStats>(
        "project:stats",
        projectId,
      );
      error.value = null;
    } catch (err) {
      console.error("[project store] loadStats error:", err);
      stats.value = null;
      error.value = err instanceof Error ? err.message : "Failed to load stats";
    }
  }

  return {
    recentProjects,
    currentProject,
    chapters,
    stats,
    loading,
    error,
    loadRecent,
    create,
    open,
    loadStats,
  };
});
