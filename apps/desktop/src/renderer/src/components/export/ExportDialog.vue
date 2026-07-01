<script setup lang="ts">
import { ref, computed } from "vue";
import { useProjectStore } from "../../stores/project";
import { useEditorStore } from "../../stores/editor";
import NtModal from "../ui/NtModal.vue";
import NtToast from "../ui/NtToast.vue";
import NtProgressBar from "../ui/NtProgressBar.vue";
import type { ExportFormat, Paragraph } from "@shared/types/index.js";
import type { ExportRunResult } from "@shared/schemas/export.js";

const props = defineProps<{
  /** Visibilité du dialogue */
  visible: boolean;
  /** ID du chapitre à exporter (null = tout le projet) */
  chapterId?: string | null;
  /** SDD §13.6 : IDs des chapitres sélectionnés pour l'export par lots */
  selectedChapterIds?: string[];
}>();

const emit = defineEmits<{
  /** Fermeture du dialogue */
  close: [];
  /** Export terminé avec succès */
  exported: [];
}>();

const projectStore = useProjectStore();
const editorStore = useEditorStore();

// --- État du formulaire ---
const selectedFormat = ref<ExportFormat>("markdown");
const bilingualMode = ref(false);
const outputFolder = ref("");
const includeTitle = ref(true);
const includeParagraphNumbers = ref(false);

// --- SDD §13.6 : Export par lots ---
const exportScope = ref<"chapter" | "selection" | "all">("chapter");

// --- État de l'export ---
const exporting = ref(false);
const exportProgress = ref(-1); // -1 = indeterminé
const toast = ref<{ message: string; type: "success" | "error" } | null>(null);

const formats: { value: ExportFormat; label: string }[] = [
  { value: "markdown", label: "Markdown (.md)" },
  { value: "txt", label: "Texte brut (.txt)" },
  { value: "html", label: "HTML (.html)" },
  { value: "docx", label: "Word (.docx)" },
  { value: "epub", label: "EPUB (.epub)" },
];

const projectTitle = computed(
  () => projectStore.currentProject?.name ?? "Export",
);

/** SDD §13.6 : indique si l'option d'export par sélection doit être affichée */
const hasSelection = computed(
  () => (props.selectedChapterIds?.length ?? 0) > 0,
);

/** SDD §13.6 : affiche les options de périmètre si on a un chapterId ou une sélection */
const showBatchOption = computed(() => props.chapterId || hasSelection.value);

/** Titre de l'export */
const exportTitle = computed(() => {
  if (props.chapterId && exportScope.value === "chapter") {
    const ch = projectStore.chapters.find((c) => c.id === props.chapterId);
    return ch?.title ?? "Chapitre sans titre";
  }
  return projectTitle.value;
});

/** Auteur du projet */
const author = computed(() => projectStore.currentProject?.author);

/** Extension de fichier selon le format */
function getExtension(): string {
  switch (selectedFormat.value) {
    case "markdown":
      return ".md";
    case "txt":
      return ".txt";
    case "html":
      return ".html";
    case "docx":
      return ".docx";
    case "epub":
      return ".epub";
  }
}

/** Nom du fichier de sortie complet */
const outputFileName = computed(() => {
  const safeName = exportTitle.value.replace(/[^a-z0-9\u00e0-\u024f]/gi, "_");
  return `${safeName}${getExtension()}`;
});

/** Chemin de sortie complet */
const outputPath = computed(() => {
  if (!outputFolder.value) return "";
  // Utiliser path.join côté renderer (pas idéal mais fonctionne)
  const folder = outputFolder.value.replace(/\\/g, "/");
  const name = outputFileName.value;
  return `${folder}/${name}`;
});

// --- Actions ---
async function browseFolder(): Promise<void> {
  const result = await window.novelTradAPI.invoke<{
    canceled: boolean;
    filePaths?: string[];
  }>("dialog:open-file", {
    properties: ["openDirectory"],
  });
  if (!result || result.canceled || !result.filePaths?.length) return;
  outputFolder.value = result.filePaths[0];
}

/** Charger les paragraphes pour un chapitre (utilisé depuis ChaptersView) */
async function loadParagraphsForChapter(
  chapterId: string,
): Promise<Paragraph[]> {
  try {
    const result = await window.novelTradAPI.invoke<{
      paragraphs: Paragraph[];
    }>("chapter:get-paragraphs", { chapterId });
    return result?.paragraphs ?? [];
  } catch {
    return [];
  }
}

