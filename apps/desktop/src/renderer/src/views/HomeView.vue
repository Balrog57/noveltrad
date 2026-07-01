<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { useOllamaStore } from '../stores/ollama'

const router = useRouter()
const projectStore = useProjectStore()
const ollamaStore = useOllamaStore()

const showCreate = ref(false)
const newProject = ref({ name: '', sourceLanguage: 'zh', targetLanguage: 'fr', parentPath: '~/NovelTrad Projects' })

onMounted(async () => {
  await projectStore.loadRecent()
  await ollamaStore.check()
})

async function create() {
  const project = await projectStore.create(newProject.value)
  router.push({ name: 'project', params: { id: project.id } })
}

async function open(path: string) {
  const project = await projectStore.open(path)
  router.push({ name: 'project', params: { id: project.id } })
}
</script>

<template>
  <div class="home">
    <header class="hero">
      <h1>NovelTrad 2.0</h1>
      <p>Moteur de traduction de romans assiste par IA multi-agent.</p>
      <div class="ollama-status" :class="{ ok: ollamaStore.available }">
        {{ ollamaStore.available ? '✅ Ollama disponible' : '❌ Ollama non detecte' }}
      </div>
    </header>

    <section class="actions">
      <button class="btn-primary" @click="showCreate = true">+ Nouveau projet</button>
    </section>

    <section v-if="showCreate" class="card">
      <h2>Nouveau projet</h2>
      <label>
        Nom
        <input v-model="newProject.name" placeholder="Mon roman" />
      </label>
      <label>
        Langue source
        <select v-model="newProject.sourceLanguage">
          <option value="zh">Chinois</option>
          <option value="ja">Japonais</option>
          <option value="ko">Coreen</option>
          <option value="en">Anglais</option>
        </select>
      </label>
      <label>
        Langue cible
        <select v-model="newProject.targetLanguage">
          <option value="fr">Francais</option>
          <option value="en">Anglais</option>
        </select>
      </label>
      <button class="btn-primary" :disabled="!newProject.name || projectStore.loading" @click="create">
        Creer
      </button>
    </section>

    <section class="card">
      <h2>Projets recents</h2>
      <ul v-if="projectStore.recentProjects.length" style="list-style: none; padding: 0;">
        <li
          v-for="p in projectStore.recentProjects"
          :key="p.id"
          class="project-item"
          role="button"
          tabindex="0"
          :aria-label="`Ouvrir le projet ${p.name}`"
          @click="open(p.path)"
          @keydown.enter="open(p.path)"
          @keydown.space.prevent="open(p.path)"
        >
          <strong>{{ p.name }}</strong>
          <span class="meta">{{ p.sourceLanguage }} → {{ p.targetLanguage }}</span>
        </li>
      </ul>
      <p v-else class="empty">Aucun projet recent.</p>
    </section>
  </div>
</template>

<style scoped>
.home {
  max-width: 800px;
  margin: 0 auto;
}

.hero {
  text-align: center;
  margin-bottom: 32px;
}

.hero h1 {
  margin: 0;
  font-size: 32px;
  color: var(--accent);
}

.ollama-status {
  margin-top: 12px;
  padding: 8px 16px;
  border-radius: var(--border-radius);
  background-color: var(--bg-tertiary);
  display: inline-block;
}

.ollama-status.ok {
  color: var(--success);
}

.actions {
  margin-bottom: 24px;
}

.card {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 20px;
  margin-bottom: 24px;
}

.card h2 {
  margin-top: 0;
  font-size: 18px;
}

label {
  display: block;
  margin-bottom: 12px;
}

input, select {
  display: block;
  width: 100%;
  margin-top: 4px;
  padding: 8px 12px;
  border-radius: var(--border-radius);
  border: 1px solid var(--bg-tertiary);
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-primary {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: var(--border-radius);
}

.btn-primary:hover {
  background-color: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.project-item {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  border-radius: var(--border-radius);
  cursor: pointer;
}

.project-item:hover {
  background-color: var(--bg-tertiary);
}

.meta {
  color: var(--text-secondary);
  font-size: 13px;
}

.empty {
  color: var(--text-secondary);
}
</style>
