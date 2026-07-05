<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { LexiconEntry } from "@shared/types/index.js";
import NtModal from "../ui/NtModal.vue";

const props = defineProps<{
  /** Entrée à éditer (null = mode création) */
  entry: LexiconEntry | null;
  /** Liste des catégories existantes pour le select */
  categories: string[];
}>();

const emit = defineEmits<{
  save: [entry: LexiconEntry];
  cancel: [];
}>();

/** Formulaire local */
const form = ref({
  term: "",
  translation: "",
  category: "general",
  gender: "",
  aliases: [""] as string[],
  description: "",
  notes: "",
  priority: 5,
  locked: false,
  forbidden: [""] as string[],
  pronunciation: "",
});

/** Erreurs de validation */
const errors = ref<Record<string, string>>({});

/** Initialiser le formulaire à partir de l'entrée prop */
watch(
  () => props.entry,
  (entry) => {
    if (entry) {
      form.value = {
        term: entry.term,
        translation: entry.translation,
        category: entry.category || "general",
        gender: entry.gender ?? "",
        aliases: entry.aliases.length > 0 ? [...entry.aliases] : [""],
        description: entry.description ?? "",
        notes: entry.notes ?? "",
        priority: entry.priority ?? 5,
        locked: entry.locked,
        forbidden:
          entry.forbidden && entry.forbidden.length > 0
            ? [...entry.forbidden]
            : [""],
        pronunciation: entry.pronunciation ?? "",
      };
    } else {
      form.value = {
        term: "",
        translation: "",
        category: "general",
        gender: "",
        aliases: [""],
        description: "",
        notes: "",
        priority: 5,
        locked: false,
        forbidden: [""],
        pronunciation: "",
      };
    }
    errors.value = {};
  },
  { immediate: true },
);

const isCreate = computed(() => props.entry === null);

/** Titre du modal */
const title = computed(() =>
  isCreate.value
    ? "Ajouter une entrée"
    : `Modifier : ${props.entry?.term ?? ""}`,
);

// --- Gestion des listes dynamiques (aliases, forbidden) ---
function addAlias(): void {
  form.value.aliases.push("");
}
function removeAlias(idx: number): void {
  if (form.value.aliases.length <= 1) {return;}
  form.value.aliases.splice(idx, 1);
}

function addForbidden(): void {
  form.value.forbidden.push("");
}
function removeForbidden(idx: number): void {
  if (form.value.forbidden.length <= 1) {return;}
  form.value.forbidden.splice(idx, 1);
}

// --- Validation ---
function validate(): boolean {
  errors.value = {};
  if (!form.value.term.trim()) {
    errors.value.term = "Le terme est requis.";
  }
  if (!form.value.translation.trim()) {
    errors.value.translation = "La traduction est requise.";
  }
  return Object.keys(errors.value).length === 0;
}

// --- Soumission ---
function onSubmit(): void {
  if (!validate()) {return;}
  const entry: LexiconEntry = {
    id: props.entry?.id ?? crypto.randomUUID(),
    projectId: props.entry?.projectId ?? "",
    term: form.value.term.trim(),
    translation: form.value.translation.trim(),
    category: form.value.category,
    aliases: form.value.aliases.filter((a) => a.trim().length > 0),
    locked: form.value.locked,
    forbidden: form.value.forbidden.filter((f) => f.trim().length > 0),
    priority: form.value.priority,
    description: form.value.description.trim() || undefined,
    notes: form.value.notes.trim() || undefined,
    gender: form.value.gender.trim() || undefined,
    pronunciation: form.value.pronunciation.trim() || undefined,
  };
  emit("save", entry);
}

function onCancel(): void {
  emit("cancel");
}
</script>

