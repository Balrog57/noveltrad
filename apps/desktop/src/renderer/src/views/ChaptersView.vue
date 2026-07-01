<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { ref, onMounted, onUnmounted } from "vue";
import { useProjectStore } from "../stores/project";
import { useWorkflowStore } from "../stores/workflow";
import ExportDialog from "../components/export/ExportDialog.vue";
import NtBadge from "../components/ui/NtBadge.vue";
import NtEmptyState from "../components/ui/NtEmptyState.vue";
import NtTooltip from "../components/ui/NtTooltip.vue";
import type { Chapter } from "@shared/types/index.js";

const tmxImporting = ref(false);
const tmxExporting = ref(false);
const batchTranslating = ref(false);

// Rafraîchissement source (SDD §5.8)
const refreshingId = ref<string | null>(null);
const refreshMessage = ref<string | null>(null);
const refreshMessageType = ref<"success" | "error">("success");
const showRefreshDialog = ref(false);
const refreshChapterId = ref<string | null>(null);
const refreshStrategy = ref<"replace" | "merge" | "new-version">("replace");

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const workflowStore = useWorkflowStore();
const chapters = ref<Chapter[]>([]);
const translatingId = ref<string | null>(null);
const exportChapterId = ref<string | null>(null);

// Drag-and-drop (SDD §5.9)
const isDragging = ref(false);
const importProgress = ref(false);
const importMessage = ref<string | null>(null);
const importMessageType = ref<"success" | "error">("success");
let dragCounter = 0;
let messageTimer: ReturnType<typeof setTimeout> | null = null;

const projectId = (route.params.projectId as string) || "";

onMounted(async () => {
  chapters.value = await window.novelTradAPI.invoke("chapter:list", projectId);
  projectStore.chapters = chapters.value;
});

/** Naviguer vers l'éditeur pour un chapitre */
function openEditor(chapter: Chapter): void {
  router.push({
    name: "chapter-editor",
    params: { projectId, chapterId: chapter.id },
  });
}

async function translateChapter(chapter: Chapter) {
  if (!projectId) return;
  const projectPath = await window.novelTradAPI.invoke<string>(
    "project:path",
    projectId,
  );
  translatingId.value = chapter.id;
  try {
    await workflowStore.start(projectPath, chapter.id);
  } finally {
    translatingId.value = null;
  }
}

function progressFor(chapterId: string): string {
  const p = workflowStore.progress;
  if (!p) return "";
  const batchPrefix =
    p.batchTotalChapters && p.batchChapterIndex !== undefined
      ? `[${p.batchChapterIndex + 1}/${p.batchTotalChapters}] `
      : "";
  if (p.chapterId === chapterId) {
    return `${batchPrefix}${p.step.name} (${p.step.orderIndex + 1}/${p.totalSteps})`;
  }
  return batchPrefix || "";
}

async function batchTranslate(): Promise<void> {
  const projectPath = await window.novelTradAPI.invoke<string>(
    "project:path",
    projectId,
  );
  // SDD §7.9 : utiliser la sélection si des chapitres sont sélectionnés, sinon tous
  const ids =
    workflowStore.selectedChapterIds.length > 0
      ? workflowStore.selectedChapterIds
      : chapters.value.map((c) => c.id);
  batchTranslating.value = true;
  try {
    await workflowStore.startBatch(projectPath, ids);
  } finally {
    batchTranslating.value = false;
  }
}

/** SDD §7.9 : traduire uniquement les chapitres sélectionnés */
async function batchTranslateSelection(): Promise<void> {
  if (workflowStore.selectedChapterIds.length === 0) return;
  const projectPath = await window.novelTradAPI.invoke<string>(
    "project:path",
    projectId,
  );
  batchTranslating.value = true;
  try {
    await workflowStore.startBatch(projectPath, [
      ...workflowStore.selectedChapterIds,
    ]);
  } finally {
    batchTranslating.value = false;
  }
}

/** SDD §7.9 : bascule la sélection d'un chapitre */
function toggleSelection(chapterId: string): void {
  workflowStore.toggleChapterSelection(chapterId);
}

/** SDD §7.9 : sélectionner/désélectionner tous les chapitres */
function toggleSelectAll(): void {
  if (workflowStore.selectedChapterIds.length === chapters.value.length) {
    workflowStore.clearSelection();
  } else {
    workflowStore.selectAll(chapters.value.map((c) => c.id));
  }
}

