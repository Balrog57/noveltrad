<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "../stores/project";
import { useWorkflowStore } from "../stores/workflow";
import { useLogsStore } from "../stores/logs";
import NtProgressBar from "../components/ui/NtProgressBar.vue";
import type { Job, Step, WorkflowStage } from "@shared/types/index.js";

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const workflowStore = useWorkflowStore();
const logsStore = useLogsStore();

const projectId = computed(() => route.params.projectId as string);

/** Jobs chargés */
const jobs = ref<Job[]>([]);
/** Job sélectionné pour le détail */
const selectedJobId = ref<string | null>(null);
/** Étape sélectionnée pour le panneau détail */
const selectedStep = ref<Step | null>(null);
/** Logs en temps réel du workflow */
const workflowLogs = ref<string[]>([]);

const selectedJob = computed(() => {
  if (!selectedJobId.value) return null;
  return jobs.value.find((j) => j.id === selectedJobId.value) ?? null;
});

/** Étapes du job sélectionné */
const steps = computed(() => {
  if (!selectedJob.value) return [];
  // Les steps sont mis à jour via le progress event
  return workflowStore.progress &&
    workflowStore.progress.jobId === selectedJobId.value
    ? [workflowStore.progress.step]
    : [];
});

/** Steps stockées localement (mise à jour via progress) */
const localSteps = ref<Step[]>([]);

// Suivre les progress events pour mettre à jour les étapes
watch(
  () => workflowStore.progress,
  (p) => {
    if (!p || !selectedJobId.value) return;
    if (p.jobId !== selectedJobId.value) return;

    const idx = localSteps.value.findIndex((s) => s.id === p.step.id);
    if (idx >= 0) {
      localSteps.value[idx] = { ...p.step };
    } else {
      localSteps.value.push({ ...p.step });
    }
    // Trier par orderIndex
    localSteps.value.sort((a, b) => a.orderIndex - b.orderIndex);

    // Ajouter un log
    const statusIcon = statusIconFor(p.step.status);
    workflowLogs.value.push(
      `[${new Date().toLocaleTimeString("fr-FR")}] ${statusIcon} ${p.step.name} — ${statusLabel(p.step.status)}`,
    );
  },
  { deep: true },
);

/** Charge la liste des jobs du projet */
async function loadJobs(): Promise<void> {
  if (!projectStore.currentProject) return;
  try {
    jobs.value = await workflowStore.list(projectStore.currentProject.path);
  } catch {
    // Erreur silencieuse
  }
}

/** Sélectionne un job */
function selectJob(job: Job): void {
  selectedJobId.value = job.id;
  selectedStep.value = null;
  localSteps.value = [];
  workflowLogs.value = [];

  // Si le job a des steps, les charger via progress
  // On récupère les steps depuis le progress courant
  if (workflowStore.progress && workflowStore.progress.jobId === job.id) {
    localSteps.value = [workflowStore.progress.step];
  }
}

/** Sélectionne une étape pour le panneau détail */
function selectStep(step: Step): void {
  selectedStep.value = step;
}

/** Icône de statut */
function statusIconFor(status: string): string {
  switch (status) {
    case "pending":
      return "\u23F3"; // ⏳
    case "running":
      return "\U0001F504"; // 🔄
    case "completed":
      return "\u2705"; // ✅
    case "failed":
      return "\u274C"; // ❌
    case "skipped":
      return "\u23ED\uFE0F"; // ⏭️
    case "paused":
      return "\u23F8\uFE0F"; // ⏸️
    case "cancelled":
      return "\u26D4\uFE0F"; // ⛔
    default:
      return "\u23F3";
  }
}

/** Label de statut en français */
function statusLabel(status: string): string {
  switch (status) {
    case "pending":
      return "En attente";
    case "running":
      return "En cours";
    case "completed":
      return "Terminé";
    case "failed":
      return "Échoué";
    case "skipped":
      return "Ignoré";
    case "paused":
      return "En pause";
    case "cancelled":
      return "Annulé";
    default:
      return status;
  }
}

/** Label du stage en français */
function stageLabel(stage: WorkflowStage): string {
  const labels: Record<WorkflowStage, string> = {
    split: "D\u00E9coupage",
    pre_translate: "Pr\u00E9-traduction",
    translate: "Traduction IA",
    consistency: "Coh\u00E9rence",
    lexicon: "Lexique",
    grammar: "Grammaire",
    style: "Style",
    polish: "Polish",
    qa: "QA",
    export: "Export",
  };
  return labels[stage] ?? stage;
}

