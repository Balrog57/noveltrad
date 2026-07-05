<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "../stores/project";
import { useEditorStore } from "../stores/editor";
import { useHistoryStore } from "../stores/history";
import NtDiffViewer from "../components/history/NtDiffViewer.vue";
import NtTable from "../components/ui/NtTable.vue";
import type { HistorySnapshot } from "@shared/types/index.js";
import type { Column } from "../components/ui/NtTable.vue";

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const editorStore = useEditorStore();
const historyStore = useHistoryStore();

const projectId = computed(() => route.params.projectId as string);
const chapterId = computed(
  () => (route.params.chapterId as string) || undefined,
);

/** Titre du chapitre (si filtré par chapitre) */
const chapterTitle = computed(() => {
  if (!chapterId.value) {return null;}
  const ch = projectStore.chapters.find((c) => c.id === chapterId.value);
  return ch?.title ?? "Chapitre";
});

// Colonnes du tableau des snapshots
const tableColumns: Column[] = [
  { key: "versionNumber", label: "Version", sortable: true, width: "80px" },
  { key: "createdAt", label: "Date", sortable: true, width: "160px" },
  { key: "stage", label: "Étape", sortable: true, width: "120px" },
  { key: "qualityScore", label: "Score", sortable: true, width: "80px" },
  { key: "triggeredBy", label: "Déclencheur", sortable: true, width: "120px" },
];

// Table rows adaptées pour NtTable
const tableRows = computed(() =>
  historyStore.sortedSnapshots.map((s) => ({
    id: s.id,
    versionNumber: s.versionNumber ?? "?",
    createdAt: formatDate(s.createdAt),
    stage: s.stage,
    qualityScore:
      s.qualityScore != null ? `${Math.round(s.qualityScore * 100)}%` : "—",
    triggeredBy: triggerLabel(s.triggeredBy),
  })),
);

/** Confirmation de rollback complet */
const showConfirmRollback = ref(false);
const snapshotToRollback = ref<HistorySnapshot | null>(null);
const partialRollbackLoading = ref(false);

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function triggerLabel(trigger: string): string {
  switch (trigger) {
    case "workflow":
      return "Workflow";
    case "manual":
      return "Manuel";
    case "rollback":
      return "Rollback";
    default:
      return trigger;
  }
}

/** Sélectionne un snapshot et calcule le diff avec le plus récent */
function selectSnapshot(row: Record<string, unknown>): void {
  const snapshot = historyStore.snapshots.find((s) => s.id === row.id);
  if (!snapshot) {return;}
  historyStore.selectedSnapshot = snapshot;
  // Diff avec le snapshot le plus récent
  const latest = historyStore.sortedSnapshots[0];
  if (latest && latest.id !== snapshot.id) {
    historyStore.loadDiff(snapshot.id, latest.id);
  } else {
    historyStore.diffResult = null;
  }
}

/** Ouvre le dialogue de confirmation de rollback complet */
function confirmRollback(snapshot: HistorySnapshot): void {
  snapshotToRollback.value = snapshot;
  showConfirmRollback.value = true;
}

/** Ouvre le sélecteur de paragraphes pour rollback partiel */
async function openPartialRollback(snapshot: HistorySnapshot): Promise<void> {
  historyStore.selectedSnapshot = snapshot;
  await historyStore.loadSnapshotParagraphs(projectId.value, snapshot.id);
  historyStore.showParagraphSelector = true;
}

/** Exécute le rollback complet */
async function executeRollback(): Promise<void> {
  if (!snapshotToRollback.value && historyStore.selectedSnapshot) {
    snapshotToRollback.value = historyStore.selectedSnapshot;
  }
  if (!snapshotToRollback.value || !chapterId.value) {return;}
  await historyStore.rollback(
    projectId.value,
    chapterId.value,
    snapshotToRollback.value.id,
  );
  showConfirmRollback.value = false;
  snapshotToRollback.value = null;
}

