import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { LexiconEntry, CandidateTerm } from "@shared/types/index.js";

/**
 * Store lexique — gère les entrées lexicales, les filtres,
 * l'import/export et l'extraction de candidats.
 */
export const useLexiconStore = defineStore("lexicon", () => {
  const entries = ref<LexiconEntry[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const searchQuery = ref("");
  const categoryFilter = ref<string | null>(null);
  const candidates = ref<CandidateTerm[]>([]);

  /** Entrées filtrées par recherche et catégorie */
  const filteredEntries = computed(() => {
    let result = entries.value;

    // Filtre par recherche (terme, traduction, alias)
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase().trim();
      result = result.filter(
        (e) =>
          e.term.toLowerCase().includes(q) ||
          e.translation.toLowerCase().includes(q) ||
          e.aliases.some((a) => a.toLowerCase().includes(q)),
      );
    }

    // Filtre par catégorie
    if (categoryFilter.value) {
      result = result.filter((e) => e.category === categoryFilter.value);
    }

    return result;
  });

  /** Catégories uniques déduites des entrées */
  const categories = computed(() => {
    const cats = new Set(entries.value.map((e) => e.category));
    return Array.from(cats).sort();
  });

  /** Charge les entrées de lexique pour un projet */
  async function loadLexicon(projectId: string): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      entries.value = await window.novelTradAPI.invoke<LexiconEntry[]>(
        "lexicon:list",
        { projectId },
      );
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors du chargement du lexique";
      entries.value = [];
    } finally {
      loading.value = false;
    }
  }

  /** Sauvegarde (insert ou update) une entrée de lexique */
  async function saveEntry(entry: LexiconEntry): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.novelTradAPI.invoke<{
        success: boolean;
        entry: LexiconEntry;
      }>("lexicon:save", {
        projectId: entry.projectId,
        entry,
      });
      // Remplacer dans la liste locale si existant, sinon ajouter
      const idx = entries.value.findIndex((e) => e.id === result.entry.id);
      if (idx >= 0) {
        entries.value[idx] = result.entry;
      } else {
        entries.value.push(result.entry);
      }
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors de la sauvegarde de l'entrée";
    } finally {
      loading.value = false;
    }
  }

  /** Supprime une entrée de lexique */
  async function deleteEntry(
    entryId: string,
    projectId: string,
  ): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await window.novelTradAPI.invoke("lexicon:delete", {
        projectId,
        entryId,
      });
      entries.value = entries.value.filter((e) => e.id !== entryId);
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors de la suppression de l'entrée";
    } finally {
      loading.value = false;
    }
  }

  /** Importe des entrées depuis un format (CSV, JSON, TSV) */
  async function importLexicon(
    projectId: string,
    format: "csv" | "json" | "tsv",
    data: string,
  ): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await window.novelTradAPI.invoke("lexicon:import", {
        projectId,
        format,
        data,
      });
      // Recharger après import
      await loadLexicon(projectId);
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors de l'import du lexique";
    } finally {
      loading.value = false;
    }
  }

  /** Exporte les entrées dans le format demandé */
  async function exportLexicon(
    projectId: string,
    format: "csv" | "json" | "tsv",
  ): Promise<string> {
    loading.value = true;
    error.value = null;
    try {
      const content = await window.novelTradAPI.invoke<string>(
        "lexicon:export",
        { projectId, format },
      );
      return content;
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors de l'export du lexique";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /** Extrait les termes candidats d'un texte source */
  async function extractCandidates(
    text: string,
    language: string,
  ): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      candidates.value = await window.novelTradAPI.invoke<CandidateTerm[]>(
        "lexicon:extract-candidates",
        { text, language },
      );
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : "Erreur lors de l'extraction des candidats";
      candidates.value = [];
    } finally {
      loading.value = false;
    }
  }

  return {
    entries,
    loading,
    error,
    searchQuery,
    categoryFilter,
    candidates,
    filteredEntries,
    categories,
    loadLexicon,
    saveEntry,
    deleteEntry,
    importLexicon,
    exportLexicon,
    extractCandidates,
  };
});