/** Classe CSS pour le statut d'une \u00E9tape */
function stepStatusClass(status: Step["status"]): string {
  switch (status) {
    case "completed":
      return "step--completed";
    case "running":
      return "step--running";
    case "failed":
      return "step--failed";
    case "skipped":
      return "step--skipped";
    default:
      return "";
  }
}

/** Classe CSS pour le statut d'un job */
function jobStatusClass(status: Job["status"]): string {
  switch (status) {
    case "completed":
      return "job--completed";
    case "running":
      return "job--running";
    case "failed":
      return "job--failed";
    case "cancelled":
      return "job--cancelled";
    case "paused":
      return "job--paused";
    default:
      return "";
  }
}

/** Formater la dur\u00E9e en ms */
function formatDuration(ms?: number): string {
  if (ms == null) return "\u2014";
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return `${m}min ${s % 60}s`;
}

/** Formater le timestamp */
function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString("fr-FR");
}

/** Pourcentage de progression du job */
function jobProgress(job: Job): number {
  if (!localSteps.value.length && job.id === selectedJobId.value)
    return job.status === "completed" ? 100 : 0;
  if (job.id !== selectedJobId.value) {
    return job.status === "completed" ? 100 : job.status === "failed" ? -1 : 0;
  }
  const completed = localSteps.value.filter(
    (s) => s.status === "completed",
  ).length;
  return Math.round((completed / Math.max(localSteps.value.length, 1)) * 100);
}

/** Pause le workflow */
async function pauseWorkflow(): Promise<void> {
  if (!selectedJobId.value) return;
  await workflowStore.pause(selectedJobId.value);
  await loadJobs();
}

/** Reprend le workflow */
async function resumeWorkflow(): Promise<void> {
  if (!selectedJobId.value) return;
  await workflowStore.resume(selectedJobId.value);
  await loadJobs();
}

/** Annule le workflow */
async function cancelWorkflow(): Promise<void> {
  if (!selectedJobId.value) return;
  await workflowStore.cancel(selectedJobId.value);
  await loadJobs();
}

/** R\u00E9essaie une \u00E9tape */
async function retryStep(): Promise<void> {
  if (!selectedJobId.value || !selectedStep.value) return;
  await workflowStore.retryStep(selectedJobId.value, selectedStep.value.id);
  await loadJobs();
}

/** R\u00E9essaie \u00E0 partir d'un stage */
async function retryFrom(): Promise<void> {
  if (!selectedJobId.value || !selectedStep.value) return;
  await workflowStore.retryFrom(selectedJobId.value, selectedStep.value.stage);
  await loadJobs();
}

onMounted(() => {
  loadJobs();
});

const unlisten = window.novelTradAPI.on("workflow:progress", () => {
  // Recharger les jobs quand il y a du progr\u00E8s
  loadJobs();
});

onUnmounted(() => {
  unlisten();
});
</script>