async function doExport(): Promise<void> {
  if (!outputFolder.value) {
    toast.value = {
      message: "Veuillez sélectionner un dossier de sortie.",
      type: "error",
    };
    return;
  }

  exporting.value = true;
  exportProgress.value = -1;

  try {
    const projectId = projectStore.currentProject?.id;
    if (!projectId) {
      toast.value = { message: "Aucun projet ouvert.", type: "error" };
      return;
    }

    // Récupérer les paragraphes selon le périmètre d'export
    let paragraphs: Paragraph[];
    let batchChapterIds: string[] | null = null;

    if (exportScope.value === "selection" && hasSelection.value) {
      // SDD §13.6 : export par lots de la sélection
      batchChapterIds = props.selectedChapterIds ?? [];
      const all: Paragraph[] = [];
      for (const chId of batchChapterIds) {
        const chParagraphs = await loadParagraphsForChapter(chId);
        all.push(...chParagraphs);
      }
      paragraphs = all;
    } else if (props.chapterId && exportScope.value === "chapter") {
      // Utiliser les paragraphes du store éditeur si disponibles
      if (
        editorStore.chapterId === props.chapterId &&
        editorStore.paragraphs.length > 0
      ) {
        paragraphs = editorStore.paragraphs;
      } else {
        paragraphs = await loadParagraphsForChapter(props.chapterId);
      }
    } else {
      // Projet entier : charger tous les chapitres
      const all: Paragraph[] = [];
      for (const ch of projectStore.chapters) {
        const chParagraphs = await loadParagraphsForChapter(ch.id);
        all.push(...chParagraphs);
      }
      paragraphs = all;
    }

    if (paragraphs.length === 0) {
      toast.value = { message: "Aucun paragraphe à exporter.", type: "error" };
      return;
    }

    exportProgress.value = 50; // Simulation de progression

    // SDD §13.6 : si export par lots (sélection), utiliser exportBatch
    if (batchChapterIds && batchChapterIds.length > 0) {
      const result = await window.novelTradAPI.invoke<{
        success: boolean;
        paths?: string[];
        error?: { code: string; message: string };
      }>("export:batch", {
        projectId,
        projectTitle: projectTitle.value,
        author: author.value ?? undefined,
        chapterIds: batchChapterIds,
        format: selectedFormat.value,
        outputDir: outputFolder.value,
        options: {
          includeTitle: includeTitle.value,
          includeParagraphNumbers: includeParagraphNumbers.value,
          bilingual: bilingualMode.value,
        },
      });

      exportProgress.value = 100;

      if (result.success && result.paths) {
        toast.value = {
          message: `Export par lots réussi : ${result.paths.length} fichier(s) généré(s) dans ${outputFolder.value}`,
          type: "success",
        };
        emit("exported");
        setTimeout(() => emit("close"), 800);
      } else if (result.error) {
        toast.value = { message: result.error.message, type: "error" };
      }
    } else {
      const result = await window.novelTradAPI.invoke<ExportRunResult>(
        "export:run",
        {
          projectId,
          chapterId: props.chapterId ?? undefined,
          title: exportTitle.value,
          author: author.value ?? undefined,
          paragraphs,
          format: selectedFormat.value,
          outputPath: outputPath.value,
          options: {
            includeTitle: includeTitle.value,
            includeParagraphNumbers: includeParagraphNumbers.value,
            bilingual: bilingualMode.value,
          },
        },
      );

      exportProgress.value = 100;

      if (result.success) {
        toast.value = {
          message: `Export réussi : ${result.path} (${formatSize(result.size ?? 0)})`,
          type: "success",
        };
        emit("exported");
        setTimeout(() => emit("close"), 800);
      } else {
        toast.value = {
          message: result.error.message,
          type: "error",
        };
      }
    }
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Erreur inconnue lors de l'export.";
    toast.value = { message, type: "error" };
  } finally {
    exporting.value = false;
    // Réinitialiser la progression après un délai
    setTimeout(() => {
      exportProgress.value = -1;
    }, 500);
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

function closeDialog(): void {
  if (exporting.value) return;
  emit("close");
}

function clearToast(): void {
  toast.value = null;
}
</script>

<template>
  <NtModal :visible="visible" title="Exporter" size="md" @close="closeDialog">
    <div class="export-form">
      <!-- Format -->
      <div class="form-group">
        <label class="form-label">Format</label>
        <select
          v-model="selectedFormat"
          class="form-select"
          :disabled="exporting"
        >
          <option v-for="fmt in formats" :key="fmt.value" :value="fmt.value">
            {{ fmt.label }}
          </option>
        </select>
      </div>

      <!-- Mode bilingue -->
      <div class="form-group">
        <label class="form-checkbox">
          <input
            v-model="bilingualMode"
            type="checkbox"
            :disabled="exporting"
          />
          <span>Mode bilingue (source + traduction)</span>
        </label>
      </div>

      <!-- SDD §13.6 : Export par lots (sélection) -->
      <div v-if="showBatchOption" class="form-group">
        <label class="form-label">Périmètre d'export</label>
        <label class="form-checkbox">
          <input
            v-model="exportScope"
            type="radio"
            value="chapter"
            :disabled="exporting"
          />
          <span>Chapitre courant uniquement</span>
        </label>
        <label class="form-checkbox">
          <input
            v-model="exportScope"
            type="radio"
            value="selection"
            :disabled="exporting || !hasSelection"
          />
          <span>
            Sélection ({{ selectedChapterIds?.length ?? 0 }} chapitre(s))
          </span>
        </label>
        <label class="form-checkbox">
          <input
            v-model="exportScope"
            type="radio"
            value="all"
            :disabled="exporting"
          />
          <span>Tous les chapitres</span>
        </label>
      </div>

      <!-- Dossier de sortie -->
      <div class="form-group">
        <label class="form-label">Dossier de sortie</label>
        <div class="form-row">
          <input
            v-model="outputFolder"
            type="text"
            class="form-input"
            placeholder="C:\Utilisateurs\..."
            :disabled="exporting"
            readonly
          />
          <button
            class="btn-secondary"
            :disabled="exporting"
            @click="browseFolder"
          >
            Parcourir
          </button>
        </div>
        <p v-if="outputPath" class="form-hint">
          Fichier : {{ outputFileName }}
        </p>
      </div>

      <!-- Options -->
      <div class="form-group">
        <label class="form-label">Options</label>
        <label class="form-checkbox">
          <input v-model="includeTitle" type="checkbox" :disabled="exporting" />
          <span>Inclure le titre</span>
        </label>
        <label class="form-checkbox">
          <input
            v-model="includeParagraphNumbers"
            type="checkbox"
            :disabled="exporting"
          />
          <span>Numéroter les paragraphes</span>
        </label>
      </div>

      <!-- Progression -->
      <NtProgressBar
        v-if="exporting"
        :value="exportProgress"
        :label="exportProgress >= 0 ? undefined : 'Export en cours...'"
      />

      <!-- Résumé -->
      <div class="export-summary">
        <p>
          <strong>{{ exportTitle }}</strong>
        </p>
        <p>
          {{
            formats.find((f) => f.value === selectedFormat)?.label ?? "Markdown"
          }}
        </p>
      </div>
    </div>

    <template #footer>
      <button class="btn-cancel" :disabled="exporting" @click="closeDialog">
        Annuler
      </button>
      <button
        class="btn-primary"
        :disabled="exporting || !outputFolder"
        @click="doExport"
      >
        Exporter
      </button>
    </template>
  </NtModal>

  <!-- Toast notification -->
  <NtToast
    v-if="toast"
    :message="toast.message"
    :type="toast.type"
    @close="clearToast"
  />
</template>

<style scoped>
.export-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-select {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  padding: 8px 12px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  cursor: pointer;
}

.form-select:focus {
  border-color: var(--accent);
}

.form-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-row {
  display: flex;
  gap: 8px;
}

.form-input {
  flex: 1;
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  padding: 8px 12px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
}

.form-input:focus {
  border-color: var(--accent);
}

.form-input:disabled {
  opacity: 0.5;
}

.form-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
}

.form-checkbox input[type="checkbox"] {
  accent-color: var(--accent);
  width: 16px;
  height: 16px;
}

.form-checkbox input[type="checkbox"]:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.export-summary {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text-secondary);
}

.export-summary p {
  margin: 2px 0;
}

.export-summary strong {
  color: var(--text-primary);
}

.btn-primary {
  background-color: var(--accent);
  color: #0f172a;
  border: none;
  padding: 8px 20px;
  border-radius: var(--border-radius);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: none;
  padding: 8px 16px;
  border-radius: var(--border-radius);
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.15s;
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--accent-hover);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel {
  background: none;
  border: 1px solid var(--bg-tertiary);
  color: var(--text-secondary);
  padding: 8px 20px;
  border-radius: var(--border-radius);
  font-size: 14px;
  cursor: pointer;
}

.btn-cancel:hover:not(:disabled) {
  color: var(--text-primary);
  border-color: var(--text-secondary);
}

.btn-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