/** Exécute le rollback partiel */
async function executePartialRollback(): Promise<void> {
  if (
    !historyStore.selectedSnapshot ||
    !chapterId.value ||
    historyStore.selectedParagraphIds.size === 0
  )
    {return;}

  partialRollbackLoading.value = true;
  await historyStore.rollbackPartial(
    projectId.value,
    chapterId.value,
    historyStore.selectedSnapshot.id,
    Array.from(historyStore.selectedParagraphIds),
  );
  partialRollbackLoading.value = false;
  historyStore.diffResult = null;
}

/** Crée un snapshot manuel */
async function createManualSnapshot(): Promise<void> {
  if (!chapterId.value) {return;}
  // Charger les paragraphes actuels
  if (editorStore.chapterId !== chapterId.value) {
    await editorStore.loadChapter(chapterId.value);
  }
  await historyStore.createManualSnapshot(
    projectId.value,
    chapterId.value,
    editorStore.paragraphs,
  );
}

function goBack(): void {
  if (chapterId.value) {
    router.push({
      name: "chapter-editor",
      params: { projectId: projectId.value, chapterId: chapterId.value },
    });
  } else {
    router.push({ name: "project", params: { projectId: projectId.value } });
  }
}

onMounted(() => {
  historyStore.loadHistory(projectId.value, chapterId.value);
});

// Recharger si le chapitre change
watch(chapterId, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    historyStore.loadHistory(projectId.value, newVal);
  }
});
</script>