// --- Drag-and-drop handlers (SDD §5.9) ---

function onDragEnter(e: DragEvent): void {
  e.preventDefault();
  dragCounter++;
  isDragging.value = true;
}

function onDragOver(e: DragEvent): void {
  e.preventDefault();
  e.dataTransfer!.dropEffect = "copy";
}

function onDragLeave(e: DragEvent): void {
  e.preventDefault();
  dragCounter--;
  if (dragCounter <= 0) {
    isDragging.value = false;
    dragCounter = 0;
  }
}

function onDrop(e: DragEvent): void {
  e.preventDefault();
  isDragging.value = false;
  dragCounter = 0;

  const files = e.dataTransfer?.files;
  if (!files || files.length === 0) return;

  // Extraire les chemins natifs (Electron expose .path sur File)
  const filePaths: string[] = [];
  for (let i = 0; i < files.length; i++) {
    const file = files[i]!;
    const filePath = (file as unknown as { path?: string }).path;
    if (filePath) {
      filePaths.push(filePath);
    }
  }

  if (filePaths.length === 0) {
    showImportMessage("Aucun fichier valide detecte.", "error");
    return;
  }

  importFiles(filePaths);
}

async function importFiles(filePaths: string[]): Promise<void> {
  importProgress.value = true;
  importMessage.value = null;

  try {
    const results = await window.novelTradAPI.invoke<
      Array<{
        filePath: string;
        success: boolean;
        chapters?: Chapter[];
        error?: string;
      }>
    >("source:import-files", { projectId, filePaths });

    const successes = results.filter((r) => r.success);
    const failures = results.filter((r) => !r.success);

    if (successes.length > 0) {
      const totalChapters = successes.reduce(
        (sum, r) => sum + (r.chapters?.length ?? 0),
        0,
      );
      showImportMessage(
        `${totalChapters} chapitre${totalChapters > 1 ? "s" : ""} importe${totalChapters > 1 ? "s" : ""} avec succes.`,
        "success",
      );
    }

    if (failures.length > 0) {
      const errorMessages = failures.map(
        (r) => `${r.filePath.split(/[/\\]/).pop()}: ${r.error}`,
      );
      showImportMessage(
        `${failures.length} echec${failures.length > 1 ? "s" : ""} : ${errorMessages.join("; ")}`,
        "error",
      );
    }

    // Recharger la liste des chapitres
    chapters.value = await window.novelTradAPI.invoke(
      "chapter:list",
      projectId,
    );
    projectStore.chapters = chapters.value;
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Erreur lors de l'import";
    showImportMessage(message, "error");
  } finally {
    importProgress.value = false;
  }
}

function showImportMessage(message: string, type: "success" | "error"): void {
  if (messageTimer) {
    clearTimeout(messageTimer);
    messageTimer = null;
  }
  importMessage.value = message;
  importMessageType.value = type;
  // Auto-masquer après 6 secondes pour les succès
  if (type === "success") {
    messageTimer = setTimeout(() => {
      importMessage.value = null;
    }, 6000);
  }
}

function badgeVariant(
  status: string,
): "default" | "success" | "warning" | "error" | "info" {
  const map: Record<
    string,
    "default" | "success" | "warning" | "error" | "info"
  > = {
    completed: "success",
    processing: "warning",
    error: "error",
    pending: "default",
  };
  return map[status] ?? "default";
}

/** Ouvre le dialogue natif de sélection de fichiers pour l'import */
async function openImportDialog(): Promise<void> {
  const result = await window.novelTradAPI.invoke<{
    canceled: boolean;
    filePaths: string[];
  }>("dialog:open-file", {
    title: "Importer des fichiers source",
    filters: [
      { name: "Texte", extensions: ["txt", "md"] },
      { name: "Word", extensions: ["docx"] },
      { name: "EPUB", extensions: ["epub"] },
      { name: "Tous les fichiers", extensions: ["*"] },
    ],
    properties: ["openFile", "multiSelections"],
  });

  if (!result.canceled && result.filePaths.length > 0) {
    importFiles(result.filePaths);
  }
}