<template>
  <NtModal :visible="true" :title="title" size="lg" @close="onCancel">
    <form class="lexicon-form" @submit.prevent="onSubmit">
      <!-- Terme * -->
      <div class="form-group">
        <label class="form-label" for="lex-term">
          Terme <span class="required">*</span>
        </label>
        <input
          id="lex-term"
          v-model="form.term"
          type="text"
          class="form-input"
          placeholder="Ex : 功法"
        >
        <p v-if="errors.term" class="form-error">{{ errors.term }}</p>
      </div>

      <!-- Traduction * -->
      <div class="form-group">
        <label class="form-label" for="lex-translation">
          Traduction <span class="required">*</span>
        </label>
        <input
          id="lex-translation"
          v-model="form.translation"
          type="text"
          class="form-input"
          placeholder="Ex : Technique de cultivation"
        >
        <p v-if="errors.translation" class="form-error">
          {{ errors.translation }}
        </p>
      </div>

      <!-- Catégorie + Genre -->
      <div class="form-row">
        <div class="form-group">
          <label class="form-label" for="lex-category">Catégorie</label>
          <select id="lex-category" v-model="form.category" class="form-input">
            <option value="general">Général</option>
            <option value="personnage">Personnage</option>
            <option value="lieu">Lieu</option>
            <option value="technique">Technique</option>
            <option value="arme">Arme</option>
            <option value="objet">Objet</option>
            <option value="concept">Concept</option>
            <option value="titre">Titre</option>
            <option value="autre">Autre</option>
            <option
              v-for="cat in categories.filter(
                (c) =>
                  ![
                    'general',
                    'personnage',
                    'lieu',
                    'technique',
                    'arme',
                    'objet',
                    'concept',
                    'titre',
                    'autre',
                  ].includes(c),
              )"
              :key="cat"
              :value="cat"
            >
              {{ cat }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="lex-gender">Genre</label>
          <select id="lex-gender" v-model="form.gender" class="form-input">
            <option value="">—</option>
            <option value="m">Masculin</option>
            <option value="f">Féminin</option>
            <option value="n">Neutre</option>
          </select>
        </div>
      </div>

      <!-- Aliases (liste dynamique) -->
      <div class="form-group">
        <label class="form-label">Alias</label>
        <div
          v-for="(_, idx) in form.aliases"
          :key="'alias-' + idx"
          class="form-list-row"
        >
          <input
            v-model="form.aliases[idx]"
            type="text"
            class="form-input"
            placeholder="Alias..."
          >
          <button
            type="button"
            class="form-list-btn"
            :class="{ 'form-list-btn--disabled': form.aliases.length <= 1 }"
            :disabled="form.aliases.length <= 1"
            :aria-label="`Supprimer l'alias ${idx + 1}`"
            :title="form.aliases.length <= 1 ? 'Impossible de supprimer le dernier alias' : `Supprimer cet alias`"
            @click="removeAlias(idx)"
          >
            ✕
          </button>
        </div>
        <button type="button" class="form-list-add" @click="addAlias">
          + Ajouter un alias
        </button>
      </div>

      <!-- Description + Notes -->
      <div class="form-row">
        <div class="form-group">
          <label class="form-label" for="lex-desc">Description</label>
          <textarea
            id="lex-desc"
            v-model="form.description"
            class="form-input form-textarea"
            rows="3"
            placeholder="Description du terme..."
          />
        </div>
        <div class="form-group">
          <label class="form-label" for="lex-notes">Notes</label>
          <textarea
            id="lex-notes"
            v-model="form.notes"
            class="form-input form-textarea"
            rows="3"
            placeholder="Notes de traduction..."
          />
        </div>
      </div>

      <!-- Priorité 0-10 -->
      <div class="form-group">
        <label class="form-label" for="lex-priority">
          Priorité : {{ form.priority }}
        </label>
        <input
          id="lex-priority"
          v-model.number="form.priority"
          type="range"
          class="form-range"
          min="0"
          max="10"
        >
        <div class="range-labels">
          <span>0 (basse)</span>
          <span>10 (haute)</span>
        </div>
      </div>

      <!-- Verrouillage -->
      <div class="form-group">
        <label class="form-checkbox">
          <input v-model="form.locked" type="checkbox">
          <span>Verrouillage (la traduction ne sera pas modifiée
            automatiquement)</span>
        </label>
      </div>

      <!-- Forbidden (liste dynamique) -->
      <div class="form-group">
        <label class="form-label">Traductions interdites</label>
        <div
          v-for="(_, idx) in form.forbidden"
          :key="'forbidden-' + idx"
          class="form-list-row"
        >
          <input
            v-model="form.forbidden[idx]"
            type="text"
            class="form-input"
            placeholder="Traduction à éviter..."
          >
          <button
            type="button"
            class="form-list-btn"
            :class="{ 'form-list-btn--disabled': form.forbidden.length <= 1 }"
            :disabled="form.forbidden.length <= 1"
            :aria-label="`Supprimer l'interdiction ${idx + 1}`"
            :title="form.forbidden.length <= 1 ? 'Impossible de supprimer la dernière interdiction' : `Supprimer cette interdiction`"
            @click="removeForbidden(idx)"
          >
            ✕
          </button>
        </div>
        <button type="button" class="form-list-add" @click="addForbidden">
          + Ajouter une interdiction
        </button>
      </div>

      <!-- Prononciation -->
      <div class="form-group">
        <label class="form-label" for="lex-pronunciation">Prononciation</label>
        <input
          id="lex-pronunciation"
          v-model="form.pronunciation"
          type="text"
          class="form-input"
          placeholder="Ex : gōng fǎ"
        >
      </div>
    </form>

    <!-- Pied de modal avec boutons d'action -->
    <template #footer>
      <button type="button" class="btn-cancel" @click="onCancel">
        Annuler
      </button>
      <button type="button" class="btn-primary" @click="onSubmit">
        {{ isCreate ? "Ajouter" : "Enregistrer" }}
      </button>
    </template>
  </NtModal>
</template>

<style scoped>
.lexicon-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row > .form-group {
  flex: 1;
}

.form-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.required {
  color: var(--error);
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
}

.form-range {
  width: 100%;
  accent-color: var(--accent);
}

.range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-secondary);
}

.form-error {
  color: var(--error);
  font-size: 12px;
  margin: 0;
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
}

.form-checkbox input {
  accent-color: var(--accent);
}

.form-list-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.form-list-row .form-input {
  flex: 1;
}

.form-list-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
}

.form-list-btn:hover {
  color: var(--error);
  background-color: var(--bg-tertiary);
}

.form-list-btn--disabled,
.form-list-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-list-btn--disabled:hover,
.form-list-btn:disabled:hover {
  color: var(--text-secondary);
  background: none;
}

.form-list-add {
  background: none;
  border: 1px dashed var(--bg-tertiary);
  color: var(--accent);
  cursor: pointer;
  font-size: 13px;
  padding: 6px 12px;
  border-radius: 6px;
}

.form-list-add:hover {
  background-color: var(--bg-tertiary);
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
</style>
