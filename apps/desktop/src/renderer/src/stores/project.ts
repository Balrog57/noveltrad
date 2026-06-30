import { defineStore } from "pinia";
import { ref } from "vue";
import type { Project, Chapter } from "@shared/types/index.js";

export const useProjectStore = defineStore("project", () => {
  const recentProjects = ref<Project[]>([]);
  const currentProject = ref<Project | null>(null);
  const chapters = ref<Chapter[]>([]);
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

  return {
    recentProjects,
    currentProject,
    chapters,
    loading,
    error,
    loadRecent,
    create,
    open,
  };
});