async function importTmx(): Promise<void> {
  const result = await window.novelTradAPI.invoke<{
    canceled: boolean;
    filePaths: string[];
  }>("dialog:open-file", {
    title: "Importer un fichier TMX",
    filters: [
      { name: "TMX", extensions: ["tmx"] },
      { name: "Tous les fichiers", extensions: ["*"] },
    ],
    properties: ["openFile"],
  });

  if (result.canceled || result.filePaths.length === 0) return;

  tmxImporting.value = true;
  try {
    const res = await window.novelTradAPI.invoke<{
      success: boolean;
      importedCount: number;
    }>("tm:import", { projectId, filePath: result.filePaths[0] });
    if (res.success) {
      showImportMessage(
        `${res.importedCount} entrée(s) TMX importée(s).`,
        "success",
      );
    }
  } catch (err) {
    const msg =
      err instanceof Error ? err.message : "Erreur lors de l'import TMX";
    showImportMessage(msg, "error");
  } finally {
    tmxImporting.value = false;
  }
}

async function exportTmx(): Promise<void> {
  const result = await window.novelTradAPI.invoke<{
    canceled: boolean;
    filePath: string | null;
  }>("dialog:save-file", {
    title: "Exporter la mémoire de traduction",
    defaultPath: "memory.tmx",
    filters: [{ name: "TMX", extensions: ["tmx"] }],
  });

  if (result.canceled || !result.filePath) return;

  tmxExporting.value = true;
  try {
    await window.novelTradAPI.invoke("tm:export", {
      projectId,
      filePath: result.filePath,
    });
    showImportMessage("Mémoire de traduction exportée.", "success");
  } catch (err) {
    const msg =
      err instanceof Error ? err.message : "Erreur lors de l'export TMX";
    showImportMessage(msg, "error");
  } finally {
    tmxExporting.value = false;
  }
}

/** Ouvre le dialogue de rafraîchissement source (SDD §5.8) */
function openRefreshDialog(chapterId: string): void {
  refreshChapterId.value = chapterId;
  refreshStrategy.value = "replace";
  refreshMessage.value = null;
  showRefreshDialog.value = true;
}

/** Rafraîchit un chapitre depuis son fichier source (SDD §5.8) */
async function confirmRefresh(): Promise<void> {
  if (!refreshChapterId.value) return;
  refreshingId.value = refreshChapterId.value;
  refreshMessage.value = null;
  showRefreshDialog.value = false;
  try {
    const updated = await window.novelTradAPI.invoke(
      "project:refresh-source",
      {
        projectId,
        chapterId: refreshChapterId.value,
        strategy: refreshStrategy.value,
      },
    );
    // Mettre à jour la liste des chapitres
    const idx = chapters.value.findIndex((c) => c.id === refreshChapterId.value);
    if (idx !== -1 && updated) {
      chapters.value[idx] = { ...chapters.value[idx], ...updated };
    }
    refreshMessage.value = "Chapitre rafraîchi avec succès.";
    refreshMessageType.value = "success";
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Erreur lors du rafraîchissement";
    refreshMessage.value = msg;
    refreshMessageType.value = "error";
  } finally {
    refreshingId.value = null;
    refreshChapterId.value = null;
  }
  // Auto-masquer le message après 6 secondes
  setTimeout(() => { refreshMessage.value = null; }, 6000);
}

// Nettoyage des timers à l'unmount
onUnmounted(() => {
  if (messageTimer) {
    clearTimeout(messageTimer);
  }
  importMessage.value = null;
});
</script>