<template>
  <div class="history-view">
    <!-- Barre d'outils -->
    <header class="toolbar">
      <div class="toolbar-left">
        <button class="btn-toolbar" @click="goBack">← Retour</button>
        <h2 class="view-title">
          🕐 Historique
          <template v-if="chapterTitle"> — {{ chapterTitle }}</template>
        </h2>
      </div>
      <div class="toolbar-right">
        <button
          v-if="chapterId"
          class="btn-toolbar btn-primary"
          :disabled="historyStore.loading"
          @click="createManualSnapshot"
        >
          Snapshot manuel
        </button>
      </div>
    </header>

    <!-- État de chargement -->
    <p
      v-if="historyStore.loading && !historyStore.snapshots.length"
      class="status-msg"
    >
      Chargement de l'historique...
    </p>

    <!-- Message d'erreur -->
    <p
      v-else-if="historyStore.error && !historyStore.snapshots.length"
      class="status-msg error"
    >
      {{ historyStore.error }}
    </p>

    <!-- Contenu principal -->
    <div v-else class="history-content">
      <!-- Panneau gauche : liste des versions -->
      <div class="history-list-panel">
        <NtTable
          :columns="tableColumns"
          :rows="tableRows"
          :sortable="true"
          @row-click="selectSnapshot"
        >
          <template #cell-versionNumber="{ row }">
            <span class="version-cell">v{{ row.versionNumber }}</span>
          </template>
          <template #cell-triggeredBy="{ row }">
            <span
              class="trigger-badge"
              :class="{
                'trigger-workflow': row.triggeredBy === 'Workflow',
                'trigger-manual': row.triggeredBy === 'Manuel',
                'trigger-rollback': row.triggeredBy === 'Rollback',
              }"
            >
              {{ row.triggeredBy }}
            </span>
          </template>
          <template #cell-qualityScore="{ row }">
            <span
              v-if="row.qualityScore !== '—'"
              class="score-badge"
              :class="{
                'score-high':
                  Number.parseFloat(row.qualityScore as string) >= 80,
                'score-mid':
                  Number.parseFloat(row.qualityScore as string) >= 50 &&
                  Number.parseFloat(row.qualityScore as string) < 80,
                'score-low': Number.parseFloat(row.qualityScore as string) < 50,
              }"
            >
              {{ row.qualityScore }}
            </span>
            <span v-else class="score-none">—</span>
          </template>
          <template #empty> Aucun snapshot disponible. </template>
        </NtTable>

        <!-- Actions sur le snapshot sélectionné -->
        <div
          v-if="historyStore.selectedSnapshot && chapterId"
          class="snapshot-actions"
        >
          <button
            class="btn-action btn-danger"
            @click="confirmRollback(historyStore.selectedSnapshot)"
          >
            Restaurer cette version
          </button>
          <button
            class="btn-action btn-partial"
            @click="openPartialRollback(historyStore.selectedSnapshot)"
          >
            Restaurer certains paragraphes
          </button>
        </div>
      </div>

      <!-- Panneau droit : diff viewer -->
      <div class="history-diff-panel">
        <NtDiffViewer :diff="historyStore.diffResult" />
      </div>
    </div>

    <!-- Dialogue de confirmation rollback complet -->
    <Teleport to="body">
      <div
        v-if="showConfirmRollback"
        class="modal-overlay"
        @click.self="showConfirmRollback = false"
      >
        <div class="modal-box" role="dialog" aria-modal="true">
          <h3>Confirmer la restauration</h3>
          <p>
            Voulez-vous vraiment restaurer la version
            <strong>v{{ snapshotToRollback?.versionNumber }}</strong>
            {{
              snapshotToRollback
                ? `du ${formatDate(snapshotToRollback.createdAt)}`
                : ""
            }}
            ?
          </p>
          <p class="modal-warning">
            Tous les paragraphes actuels seront remplacés par ceux de cette
            version. Une nouvelle version de rollback sera créée.
          </p>
          <div class="modal-actions">
            <button class="btn-toolbar" @click="showConfirmRollback = false">
              Annuler
            </button>
            <button
              class="btn-toolbar btn-danger"
              :disabled="historyStore.loading"
              @click="executeRollback"
            >
              {{ historyStore.loading ? "Restauration..." : "Restaurer tout" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Dialogue de sélection de paragraphes pour rollback partiel -->
    <Teleport to="body">
      <div
        v-if="historyStore.showParagraphSelector"
        class="modal-overlay"
        @click.self="historyStore.showParagraphSelector = false"
      >
        <div class="modal-box partial-modal" role="dialog" aria-modal="true">
          <h3>Restaurer certains paragraphes</h3>
          <p class="modal-subtitle">
            Sélectionnez les paragraphes à restaurer depuis la version
            <strong>v{{ historyStore.selectedSnapshot?.versionNumber }}</strong>.
          </p>

          <!-- Sélection tout/rien -->
          <div class="partial-toolbar">
            <label class="checkbox-label">
              <input
                type="checkbox"
                :checked="
                  historyStore.selectedParagraphIds.size ===
                    historyStore.snapshotParagraphs.length &&
                    historyStore.snapshotParagraphs.length > 0
                "
                @change="
                  historyStore.toggleAllParagraphs(
                    ($event.target as HTMLInputElement).checked,
                  )
                "
              >
              Tout sélectionner
            </label>
            <span class="partial-count">
              {{ historyStore.selectedParagraphIds.size }} /
              {{ historyStore.snapshotParagraphs.length }} paragraphes
            </span>
          </div>

          <!-- Liste des paragraphes -->
          <div class="paragraph-list">
            <div
              v-for="p in historyStore.snapshotParagraphs"
              :key="p.id"
              class="paragraph-item"
              :class="{ selected: p.selected }"
              @click="historyStore.toggleParagraph(p.id)"
            >
              <input
                type="checkbox"
                :checked="p.selected"
                class="paragraph-checkbox"
                @click.stop
                @change="historyStore.toggleParagraph(p.id)"
              >
              <div class="paragraph-content">
                <span class="paragraph-index">#{{ p.index }}</span>
                <span class="paragraph-text-source">{{ p.sourceText }}</span>
                <span v-if="p.translatedText" class="paragraph-text-target">{{
                  p.translatedText
                }}</span>
              </div>
            </div>
          </div>

          <!-- Aucun paragraphe trouvé -->
          <p
            v-if="historyStore.snapshotParagraphs.length === 0"
            class="empty-msg"
          >
            Aucun paragraphe trouvé dans ce snapshot.
          </p>

          <!-- Actions -->
          <div class="modal-actions">
            <button
              class="btn-toolbar"
              @click="historyStore.showParagraphSelector = false"
            >
              Annuler
            </button>
            <button
              class="btn-toolbar btn-partial"
              :disabled="
                historyStore.selectedParagraphIds.size === 0 ||
                  partialRollbackLoading
              "
              @click="executePartialRollback"
            >
              {{
                partialRollbackLoading
                  ? "Restauration..."
                  : `Restaurer ${historyStore.selectedParagraphIds.size} paragraphe${historyStore.selectedParagraphIds.size > 1 ? "s" : ""}`
              }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.history-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* --- Barre d'outils --- */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--bg-tertiary);
  gap: 16px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.view-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.btn-toolbar {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: none;
  padding: 6px 14px;
  border-radius: var(--border-radius);
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.15s;
}

.btn-toolbar:hover {
  background-color: var(--accent-hover);
}

.btn-toolbar:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: var(--accent);
  color: white;
}

.btn-danger {
  background-color: var(--error);
  color: white;
}

.btn-danger:hover {
  background-color: #d32f2f;
}

.btn-partial {
  background-color: var(--warning);
  color: white;
}

.btn-partial:hover {
  background-color: #e65100;
}

/* --- Contenu --- */
.history-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.history-list-panel {
  width: 380px;
  min-width: 280px;
  border-right: 1px solid var(--bg-tertiary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.history-diff-panel {
  flex: 1;
  overflow: hidden;
}

/* --- Tableau versions --- */
.version-cell {
  font-weight: 700;
  color: var(--accent);
}

.trigger-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
}

.trigger-workflow {
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
}

.trigger-manual {
  background-color: var(--accent);
  color: white;
}

.trigger-rollback {
  background-color: var(--warning);
  color: white;
}

.score-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}

.score-high {
  background-color: rgba(0, 200, 83, 0.15);
  color: var(--success);
}

.score-mid {
  background-color: rgba(255, 193, 7, 0.15);
  color: var(--warning);
}

.score-low {
  background-color: rgba(255, 82, 82, 0.15);
  color: var(--error);
}

.score-none {
  color: var(--text-secondary);
}

/* --- Actions snapshot --- */
.snapshot-actions {
  padding: 12px;
  border-top: 1px solid var(--bg-tertiary);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.btn-action {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border-radius: var(--border-radius);
  border: none;
  font-size: 13px;
  cursor: pointer;
  text-align: center;
}

/* --- Modal confirmation --- */
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 24px;
  max-width: 440px;
  width: 90%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.partial-modal {
  max-width: 640px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-box h3 {
  margin: 0 0 12px;
  color: var(--text-primary);
  font-size: 16px;
}

.modal-box p {
  margin: 0 0 8px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.modal-subtitle {
  margin-bottom: 16px !important;
}

.modal-warning {
  color: var(--warning) !important;
  font-size: 13px !important;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

/* --- Sélecteur de paragraphes --- */
.partial-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--bg-tertiary);
  margin-bottom: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
}

.partial-count {
  font-size: 12px;
  color: var(--text-secondary);
}

.paragraph-list {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
}

.paragraph-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 6px;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background-color 0.1s;
}

.paragraph-item:hover {
  background-color: var(--bg-tertiary);
}

.paragraph-item.selected {
  background-color: rgba(0, 150, 255, 0.1);
  border-left: 3px solid var(--accent);
}

.paragraph-checkbox {
  margin-top: 4px;
  flex-shrink: 0;
}

.paragraph-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.paragraph-index {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
}

.paragraph-text-source {
  font-size: 13px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.paragraph-text-target {
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-msg {
  color: var(--text-secondary);
  text-align: center;
  padding: 24px;
}

/* --- Statuts --- */
.status-msg {
  padding: 24px;
  color: var(--text-secondary);
  text-align: center;
}

.status-msg.error {
  color: var(--error);
}
</style>
