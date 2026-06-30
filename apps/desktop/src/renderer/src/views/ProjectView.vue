<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "../stores/project";
import { useWorkflowStore } from "../stores/workflow";
import { onMounted, ref } from "vue";
import ExportDialog from "../components/export/ExportDialog.vue";

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

onMounted(async () => {
  if (!projectStore.currentProject) {
    await projectStore.loadRecent();
    project.value =
      projectStore.recentProjects.find((p) => p.id === projectId) || null;
  }
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
</script>

<template>
  <div v-if="project" class="project">
    <h1>{{ project.name }}</h1>
    <p class="meta">
      {{ project.sourceLanguage }} → {{ project.targetLanguage }}
    </p>
    <div class="actions">
      <button
        class="btn-primary"
        @click="router.push({ name: 'chapters', params: { projectId } })"
      >
        Voir les chapitres
      </button>
      <button class="btn-primary" @click="importFile">
        Importer un chapitre
      </button>
      <button
        class="btn-primary"
        :disabled="starting || workflowStore.loading"
        @click="translate"
      >
        Traduire le chapitre
      </button>
      <button class="btn-primary" @click="showExport = true">
        Exporter le projet
      </button>
    </div>
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
  max-width: 800px;
}

.meta {
  color: var(--text-secondary);
}

.actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.empty {
  color: var(--text-secondary);
}
</style>