<template>
  <div
    class="chapters-container"
    @dragenter="onDragEnter"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <h1>Chapitres</h1>

    <!-- Zone de drop (SDD §5.9) -->
    <div class="drop-zone" :class="{ dragging: isDragging }">
      <div v-if="isDragging" class="drop-overlay">
        <span class="drop-icon">&#x1F4C4;</span>
        <span class="drop-text">Deposez vos fichiers ici</span>
        <span class="drop-formats"
          >Formats supportes : TXT, MD, DOCX, EPUB</span
        >
      </div>
      <div v-else class="drop-hint">
        <span
          >Glissez-deposez des fichiers (TXT, MD, DOCX, EPUB) pour les
          importer</span
        >
      </div>
    </div>

    <!-- Barre de progression import -->
    <div v-if="importProgress" class="import-progress">
      <span class="spinner"></span>
      <span>Import en cours...</span>
    </div>

    <!-- Message d'import -->
    <div
      v-if="importMessage"
      class="import-message"
      :class="importMessageType"
      role="alert"
    >
      {{ importMessage }}
    </div>

    <!-- Import button (backup for drag-and-drop) -->
    <div class="import-actions">
      <button class="btn-import" @click="openImportDialog">
        + Importer des fichiers
      </button>
      <NtTooltip text="Importer un fichier TMX (mémoire de traduction)">
        <button class="btn-import" :disabled="tmxImporting" @click="importTmx">
          Importer TMX
        </button>
      </NtTooltip>
      <NtTooltip text="Exporter la mémoire de traduction au format TMX">
        <button class="btn-import" :disabled="tmxExporting" @click="exportTmx">
          Exporter TMX
        </button>
      </NtTooltip>
    </div>

    <NtEmptyState
      v-if="!chapters.length && !importProgress"
      icon="📖"
      title="Aucun chapitre"
      description="Importez un fichier TXT, MD, DOCX ou EPUB pour commencer."
      action-label="Importer un fichier"
      @action="openImportDialog"
    />
    <div v-if="chapters.length > 1" class="batch-actions">
      <NtTooltip text="Sélectionner ou désélectionner tous les chapitres">
        <label class="select-all-label">
          <input
            type="checkbox"
            :checked="
              workflowStore.selectedChapterIds.length === chapters.length &&
              chapters.length > 0
            "
            @change="toggleSelectAll"
          />
          <span>Tout sélectionner</span>
        </label>
      </NtTooltip>
      <NtTooltip
        :text="
          workflowStore.selectedChapterIds.length > 0
            ? `Traduire les ${workflowStore.selectedChapterIds.length} chapitre(s) sélectionné(s)`
            : 'Lancer la traduction de tous les chapitres en séquence'
        "
      >
        <button
          class="btn-primary"
          :disabled="batchTranslating || workflowStore.loading"
          @click="batchTranslate"
        >
          {{
            workflowStore.selectedChapterIds.length > 0
              ? `Traduire la sélection (${workflowStore.selectedChapterIds.length})`
              : "Tout traduire"
          }}
        </button>
      </NtTooltip>
    </div>
    <ul class="chapter-list">
      <li v-for="ch in chapters" :key="ch.id" class="chapter-item">
        <div class="chapter-select">
          <input
            type="checkbox"
            :checked="workflowStore.isSelected(ch.id)"
            @change="toggleSelection(ch.id)"
          />
        </div>
        <div
          class="chapter-info"
          @click="openEditor(ch)"
          role="button"
          tabindex="0"
          @keydown.enter="openEditor(ch)"
        >
          <strong>{{ ch.title || ch.id }}</strong>
          <NtBadge :variant="badgeVariant(ch.status)">{{ ch.status }}</NtBadge>
        </div>
        <div class="chapter-actions">
          <NtTooltip text="Lancer la traduction">
            <button
              class="btn-primary"
              :disabled="translatingId === ch.id || workflowStore.loading"
              @click="translateChapter(ch)"
            >
              Traduire
            </button>
          </NtTooltip>
          <NtTooltip text="Exporter ce chapitre">
            <button class="btn-primary" @click="exportChapterId = ch.id">
              Exporter
            </button>
          </NtTooltip>
          <NtTooltip text="Rafraîchir depuis le fichier source">
            <button
              class="btn-refresh"
              :disabled="refreshingId === ch.id"
              @click="openRefreshDialog(ch.id)"
            >
              Rafraîchir
            </button>
          </NtTooltip>
          <span v-if="progressFor(ch.id)" class="progress">{{
            progressFor(ch.id)
          }}</span>
        </div>
      </li>
    </ul>

    <!-- Message de rafraîchissement -->
    <div
      v-if="refreshMessage"
      class="import-message"
      :class="refreshMessageType"
      role="alert"
    >
      {{ refreshMessage }}
    </div>

    <!-- Dialogue de confirmation rafraîchissement (SDD §5.8) -->
    <div v-if="showRefreshDialog" class="modal-overlay" @click.self="showRefreshDialog = false">
      <div class="modal-card">
        <h3>Rafraîchir depuis le fichier source</h3>
        <p>Le fichier source original a été modifié. Comment souhaitez-vous appliquer les changements ?</p>
        <label class="radio-label">
          <input type="radio" v-model="refreshStrategy" value="replace" />
          <span><strong>Remplacer</strong> — écraser les paragraphes existants</span>
        </label>
        <label class="radio-label">
          <input type="radio" v-model="refreshStrategy" value="merge" />
          <span><strong>Fusionner</strong> — ajouter uniquement les nouveaux paragraphes</span>
        </label>
        <label class="radio-label">
          <input type="radio" v-model="refreshStrategy" value="new-version" />
          <span><strong>Nouvelle version</strong> — créer un chapitre distinct</span>
        </label>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showRefreshDialog = false">Annuler</button>
          <button class="btn-primary" @click="confirmRefresh">Confirmer</button>
        </div>
      </div>
    </div>

    <!-- Dialogue d'export -->
    <ExportDialog
      :visible="exportChapterId !== null"
      :chapter-id="exportChapterId"
      :selected-chapter-ids="workflowStore.selectedChapterIds"
      @close="exportChapterId = null"
    />
  </div>
