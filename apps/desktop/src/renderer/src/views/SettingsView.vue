<script setup lang="ts">
import { useSettingsStore } from '../stores/settings'
import { useOllamaStore } from '../stores/ollama'
import { useUpdateStore } from '../stores/update'

const settings = useSettingsStore()
const ollama = useOllamaStore()
const update = useUpdateStore()
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

    <section class="card">
      <h2>Mises a jour</h2>
      <label>
        Canal
        <select v-model="settings.data.updateChannel" @change="update.setChannel(settings.data.updateChannel ?? 'latest')">
          <option value="latest">Stable</option>
          <option value="beta">Beta</option>
          <option value="alpha">Alpha</option>
        </select>
      </label>
      <button class="btn-primary" @click="update.check">Verifier maintenant</button>
      <p v-if="update.available" class="ok">Nouvelle version disponible : {{ update.info?.version }}</p>
      <button v-if="update.available && !update.downloaded" class="btn-primary" @click="update.download">Telecharger</button>
      <button v-if="update.downloaded" class="btn-primary" @click="update.install">Installer et redemarrer</button>
      <p v-if="update.error" class="error">Erreur : {{ update.error }}</p>
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

input,
select {
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
  margin-right: 8px;
}

.ok {
  color: var(--success);
}

.error {
  color: var(--error);
}
</style>


