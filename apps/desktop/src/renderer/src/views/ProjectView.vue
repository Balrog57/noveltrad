<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "../stores/project";
import { useWorkflowStore } from "../stores/workflow";
import { onMounted, ref, computed, watch } from "vue";
import { stageLabel } from "../composables/useStatusLabels";
import ExportDialog from "../components/export/ExportDialog.vue";
import NtEmptyState from "../components/ui/NtEmptyState.vue";
import { toPlain } from "../utils/toPlain";
import type { Chapter, Paragraph } from "@shared/types/index.js";

interface OpenDialogResult {
  canceled: boolean;
  filePaths?: string[];
}

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const workflowStore = useWorkflowStore();
const project = computed(() => projectStore.currentProject);
const projectId = (route.params.projectId as string) || "";

// ── État local ──
const selectedChapterId = ref<string | null>(null);
const paragraphs = ref<Paragraph[]>([]);
const loadingParagraphs = ref(false);
const showExport = ref(false);
const importStatus = ref<string | null>(null);

const selectedChapter = computed<Chapter | undefined>(() =>
  projectStore.chapters.find((c) => c.id === selectedChapterId.value),
);

/** Texte source agrégé (pour l'affichage). */
const sourceText = computed(() =>
  paragraphs.value.map((p) => p.sourceText).join("\n\n"),
);

/** Texte traduit agrégé. */
const targetText = computed(() =>
  paragraphs.value
    .map((p) => p.translatedText ?? "")
    .filter((t) => t.length > 0)
    .join("\n\n"),
);

/** Les 4 stages pour l'inspecteur. */
const pipelineStages = ["translate", "proofread", "glossary", "validate"] as const;

onMounted(async () => {
  if (!projectStore.currentProject) {
    await projectStore.loadRecent();
    const found =
      projectStore.recentProjects.find((p) => p.id === projectId) || null;
    if (found) {
      projectStore.currentProject = found;
    }
  }
  await projectStore.loadChapters(projectId);
  // Sélectionner le premier chapitre par défaut.
  if (projectStore.chapters.length > 0 && !selectedChapterId.value) {
    selectedChapterId.value = projectStore.chapters[0].id;
  }
});

// Recharger les paragraphes quand le chapitre sélectionné change.
watch(selectedChapterId, async (id) => {
  if (!id) {
    paragraphs.value = [];
    return;
  }
  loadingParagraphs.value = true;
  try {
    paragraphs.value = await window.novelTradAPI.invoke<Paragraph[]>(
      "chapter:get-paragraphs",
      toPlain({ chapterId: id }),
    );
  } catch (err) {
    console.error("[ProjectView] load paragraphs error:", err);
    paragraphs.value = [];
  } finally {
    loadingParagraphs.value = false;
  }
}, { immediate: true });

// ── Actions ──

async function importFile() {
  importStatus.value = null;
  const result = await window.novelTradAPI.invoke<OpenDialogResult>(
    "dialog:open-file",
    toPlain({
      filters: [
        { name: "Documents", extensions: ["txt", "md", "epub", "docx"] },
      ],
      properties: ["openFile"],
    }),
  );
  if (!result || !result.filePaths?.length) {
    return;
  }
  try {
    const chapters = await window.novelTradAPI.invoke<Chapter[]>(
      "chapter:import",
      projectId,
      result.filePaths[0],
    );
    importStatus.value = `${chapters.length} chapitre(s) importé(s).`;
    await projectStore.loadChapters(projectId);
    if (projectStore.chapters.length > 0 && !selectedChapterId.value) {
      selectedChapterId.value = projectStore.chapters[0].id;
    }
  } catch (err) {
    importStatus.value = err instanceof Error ? err.message : "Erreur d'import";
  }
}

async function translateCurrent() {
  if (!project.value || !selectedChapterId.value) {
    return;
  }
  workflowStore.reset();
  await workflowStore.start(project.value.path, selectedChapterId.value);
}