<template>
  <div class="workflow-view">
    <header class="workflow-header">
      <h1>Workflow</h1>
      <p class="workflow-subtitle">Visualisation du pipeline de traduction</p>
    </header>

    <div class="workflow-layout">
      <!-- Colonne gauche : liste des jobs -->
      <aside class="jobs-panel">
        <div class="panel-header">
          <h2>Jobs</h2>
          <button class="btn-secondary" @click="loadJobs">Actualiser</button>
        </div>

        <div v-if="jobs.length === 0" class="empty-state">
          <p>Aucun workflow en cours ou termin\u00E9.</p>
          <p class="empty-hint">
            Lancez une traduction depuis le projet pour cr\u00E9er un job.
          </p>
        </div>

        <ul v-else class="jobs-list">
          <li
            v-for="job in jobs"
            :key="job.id"
            class="job-item"
            :class="[
              jobStatusClass(job.status),
              { 'job-item--selected': selectedJobId === job.id },
            ]"
            @click="selectJob(job)"
          >
            <span class="job-icon">{{ statusIconFor(job.status) }}</span>
            <div class="job-info">
              <span class="job-status">{{ statusLabel(job.status) }}</span>
              <span class="job-date">
                {{ new Date(job.createdAt).toLocaleDateString("fr-FR") }}
              </span>
            </div>
            <span v-if="job.chapterId" class="job-chapter">
              Ch. {{ job.chapterId.slice(0, 8) }}
            </span>
          </li>
        </ul>
      </aside>

      <!-- Colonne centrale : pipeline graph -->
      <section class="pipeline-panel">
        <template v-if="selectedJob">
          <div class="pipeline-header">
            <h2>Pipeline</h2>
            <div class="pipeline-actions">
              <button
                v-if="selectedJob.status === 'running'"
                class="btn-secondary"
                @click="pauseWorkflow"
              >
                \u23F8\uFE0F Pause
              </button>
              <button
                v-if="selectedJob.status === 'paused'"
                class="btn-secondary"
                @click="resumeWorkflow"
              >
                \u25B6\uFE0F Reprendre
              </button>
              <button
                v-if="
                  selectedJob.status === 'running' ||
                  selectedJob.status === 'paused'
                "
                class="btn-danger"
                @click="cancelWorkflow"
              >
                \u23F9\uFE0F Annuler
              </button>
              <button
                v-if="selectedStep"
                class="btn-secondary"
                @click="retryStep"
              >
                \U0001F504 R\u00E9essayer \u00E9tape
              </button>
              <button
                v-if="selectedStep"
                class="btn-secondary"
                @click="retryFrom"
              >
                \u23ED\uFE0F R\u00E9essayer depuis
              </button>
            </div>
          </div>

          <!-- Progression globale -->
          <div class="pipeline-progress">
            <NtProgressBar
              :value="jobProgress(selectedJob)"
              :label="`${statusLabel(selectedJob.status)}`"
            />
          </div>

          <!-- Graphique des \u00E9tapes -->
          <div class="steps-graph">
            <div
              v-for="step in localSteps"
              :key="step.id"
              class="step-node"
              :class="[
                stepStatusClass(step.status),
                { 'step-node--selected': selectedStep?.id === step.id },
              ]"
              @click="selectStep(step)"
            >
              <div class="step-icon">
                {{ statusIconFor(step.status) }}
              </div>
              <div class="step-label">
                {{ step.name }}
              </div>
              <div class="step-meta">
                <span class="step-stage">{{ stageLabel(step.stage) }}</span>
                <span v-if="step.durationMs" class="step-duration">
                  {{ formatDuration(step.durationMs) }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="localSteps.length === 0" class="empty-state">
            <p>
              Aucune \u00E9tape disponible. Le workflow sera affich\u00E9 en
              temps r\u00E9el.
            </p>
          </div>
        </template>

        <div v-else class="empty-state">
          <p>S\u00E9lectionnez un job pour afficher le pipeline.</p>
        </div>
      </section>

      <!-- Colonne droite : d\u00E9tail + logs -->
      <aside class="detail-panel">
        <!-- D\u00E9tail de l'\u00E9tape s\u00E9lectionn\u00E9e -->
        <template v-if="selectedStep">
          <div class="step-detail">
            <h3>D\u00E9tails de l'\u00E9tape</h3>
            <dl class="detail-list">
              <dt>Nom</dt>
              <dd>{{ selectedStep.name }}</dd>

              <dt>Agent</dt>
              <dd>{{ selectedStep.agentId }}</dd>

              <dt>Mod\u00E8le</dt>
              <dd>
                {{ selectedStep.inputSnapshot?.model ?? "\u2014" }}
              </dd>

              <dt>Tokens entr\u00E9e</dt>
              <dd>
                {{ selectedStep.tokensIn ?? "\u2014" }}
              </dd>

              <dt>Tokens sortie</dt>
              <dd>
                {{ selectedStep.tokensOut ?? "\u2014" }}
              </dd>

              <dt>Dur\u00E9e</dt>
              <dd>{{ formatDuration(selectedStep.durationMs) }}</dd>

              <dt>Score</dt>
              <dd>
                {{
                  selectedStep.score != null
                    ? `${Math.round(selectedStep.score * 100)}%`
                    : "\u2014"
                }}
              </dd>

              <template v-if="selectedStep.errorMessage">
                <dt class="error-label">Erreur</dt>
                <dd class="error-text">
                  {{ selectedStep.errorMessage }}
                </dd>
              </template>
            </dl>
          </div>
        </template>

        <!-- Logs en temps r\u00E9el -->
        <div class="logs-section">
          <div class="logs-header">
            <h3>Journal</h3>
          </div>
          <div class="logs-container">
            <div v-if="workflowLogs.length === 0" class="logs-empty">
              En attente de logs...
            </div>
            <div v-for="(log, i) in workflowLogs" :key="i" class="log-line">
              {{ log }}
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.workflow-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.workflow-header {
  margin-bottom: 20px;
}

.workflow-header h1 {
  margin: 0;
  font-size: 24px;
  color: var(--text-primary);
}

.workflow-subtitle {
  margin: 4px 0 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.workflow-layout {
  display: grid;
  grid-template-columns: 240px 1fr 320px;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* Panneau jobs */
.jobs-panel {
  display: flex;
  flex-direction: column;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 16px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.panel-header h2 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}

.jobs-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
}

.job-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--border-radius);
  background-color: var(--bg-tertiary);
  cursor: pointer;
  transition: background-color 0.15s;
}

