<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "../stores/project";
import { useWorkflowStore } from "../stores/workflow";
import { onMounted, ref, computed } from "vue";
import ExportDialog from "../components/export/ExportDialog.vue";
import NtStatCard from "../components/ui/NtStatCard.vue";

interface OpenDialogResult {
  canceled: boolean;
  filePaths?: string[];
}

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const workflowStore = useWorkflowStore();
const project = ref(projectStore.currentProject);
const starting = ref(false);
const showExport = ref(false);

const projectId = (route.params.projectId as string) || "";

/** Label du dernier statut workflow */
const workflowStatusLabel = computed(() => {
  const s = projectStore.stats?.lastWorkflowStatus;
  if (!s) return "Aucun";
  const labels: Record<string, string> = {
    pending: "En attente",
    running: "En cours",
    paused: "En pause",
    completed: "Termine",
    failed: "Echoue",
    cancelled: "Annule",
  };
  return labels[s] ?? s;
});

/** Couleur du badge statut workflow */
const workflowStatusColor = computed(() => {
  const s = projectStore.stats?.lastWorkflowStatus;
  if (s === "completed") return "var(--success)";
  if (s === "failed") return "var(--error)";
  if (s === "running") return "var(--warning)";
  return "var(--text-secondary)";
});

/** Date de creation formatee */
const createdAtFormatted = computed(() => {
  if (!project.value?.createdAt) return "";
  return new Date(project.value.createdAt).toLocaleDateString("fr-FR");
});

onMounted(async () => {
  if (!projectStore.currentProject) {
    await projectStore.loadRecent();
    project.value =
      projectStore.recentProjects.find((p) => p.id === projectId) || null;
  }
  // Charger les statistiques du projet
  await projectStore.loadStats(projectId);
});

async function importFile() {
  const result = await window.novelTradAPI.invoke<OpenDialogResult>(
    "dialog:open-file",
    {
      filters: [{ name: "Texte", extensions: ["txt", "md"] }],
      properties: ["openFile"],
    },
  );
  if (!result || !result.filePaths?.length) return;
  await window.novelTradAPI.invoke(
    "chapter:import",
    projectId,
    result.filePaths[0],
  );
  router.push({ name: "chapters", params: { projectId } });
}

async function translate() {
  if (!project.value) return;
  starting.value = true;
  try {
    await workflowStore.start(project.value.path);
    router.push({ name: "chapters", params: { projectId } });
  } finally {
    starting.value = false;
  }
}

function openLexique() {
  router.push({ name: "lexicon", params: { projectId } });
}
</script>

<template>
  <div v-if="project" class="project">
    <!-- En-tete du projet -->
    <header class="project-header">
      <h1>{{ project.name }}</h1>
      <p class="project-meta">
        <span class="meta-item">{{ project.sourceLanguage }} → {{ project.targetLanguage }}</span>
        <span v-if="project.author" class="meta-item meta-sep">·</span>
        <span v-if="project.author" class="meta-item">{{ project.author }}</span>
        <span class="meta-item meta-sep">·</span>
        <span class="meta-item">Cree le {{ createdAtFormatted }}</span>
      </p>
    </header>

    <!-- Statistiques (SDD §4.6) -->
    <section v-if="projectStore.stats" class="project-stats">
      <h2 class="section-title">Statistiques</h2>
      <div class="stats-grid">
        <NtStatCard
          icon="📖"
          :value="projectStore.stats.chapterCount"
          label="Chapitres"
          color="var(--accent)"
        />
        <NtStatCard
          icon="📝"
          :value="`${projectStore.stats.translatedParagraphs} / ${projectStore.stats.totalParagraphs}`"
          label="Paragraphes traduits"
          color="var(--success)"
        />
        <NtStatCard
          icon="🔤"
          :value="projectStore.stats.sourceWordCount.toLocaleString('fr-FR')"
          label="Mots source"
          color="var(--accent)"
        />
        <NtStatCard
          icon="🌐"
          :value="projectStore.stats.targetWordCount.toLocaleString('fr-FR')"
          label="Mots traduits"
          color="var(--accent)"
        />
        <NtStatCard
          icon="⭐"
          :value="projectStore.stats.averageQualityScore !== null ? `${projectStore.stats.averageQualityScore}/10` : 'N/A'"
          label="Score qualite"
          color="var(--warning)"
        />
        <NtStatCard
          icon="⚙️"
          :value="workflowStatusLabel"
          label="Dernier workflow"
          :color="workflowStatusColor"
        />
      </div>
    </section>

    <!-- Actions rapides -->
    <section class="project-actions">
      <h2 class="section-title">Actions</h2>
      <div class="actions-grid">
        <button
          class="btn-action"
          :disabled="starting || workflowStore.loading"
          @click="translate"
        >
          <span class="btn-icon">▶</span>
          <span class="btn-label">Traduire le chapitre</span>
        </button>
        <button class="btn-action" @click="openLexique">
          <span class="btn-icon">📚</span>
          <span class="btn-label">Ouvrir le lexique</span>
        </button>
        <button class="btn-action" @click="importFile">
          <span class="btn-icon">📥</span>
          <span class="btn-label">Importer un chapitre</span>
        </button>
        <button class="btn-action" @click="showExport = true">
          <span class="btn-icon">📤</span>
          <span class="btn-label">Exporter le projet</span>
        </button>
      </div>
    </section>

    <!-- Navigation rapide -->
    <section class="project-nav">
      <button
        class="btn-link"
        @click="router.push({ name: 'chapters', params: { projectId } })"
      >
        Voir les chapitres →
      </button>
    </section>
  </div>
  <p v-else class="empty">Chargement du projet...</p>

  <!-- Dialogue d'export -->
  <ExportDialog
    :visible="showExport"
    :chapter-id="null"
    @close="showExport = false"
  />
</template>

<style scoped>
.project {
  max-width: 900px;
}

.project-header {
  margin-bottom: 32px;
}

.project-header h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  color: var(--text-primary);
}

.project-meta {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 14px;
}

.meta-sep {
  opacity: 0.4;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

/* Statistiques */
.project-stats {
  margin-bottom: 32px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}

/* Actions rapides */
.project-actions {
  margin-bottom: 32px;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.btn-action {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background-color: var(--bg-secondary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.15s, border-color 0.15s;
  text-align: left;
}

.btn-action:hover:not(:disabled) {
  background-color: var(--bg-tertiary);
  border-color: var(--accent);
}

.btn-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 18px;
  line-height: 1;
  flex-shrink: 0;
}

.btn-label {
  font-weight: 500;
}

/* Navigation */
.project-nav {
  margin-top: 8px;
}

.btn-link {
  background: none;
  border: none;
  color: var(--accent);
  font-size: 14px;
  cursor: pointer;
  padding: 0;
}

.btn-link:hover {
  color: var(--accent-hover);
  text-decoration: underline;
}

.empty {
  color: var(--text-secondary);
}
</style>