async function translateAll() {
  if (!project.value || projectStore.chapters.length === 0) {
    return;
  }
  workflowStore.reset();
  await workflowStore.startBatch(
    project.value.path,
    projectStore.chapters.map((c) => c.id),
  );
}

async function cancelRun() {
  await workflowStore.cancel();
}
</script>

<template>
  <div v-if="project" class="project">
    <!-- En-tête -->
    <header class="project-header">
      <div class="header-left">
        <button class="btn-back" @click="router.push({ name: 'home' })">←</button>
        <div>
          <h1>{{ project.name }}</h1>
          <p class="project-meta">
            {{ project.sourceLanguage }} → {{ project.targetLanguage }}
          </p>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="importFile">📥 Importer</button>
        <button class="btn-secondary" @click="showExport = true">📤 Exporter</button>
      </div>
    </header>

    <p v-if="importStatus" class="import-status">{{ importStatus }}</p>

    <!-- Sélecteur de chapitre -->
    <section v-if="projectStore.chapters.length > 0" class="chapter-selector">
      <label for="chapter-select">Chapitre</label>
      <select
        id="chapter-select"
        v-model="selectedChapterId"
        :disabled="workflowStore.isRunning"
      >
        <option
          v-for="ch in projectStore.chapters"
          :key="ch.id"
          :value="ch.id"
        >
          {{ ch.title || `Chapitre ${ch.orderIndex + 1}` }}
          <template v-if="ch.status === 'completed'"> ✓</template>
        </option>
      </select>
    </section>

    <!-- État vide : aucun chapitre -->
    <NtEmptyState
      v-else
      icon="📖"
      title="Aucun chapitre"
      description="Importez un fichier (TXT, DOCX, EPUB) pour commencer."
      action-label="📥 Importer un fichier"
      @action="importFile"
    />

    <!-- Source / Cible -->
    <section v-if="selectedChapterId" class="panes">
      <div class="pane">
        <div class="pane-header">
          <span>SOURCE ({{ project.sourceLanguage }})</span>
        </div>
        <div v-if="loadingParagraphs" class="pane-loading">Chargement…</div>
        <pre v-else class="pane-content">{{ sourceText || '(vide)' }}</pre>
      </div>
      <div class="pane">
        <div class="pane-header">
          <span>TRADUCTION ({{ project.targetLanguage }})</span>
        </div>
        <div v-if="loadingParagraphs" class="pane-loading">Chargement…</div>
        <pre v-else class="pane-content">{{ targetText || '(pas encore traduit)' }}</pre>
      </div>
    </section>

    <!-- Boutons de traduction -->
    <section v-if="selectedChapterId" class="translate-actions">
      <button
        v-if="!workflowStore.isRunning"
        class="btn-primary"
        :disabled="!selectedChapterId"
        @click="translateCurrent"
      >
        ▶ Traduire ce chapitre (pipeline 4 agents)
      </button>
      <button
        v-if="!workflowStore.isRunning && projectStore.chapters.length > 1"
        class="btn-secondary"
        @click="translateAll"
      >
        ▶▶ Traduire tous les chapitres
      </button>
      <button
        v-if="workflowStore.isRunning"
        class="btn-danger"
        @click="cancelRun"
      >
        ⏹ Annuler
      </button>
    </section>

    <!-- Inspecteur d'agents (temps réel) -->
    <section v-if="workflowStore.activeJobId || workflowStore.progress" class="inspector">
      <h2 class="section-title">Inspecteur du pipeline</h2>
      <div class="pipeline">
        <div
          v-for="(stage, i) in pipelineStages"
          :key="stage"
          class="pipeline-step"
          :class="workflowStore.stageStatuses[stage]"
        >
          <span class="step-icon">
            <template v-if="workflowStore.stageStatuses[stage] === 'completed'">✓</template>
            <template v-else-if="workflowStore.stageStatuses[stage] === 'running'">⏳</template>
            <template v-else-if="workflowStore.stageStatuses[stage] === 'failed'">✗</template>
            <template v-else>○</template>
          </span>
          <span class="step-label">{{ stageLabel(stage) }}</span>
          <span class="step-index">{{ i + 1 }}/4</span>
        </div>
      </div>
      <p v-if="workflowStore.progress" class="progress-detail">
        Étape {{ workflowStore.progress.stageIndex + 1 }}/{{ workflowStore.progress.totalStages }}
        — {{ workflowStore.progress.status }}
        <template v-if="workflowStore.progress.batchTotalChapters">
          (chapitre {{ (workflowStore.progress.batchChapterIndex ?? 0) + 1 }}/{{ workflowStore.progress.batchTotalChapters }})
        </template>
      </p>
      <p v-if="workflowStore.error" class="error-msg">{{ workflowStore.error }}</p>
    </section>

    <!-- Dialogue d'export -->
    <ExportDialog
      :visible="showExport"
      :chapter-id="selectedChapterId"
      @close="showExport = false"
    />
  </div>

  <!-- Projet introuvable -->
  <div v-else class="empty">
    <NtEmptyState
      icon="📁"
      title="Projet introuvable"
      description="Ce projet n'existe pas ou n'est pas accessible."
      action-label="Retour à l'accueil"
      @action="router.push('/')"
    />
  </div>