.job-item:hover {
  background-color: var(--bg-primary);
}

.job-item--selected {
  outline: 2px solid var(--accent);
}

.job-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.job-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.job-status {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.job-date {
  font-size: 11px;
  color: var(--text-secondary);
}

.job-chapter {
  font-size: 11px;
  color: var(--text-secondary);
  margin-left: auto;
  white-space: nowrap;
}

.job--completed .job-icon {
  color: var(--success);
}

.job--running .job-icon {
  color: var(--accent);
}

.job--failed .job-icon {
  color: var(--error);
}

.job--cancelled .job-icon {
  color: var(--warning);
}

.job--paused .job-icon {
  color: var(--warning);
}

/* Panneau pipeline */
.pipeline-panel {
  display: flex;
  flex-direction: column;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 16px;
  overflow-y: auto;
}

.pipeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.pipeline-header h2 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}

.pipeline-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pipeline-progress {
  margin-bottom: 16px;
}

.steps-graph {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-node {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--border-radius);
  background-color: var(--bg-tertiary);
  cursor: pointer;
  transition:
    background-color 0.15s,
    outline 0.15s;
}

.step-node:hover {
  background-color: var(--bg-primary);
}

.step-node--selected {
  outline: 2px solid var(--accent);
}

.step-icon {
  font-size: 20px;
  flex-shrink: 0;
  width: 28px;
  text-align: center;
}

.step-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}

.step-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.step-stage {
  font-size: 11px;
  color: var(--text-secondary);
}

.step-duration {
  font-size: 11px;
  color: var(--text-secondary);
}

.step--completed .step-icon {
  color: var(--success);
}

.step--running .step-icon {
  color: var(--accent);
}

.step--failed .step-icon {
  color: var(--error);
}

.step--skipped .step-icon {
  color: var(--text-secondary);
}

/* Panneau d\u00E9tail */
.detail-panel {
  display: flex;
  flex-direction: column;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 16px;
  overflow-y: auto;
  gap: 16px;
}

.step-detail h3 {
  margin: 0 0 12px;
  font-size: 16px;
  color: var(--text-primary);
}

.detail-list {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px 16px;
  margin: 0;
}

.detail-list dt {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.detail-list dd {
  margin: 0;
  font-size: 13px;
  color: var(--text-primary);
  word-break: break-word;
}

.error-label {
  color: var(--error) !important;
}

.error-text {
  color: var(--error) !important;
}

/* Logs */
.logs-section {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.logs-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}

.logs-container {
  flex: 1;
  overflow-y: auto;
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius);
  padding: 12px;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
  max-height: 300px;
}

.logs-empty {
  color: var(--text-secondary);
  font-style: italic;
}

.log-line {
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-all;
}

/* Boutons */
.btn-secondary {
  padding: 6px 12px;
  border-radius: var(--border-radius);
  border: 1px solid var(--bg-tertiary);
  background-color: transparent;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.btn-secondary:hover {
  background-color: var(--bg-tertiary);
}

.btn-danger {
  padding: 6px 12px;
  border-radius: var(--border-radius);
  border: 1px solid var(--error);
  background-color: transparent;
  color: var(--error);
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.btn-danger:hover {
  background-color: var(--error);
  color: #fff;
}

/* \u00C9tat vide */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-state p {
  margin: 0;
}

.empty-hint {
  margin-top: 8px !important;
  font-size: 13px;
}

/* Responsive */
@media (max-width: 1024px) {
  .workflow-layout {
    grid-template-columns: 1fr;
  }

  .jobs-panel,
  .detail-panel {
    max-height: 300px;
  }
}
</style>
