<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import { useLexiconStore } from "../stores/lexicon";
import { useProjectStore } from "../stores/project";
import LexiconTable from "../components/lexicon/LexiconTable.vue";
import LexiconForm from "../components/lexicon/LexiconForm.vue";
import NtModal from "../components/ui/NtModal.vue";
import type { LexiconEntry, CandidateTerm } from "@shared/types/index.js";

const route = useRoute();
const lexiconStore = useLexiconStore();
const projectStore = useProjectStore();

const projectId = computed(
  () =>
    ((route.params.projectId as string) || projectStore.currentProject?.id) ??
    "",
);

/** État de la modale d'édition */
const editingEntry = ref<LexiconEntry | null>(null);

/** État de la modale d'import */
const showImportModal = ref(false);
const importFormat = ref<"csv" | "json" | "tsv">("csv");
const importData = ref("");

/** État de l'export */
const showExportModal = ref(false);
const exportFormat = ref<"csv" | "json" | "tsv">("csv");

/** État de l'extraction de candidats */
const showCandidatesModal = ref(false);
const candidateText = ref("");
const selectedCandidates = ref<Set<string>>(new Set());

// Charger le lexique au montage si un projet est ouvert
onMounted(async () => {
  if (projectId.value) {
    await lexiconStore.loadLexicon(projectId.value);
  }
});

// --- CRUD ---

function openCreateForm(): void {
  editingEntry.value = null;
}

function openEditForm(entry: LexiconEntry): void {
  editingEntry.value = { ...entry };
}

async function handleSave(entry: LexiconEntry): Promise<void> {
  // S'assurer que le projectId est présent
  if (!entry.projectId) {
    entry.projectId = projectId.value;
  }
  await lexiconStore.saveEntry(entry);
  editingEntry.value = null;
}

function handleCancel(): void {
  editingEntry.value = null;
}

async function handleDelete(entry: LexiconEntry): Promise<void> {
  if (!confirm(`Supprimer l'entrée "${entry.term}" ?`)) return;
  await lexiconStore.deleteEntry(entry.id, projectId.value);
}

function handleDuplicate(entry: LexiconEntry): void {
  const duplicate: LexiconEntry = {
    ...entry,
    id: crypto.randomUUID(),
    term: `${entry.term} (copie)`,
    locked: false,
  };
  editingEntry.value = duplicate;
}

function handleMerge(entry: LexiconEntry): void {
  // Ouvre l'entrée en édition pour permettre de fusionner manuellement
  editingEntry.value = { ...entry };
}

// --- Import ---

function openImport(): void {
  importFormat.value = "csv";
  importData.value = "";
  showImportModal.value = true;
}

async function doImport(): Promise<void> {
  if (!importData.value.trim()) return;
  await lexiconStore.importLexicon(
    projectId.value,
    importFormat.value,
    importData.value,
  );
  showImportModal.value = false;
}

// --- Export ---

function openExport(): void {
  exportFormat.value = "csv";
  showExportModal.value = true;
}

async function doExport(): Promise<void> {
  try {
    const content = await lexiconStore.exportLexicon(
      projectId.value,
      exportFormat.value,
    );
    // Télécharger en tant que fichier
    const ext = exportFormat.value === "tsv" ? "tsv" : exportFormat.value;
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lexique-${projectId.value}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
    showExportModal.value = false;
  } catch {
    // Erreur déjà gérée dans le store
  }
}

// --- Extraction de candidats ---

async function openCandidates(): Promise<void> {
  candidateText.value = "";
  selectedCandidates.value = new Set();
  lexiconStore.candidates = [];

  showCandidatesModal.value = true;
}

async function doExtract(): Promise<void> {
  if (!candidateText.value.trim()) return;
  await lexiconStore.extractCandidates(
    candidateText.value,
    projectStore.currentProject?.sourceLanguage ?? "auto",
  );
}

function toggleCandidate(term: string): void {
  const s = new Set(selectedCandidates.value);
  if (s.has(term)) {
    s.delete(term);
  } else {
    s.add(term);
  }
  selectedCandidates.value = s;
}