</template>

<style scoped>
.project {
  max-width: 1100px;
}

/* En-tête */
.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-back {
  background: var(--bg-tertiary);
  border: none;
  color: var(--text-primary);
  width: 36px;
  height: 36px;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 18px;
}

.btn-back:hover {
  background: var(--accent);
  color: white;
}

.project-header h1 {
  margin: 0;
  font-size: 24px;
  color: var(--text-primary);
}

.project-meta {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.import-status {
  color: var(--success);
  font-size: 13px;
  margin: 0 0 16px;
}

/* Sélecteur de chapitre */
.chapter-selector {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.chapter-selector label {
  font-size: 14px;
  color: var(--text-secondary);
}

.chapter-selector select {
  flex: 1;
  padding: 8px 12px;
  border-radius: var(--border-radius);
  border: 1px solid var(--bg-tertiary);
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

/* Panes source/cible */
.panes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.pane {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 300px;
  max-height: 500px;
}

.pane-header {
  padding: 8px 12px;
  background-color: var(--bg-tertiary);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.pane-content {
  flex: 1;
  overflow: auto;
  padding: 12px;
  margin: 0;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: var(--text-primary);
}

.pane-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

/* Boutons traduction */
.translate-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.btn-primary {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: var(--border-radius);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
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
  border: 1px solid var(--bg-tertiary);
  padding: 12px 20px;
  border-radius: var(--border-radius);
  font-size: 14px;
  cursor: pointer;
}

.btn-secondary:hover {
  background-color: var(--accent);
  color: white;
}

.btn-danger {
  background-color: var(--error);
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: var(--border-radius);
  font-size: 14px;
  cursor: pointer;
}

/* Inspecteur d'agents */
.inspector {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px;
}

.pipeline {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pipeline-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--border-radius);
  background-color: var(--bg-tertiary);
  font-size: 13px;
}

.pipeline-step.completed {
  border-left: 3px solid var(--success);
}

.pipeline-step.running {
  border-left: 3px solid var(--accent);
}

.pipeline-step.failed {
  border-left: 3px solid var(--error);
}

.pipeline-step.pending {
  border-left: 3px solid transparent;
  opacity: 0.6;
}

.step-icon {
  font-size: 16px;
}

.step-label {
  font-weight: 500;
  color: var(--text-primary);
}

.step-index {
  color: var(--text-secondary);
  font-size: 11px;
}

.progress-detail {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.error-msg {
  color: var(--error);
  font-size: 13px;
  margin: 8px 0 0;
  padding: 8px 12px;
  background-color: rgba(239, 68, 68, 0.1);
  border-radius: var(--border-radius);
}

.empty {
  color: var(--text-secondary);
}
</style>
