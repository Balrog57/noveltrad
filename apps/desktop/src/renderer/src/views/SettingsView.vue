<script setup lang="ts">
import { useSettingsStore } from '../stores/settings'
import { useOllamaStore } from '../stores/ollama'

const settings = useSettingsStore()
const ollama = useOllamaStore()
</script>

<template>
  <div class="settings">
    <h1>Parametres</h1>
    
    <section class="card">
      <h2>Ollama</h2>
      <label>
        Hote Ollama
        <input v-model="settings.data.ollamaHost" />
      </label>
      <button class="btn-primary" @click="ollama.check(settings.data.ollamaHost)">Tester</button>
      <p :class="{ ok: ollama.available }">
        {{ ollama.available ? 'Connecte' : 'Non disponible' }}
      </p>
      <ul v-if="ollama.models.length">
        <li v-for="m in ollama.models" :key="m.name">{{ m.name }}</li>
      </ul>
    </section>

    <section class="card">
      <h2>Langues par defaut</h2>
      <label>
        Source
        <input v-model="settings.data.sourceLanguage" />
      </label>
      <label>
        Cible
        <input v-model="settings.data.targetLanguage" />
      </label>
    </section>
  </div>
</template>

<style scoped>
.settings {
  max-width: 600px;
}

.card {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 20px;
  margin-bottom: 20px;
}

.card h2 {
  margin-top: 0;
  font-size: 16px;
}

label {
  display: block;
  margin-bottom: 12px;
}

input {
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
  padding: 8px 16px;
  border-radius: var(--border-radius);
}

.ok {
  color: var(--success);
}
</style>