async function addSelectedCandidates(): Promise<void> {
  for (const candidate of lexiconStore.candidates) {
    if (!selectedCandidates.value.has(candidate.term)) continue;
    const entry: LexiconEntry = {
      id: crypto.randomUUID(),
      projectId: projectId.value,
      term: candidate.term,
      translation: "",
      category: candidate.suggestedCategory ?? "general",
      aliases: [],
      locked: false,
      priority: 5,
    };
    await lexiconStore.saveEntry(entry);
  }
  showCandidatesModal.value = false;
}
</script>

<template>
  <div class="lexicon-view">
    <!-- Barre d'outils -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h1>📚 Lexique</h1>
        <!-- Barre de recherche -->
        <div class="search-box">
          <input
            v-model="lexiconStore.searchQuery"
            type="text"
            class="search-input"
            placeholder="Rechercher un terme, une traduction…"
          />
        </div>
        <!-- Filtre par catégorie -->
        <select v-model="lexiconStore.categoryFilter" class="filter-select">
          <option :value="null">Toutes les catégories</option>
          <option
            v-for="cat in lexiconStore.categories"
            :key="cat"
            :value="cat"
          >
            {{ cat }}
          </option>
        </select>
      </div>

      <div class="toolbar-right">
        <button class="btn-accent" @click="openCreateForm">+ Ajouter</button>
        <button class="btn-secondary" @click="openImport">Importer</button>
        <button
          class="btn-secondary"
          :disabled="lexiconStore.entries.length === 0"
          @click="openExport"
        >
          Exporter
        </button>
        <button class="btn-secondary" @click="openCandidates">
          Extraire candidats
        </button>
      </div>
    </div>

    <!-- Message d'erreur -->
    <p v-if="lexiconStore.error" class="error-msg">
      {{ lexiconStore.error }}
    </p>

    <!-- Indicateur de chargement -->
    <p v-if="lexiconStore.loading" class="loading-msg">Chargement…</p>

    <!-- Tableau des entrées -->
    <LexiconTable
      v-else
      :entries="lexiconStore.filteredEntries"
      @edit="openEditForm"
      @duplicate="handleDuplicate"
      @delete="handleDelete"
      @merge="handleMerge"
    />

    <!-- Formulaire d'édition (modal) -->
    <LexiconForm
      v-if="editingEntry !== null"
      :entry="editingEntry"
      :categories="lexiconStore.categories"
      @save="handleSave"
      @cancel="handleCancel"
    />

    <!-- Modal d'import -->
    <NtModal
      :visible="showImportModal"
      title="Importer un lexique"
      size="md"
      @close="showImportModal = false"
    >
      <div class="import-body">
        <div class="form-group">
          <label class="form-label">Format</label>
          <select v-model="importFormat" class="form-input">
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
            <option value="tsv">TSV</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Données</label>
          <textarea
            v-model="importData"
            class="form-input form-textarea"
            rows="12"
            placeholder="Collez les données CSV, JSON ou TSV ici…"
          />
        </div>
      </div>
      <template #footer>
        <button class="btn-cancel" @click="showImportModal = false">
          Annuler
        </button>
        <button class="btn-primary" @click="doImport">Importer</button>
      </template>
    </NtModal>

    <!-- Modal d'export -->
    <NtModal
      :visible="showExportModal"
      title="Exporter le lexique"
      size="sm"
      @close="showExportModal = false"
    >
      <div class="form-group">
        <label class="form-label">Format</label>
        <select v-model="exportFormat" class="form-input">
          <option value="csv">CSV</option>
          <option value="json">JSON</option>
          <option value="tsv">TSV</option>
        </select>
      </div>
      <template #footer>
        <button class="btn-cancel" @click="showExportModal = false">
          Annuler
        </button>
        <button class="btn-primary" @click="doExport">Exporter</button>
      </template>
    </NtModal>

    <!-- Modal d'extraction de candidats -->
    <NtModal
      :visible="showCandidatesModal"
      title="Extraire les termes candidats"
      size="lg"
      @close="showCandidatesModal = false"
    >
      <div class="candidates-body">
        <div class="form-group">
          <label class="form-label"> Texte source à analyser </label>
          <textarea
            v-model="candidateText"
            class="form-input form-textarea"
            rows="8"
            placeholder="Collez le texte à analyser ici…"
          />
        </div>
        <button
          class="btn-accent"
          :disabled="!candidateText.trim() || lexiconStore.loading"
          @click="doExtract"
        >
          Extraire
        </button>

        <!-- Résultats -->
        <div
          v-if="lexiconStore.candidates.length > 0"
          class="candidates-results"
        >
          <h3>{{ lexiconStore.candidates.length }} termes candidats trouvés</h3>
          <div
            v-for="c in lexiconStore.candidates"
            :key="c.term"
            class="candidate-item"
          >
            <label class="form-checkbox">
              <input
                type="checkbox"
                :checked="selectedCandidates.has(c.term)"
                @change="toggleCandidate(c.term)"
              />
              <span class="candidate-term">{{ c.term }}</span>
            </label>
            <span class="candidate-occ"> {{ c.occurrences }} occ. </span>
            <span class="candidate-cat">{{ c.suggestedCategory }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-cancel" @click="showCandidatesModal = false">
          Fermer
        </button>
        <button
          class="btn-primary"
          :disabled="selectedCandidates.size === 0"
          @click="addSelectedCandidates"
        >
          Ajouter la sélection ({{ selectedCandidates.size }})
        </button>
      </template>
    </NtModal>
  </div>
</template>

<style scoped>
.lexicon-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  height: 100%;
  overflow: auto;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-left h1 {
  margin: 0;
  font-size: 22px;
  color: var(--text-primary);
}

.toolbar-right {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.search-box {
  min-width: 220px;
}

.search-input {
  background-color: var(--bg-secondary);
  border: 1px solid var(--bg-tertiary);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--text-primary);
  font-size: 14px;
  width: 100%;
}

.search-input:focus {
  border-color: var(--accent);
  outline: none;
}

.search-input::placeholder {
  color: var(--text-secondary);
}

.filter-select {
  background-color: var(--bg-secondary);
  border: 1px solid var(--bg-tertiary);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
}

.filter-select:focus {
  border-color: var(--accent);
  outline: none;
}

.error-msg {
  color: var(--error);
  padding: 12px;
  background-color: rgba(239, 68, 68, 0.1);
  border-radius: var(--border-radius);
  margin: 0;
}

.loading-msg {
  color: var(--text-secondary);
  text-align: center;
  padding: 24px;
}

/* Boutons */
.btn-accent {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}

.btn-accent:hover {
  background-color: var(--accent-hover);
}

.btn-accent:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: none;
  padding: 8px 16px;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary:hover {
  background-color: var(--text-secondary);
  color: white;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel {
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
  border: none;
  padding: 8px 20px;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 14px;
}

.btn-cancel:hover {
  background-color: var(--text-secondary);
  color: var(--bg-primary);
}

.btn-primary {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 8px 20px;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}

.btn-primary:hover {
  background-color: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Formulaire (import) */
.import-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.form-input {
  background-color: var(--bg-secondary);
  border: 1px solid var(--bg-tertiary);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--text-primary);
  font-size: 14px;
}

.form-input:focus {
  border-color: var(--accent);
  outline: none;
}

.form-textarea {
  resize: vertical;
  font-family: monospace;
}

/* Candidats */
.candidates-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.candidates-results {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--bg-tertiary);
  border-radius: 6px;
  padding: 12px;
}

.candidates-results h3 {
  margin: 0 0 8px;
  font-size: 15px;
  color: var(--text-primary);
}

.candidate-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid var(--bg-tertiary);
}

.candidate-item:last-child {
  border-bottom: none;
}

.candidate-term {
  font-weight: 500;
  color: var(--text-primary);
}

.candidate-occ {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 60px;
}

.candidate-cat {
  font-size: 11px;
  color: var(--accent);
  background-color: rgba(56, 189, 248, 0.1);
  padding: 2px 8px;
  border-radius: 999px;
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.form-checkbox input {
  accent-color: var(--accent);
}
</style>
