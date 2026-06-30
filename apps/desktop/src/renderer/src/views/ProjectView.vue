<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { onMounted, ref } from 'vue'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const project = ref(projectStore.currentProject)

onMounted(async () => {
  if (!projectStore.currentProject) {
    await projectStore.loadRecent()
    project.value = projectStore.recentProjects.find((p) => p.id === route.params.id) || null
  }
})

async function importFile() {
  const result = await window.novelTradAPI.invoke('dialog:open-file', {
    filters: [{ name: 'Texte', extensions: ['txt', 'md'] }],
    properties: ['openFile']
  })
  if (!result || !result.filePaths?.length) return
  await window.novelTradAPI.invoke('chapter:import', route.params.id, result.filePaths[0])
  router.push({ name: 'chapters', params: { id: route.params.id } })
}
</script>

<template>
  <div v-if="project" class="project">
    <h1>{{ project.name }}</h1>
    <p class="meta">{{ project.sourceLanguage }} → {{ project.targetLanguage }}</p>
    <div class="actions">
      <button class="btn-primary" @click="router.push({ name: 'chapters', params: { id: route.params.id } })">
        Voir les chapitres
      </button>
      <button class="btn-primary" @click="importFile">
        Importer un chapitre
      </button>
    </div>
  </div>
  <p v-else class="empty">Chargement du projet...</p>
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
}

.empty {
  color: var(--text-secondary);
}
</style>