</template>

<style scoped>
.empty {
  color: var(--text-secondary);
}

.chapter-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chapter-item {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.chapter-select {
  display: flex;
  align-items: center;
}

.chapter-select input[type="checkbox"] {
  accent-color: var(--accent);
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.chapter-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
  flex: 1;
}

.chapter-info:hover strong {
  color: var(--accent);
}

.chapter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Batch actions bar */
.batch-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
  padding: 12px 16px;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
}

.select-all-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
}

.select-all-label input[type="checkbox"] {
  accent-color: var(--accent);
  width: 18px;
  height: 18px;
}

.badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background-color: var(--bg-tertiary);
  text-transform: uppercase;
}

.badge.completed {
  background-color: var(--success);
  color: white;
}

.progress {
  color: var(--text-secondary);
  font-size: 13px;
}

.btn-primary {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: var(--border-radius);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Drag-and-drop zone */
.drop-zone {
  border: 2px dashed var(--border-color, var(--bg-tertiary));
  border-radius: var(--border-radius);
  padding: 24px;
  text-align: center;
  margin-bottom: 16px;
  transition:
    border-color 0.2s,
    background-color 0.2s;
}

.drop-zone.dragging {
  border-color: var(--accent);
  background-color: var(--bg-accent, var(--accent));
  opacity: 0.15;
}

.drop-hint {
  color: var(--text-secondary);
  font-size: 14px;
}

.drop-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.drop-icon {
  font-size: 32px;
}

.drop-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent);
}

.drop-formats {
  font-size: 12px;
  color: var(--text-secondary);
}

/* Import progress */
.import-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  margin-bottom: 12px;
  color: var(--accent);
  font-size: 14px;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--bg-tertiary);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Import message */
.import-message {
  padding: 10px 16px;
  border-radius: var(--border-radius);
  margin-bottom: 12px;
  font-size: 14px;
}

.import-message.success {
  background-color: var(--success);
  color: white;
}

.import-message.error {
  background-color: var(--error);
  color: white;
}

/* Import actions */
.import-actions {
  margin-bottom: 12px;
}

.btn-import {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color, var(--bg-tertiary));
  padding: 8px 16px;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 14px;
}

.btn-import:hover {
  background-color: var(--bg-tertiary);
}

.btn-refresh {
  background-color: transparent;
  color: var(--accent);
  border: 1px solid var(--accent);
  padding: 6px 12px;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 13px;
}

.btn-refresh:hover {
  background-color: var(--accent);
  color: white;
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal overlay */
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background-color: var(--bg-primary);
  border-radius: var(--border-radius);
  padding: 24px;
  max-width: 480px;
  width: 90%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.modal-card h3 {
  margin: 0 0 12px;
  font-size: 18px;
  color: var(--text-primary);
}

.modal-card p {
  margin: 0 0 16px;
  color: var(--text-secondary);
  font-size: 14px;
}

.radio-label {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 12px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-primary);
}

.radio-label input[type="radio"] {
  margin-top: 2px;
  accent-color: var(--accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.btn-cancel {
  background-color: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--bg-tertiary);
  padding: 8px 16px;
  border-radius: var(--border-radius);
  cursor: pointer;
}
</style>
