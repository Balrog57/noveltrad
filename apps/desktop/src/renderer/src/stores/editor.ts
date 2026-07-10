import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Paragraph } from "@shared/types/index.js";
import { toPlain } from "../utils/toPlain";

/**
 * Store éditeur — gère les paragraphes en cours d'édition,
 * l'état de modification (dirty) et l'auto-save.
 */
export const useEditorStore = defineStore("editor", () => {
  const paragraphs = ref<Paragraph[]>([]);
  const chapterId = ref<string | null>(null);
  const dirtyParagraphs = ref<Set<string>>(new Set());
  const loading = ref(false);
  const error = ref<string | null>(null);

  /** Indique si des paragraphes modifiés n'ont pas encore été sauvegardés */
  const hasUnsavedChanges = computed(() => dirtyParagraphs.value.size > 0);

  /** Indique si un paragraphe donné a été modifié mais pas sauvegardé */
  function isDirty(paragraphId: string): boolean {
    return dirtyParagraphs.value.has(paragraphId);
  }

  /** Charge les paragraphes d'un chapitre depuis le main process */
  async function loadChapter(id: string): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      chapterId.value = id;
      paragraphs.value = await window.novelTradAPI.invoke<Paragraph[]>(
        "chapter:get-paragraphs",
        { chapterId: id },
      );
      dirtyParagraphs.value = new Set();
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors du chargement du chapitre";
      paragraphs.value = [];
    } finally {
      loading.value = false;
    }
  }

  /** Met à jour un paragraphe localement (marque comme modifié) */
  function updateParagraph(updated: Paragraph): void {
    const idx = paragraphs.value.findIndex((p) => p.id === updated.id);
    if (idx === -1) {return;}
    paragraphs.value[idx] = { ...updated };
    dirtyParagraphs.value = new Set([...dirtyParagraphs.value, updated.id]);
  }

  /** Sauvegarde uniquement les paragraphes modifiés via IPC */
  async function saveAll(): Promise<void> {
    if (!chapterId.value || paragraphs.value.length === 0) {return;}
    // Fix 5 : Ne sauvegarder que les paragraphes modifiés (dirty)
    const dirtyList = paragraphs.value.filter((p) =>
      dirtyParagraphs.value.has(p.id),
    );
    if (dirtyList.length === 0) {return;}
    loading.value = true;
    error.value = null;
    try {
      await window.novelTradAPI.invoke("chapter:save", {
        chapterId: chapterId.value,
        paragraphs: toPlain(dirtyList),
      });
      dirtyParagraphs.value = new Set();
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : "Erreur lors de la sauvegarde";
    } finally {
      loading.value = false;
    }
  }

  /** Réinitialise un paragraphe à son état source (efface la traduction) */
  function resetParagraph(paragraphId: string): void {
    const paragraph = paragraphs.value.find((p) => p.id === paragraphId);
    if (!paragraph) {return;}
    paragraph.translatedText = undefined;
    paragraph.status = "pending";
    dirtyParagraphs.value = new Set([...dirtyParagraphs.value, paragraphId]);
  }

  return {
    paragraphs,
    chapterId,
    dirtyParagraphs,
    loading,
    error,
    hasUnsavedChanges,
    isDirty,
    loadChapter,
    updateParagraph,
    saveAll,
    resetParagraph,
  };
});
