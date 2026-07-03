<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useProjectStore } from "../stores/project";
import { useOllamaStore } from "../stores/ollama";

const router = useRouter();
const projectStore = useProjectStore();
const ollamaStore = useOllamaStore();

const showCreate = ref(false);
const creationError = ref<string | null>(null);

// Suppression de projet (SDD §5.11)
const showDeleteDialog = ref(false);
const deleteProjectId = ref<string | null>(null);
const deleteProjectName = ref("");
const deleteRemoveFiles = ref(false);
const deleteError = ref<string | null>(null);
const newProject = ref({
  name: "",
  sourceLanguage: "zh",
  targetLanguage: "fr",
  parentPath: "~/NovelTrad Projects",
});

// Mise à jour
const updateAvailable = ref(false);
const updateVersion = ref("");
const updateChecking = ref(false);
const updateDownloading = ref(false);
const updateDownloaded = ref(false);

function checkUpdate(): void {
  updateChecking.value = true;
  window.novelTradAPI.invoke("update:check").catch(() => {});
  setTimeout(() => { updateChecking.value = false; }, 3000);
}

function downloadUpdate(): void {
  updateDownloading.value = true;
  window.novelTradAPI.invoke("update:download").catch(() => {});
}

function installUpdate(): void {
  window.novelTradAPI.invoke("update:install").catch(() => {});
}

// Écoute les événements de mise à jour du main process
onMounted(async () => {
  await projectStore.loadRecent();
  await ollamaStore.check();

  window.novelTradAPI.on("update:available", (info: any) => {
    updateAvailable.value = true;
    updateVersion.value = info?.version ?? "";
  });
  window.novelTradAPI.on("update:downloaded", () => {
    updateDownloading.value = false;
    updateDownloaded.value = true;
  });
  window.novelTradAPI.on("update:error", () => {
    updateChecking.value = false;
    updateDownloading.value = false;
  });
});

async function create() {
  creationError.value = null;
  try {
    const project = await projectStore.create(newProject.value);
    router.push({ name: "project", params: { projectId: project.id } });
  } catch (err) {
    creationError.value = err instanceof Error ? err.message : "Erreur inconnue";
  }
}

async function open(path: string) {
  const project = await projectStore.open(path);
  router.push({ name: "project", params: { projectId: project.id } });
}

/** Ouvre le dialogue de confirmation de suppression (SDD §5.11) */
function openDeleteDialog(projectId: string, projectName: string): void {
  deleteProjectId.value = projectId;
  deleteProjectName.value = projectName;
  deleteRemoveFiles.value = false;
  deleteError.value = null;
  showDeleteDialog.value = true;
}

/** Supprime le projet (SDD §5.11) */
async function confirmDelete(): Promise<void> {
  if (!deleteProjectId.value) return;
  deleteError.value = null;
  try {
    await window.novelTradAPI.invoke("project:delete", deleteProjectId.value, deleteRemoveFiles.value);
    await projectStore.loadRecent();
    showDeleteDialog.value = false;
    deleteProjectId.value = null;
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : "Erreur lors de la suppression du projet";
  }
}
</script>

<template>
  <div class="home">
    <header class="hero">
      <h1>NovelTrad 2.0</h1>
      <p>Moteur de traduction de romans assiste par IA multi-agent.</p>
      <div class="ollama-status" :class="{ ok: ollamaStore.available }">
        {{
          ollamaStore.available
            ? "✅ Ollama disponible"
            : "❌ Ollama non detecte"
        }}
      </div>
    </header>

    <section class="actions">
      <button class="btn-primary" @click="showCreate = true">
        + Nouveau projet
      </button>
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
      <button
        class="btn-primary"
        :disabled="!newProject.name || projectStore.loading"
        @click="create"
      >
        Creer
      </button>
      <p v-if="creationError" class="error-msg">{{ creationError }}</p>
    </section>

    <!-- Dialogue de confirmation de suppression (SDD §5.11) -->
    <div v-if="showDeleteDialog" class="modal-overlay" @click.self="showDeleteDialog = false">
      <div class="modal-card">
        <h3>Supprimer le projet</h3>
        <p>
          Êtes-vous sûr de vouloir supprimer le projet
          <strong>{{ deleteProjectName }}</strong> ?
        </p>
        <label class="checkbox-label">
          <input type="checkbox" v-model="deleteRemoveFiles" />
          <span>Supprimer les fichiers du disque</span>
        </label>
        <p class="modal-hint">
          {{
            deleteRemoveFiles
              ? "Tous les fichiers du projet seront définitivement supprimés."
              : "Le projet sera retiré de la liste mais les fichiers resteront sur le disque."
          }}
        </p>
        <p v-if="deleteError" class="error-msg">{{ deleteError }}</p>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showDeleteDialog = false">
            Annuler
          </button>
          <button class="btn-danger" @click="confirmDelete">
            Supprimer
          </button>
        </div>
      </div>
    </div>

    <!-- Bannière de mise à jour -->
    <section v-if="updateAvailable" class="card update-banner">
      <h2>🔄 Mise à jour disponible</h2>
      <p>Version <strong>{{ updateVersion }}</strong> est disponible.</p>
      <div class="update-actions">
        <button v-if="!updateDownloaded" class="btn-primary" @click="downloadUpdate" :disabled="updateDownloading">
          {{ updateDownloading ? "Téléchargement..." : "Télécharger" }}
        </button>
        <button v-if="updateDownloaded" class="btn-primary" @click="installUpdate">
          Installer et redémarrer
        </button>
      </div>
    </section>
    <section v-else class="card update-check">
      <div class="update-row">
        <span>NovelTrad 2.0.4</span>
        <button class="btn-ghost" @click="checkUpdate" :disabled="updateChecking">
          {{ updateChecking ? "Vérification..." : "Vérifier mise à jour" }}
        </button>
      </div>
    </section>

    <section class="card">
      <h2>Projets recents</h2>
      <ul v-if="projectStore.recentProjects.length">
        <li
          v-for="p in projectStore.recentProjects"
          :key="p.id"
          class="project-item"
          @click="open(p.path)"
          @contextmenu.prevent="openDeleteDialog(p.id, p.name)"
        >
          <strong>{{ p.name }}</strong>
          <span class="meta"
            >{{ p.sourceLanguage }} → {{ p.targetLanguage }}</span
          >
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

input,
select {
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

.error-msg {
  color: var(--error);
  font-size: 13px;
  margin-top: 8px;
  padding: 8px 12px;
  background-color: rgba(239, 68, 68, 0.1);
  border-radius: var(--border-radius);
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
  max-width: 460px;
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

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-primary);
}

.checkbox-label input[type="checkbox"] {
  accent-color: var(--accent);
  width: 18px;
  height: 18px;
}

.modal-hint {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-cancel {
  background-color: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--bg-tertiary);
  padding: 8px 16px;
  border-radius: var(--border-radius);
  cursor: pointer;
}

.btn-danger {
  background-color: var(--error);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: var(--border-radius);
  cursor: pointer;
}

.btn-danger:hover {
  opacity: 0.9;
}

/* Bannière de mise à jour */
.update-banner {
  border: 1px solid var(--accent);
  background: rgba(56, 189, 248, 0.08);
}

.update-banner h2 {
  color: var(--accent);
}

.update-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.update-check {
  padding: 8px 16px;
}

.update-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--text-secondary);
}

.btn-ghost {
  background: transparent;
  border: 1px solid var(--bg-tertiary);
  color: var(--text-secondary);
  padding: 4px 12px;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 12px;
}

.btn-ghost:hover {
  background: var(--bg-tertiary);
}

.btn-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
