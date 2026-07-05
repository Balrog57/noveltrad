<script setup lang="ts">
import { ref } from "vue";
import type { LexiconEntry } from "@shared/types/index.js";
import NtTable, { type Column } from "../ui/NtTable.vue";

const _props = defineProps<{
  entries: LexiconEntry[];
}>();

const emit = defineEmits<{
  edit: [entry: LexiconEntry];
  duplicate: [entry: LexiconEntry];
  delete: [entry: LexiconEntry];
  merge: [entry: LexiconEntry];
}>();

/** Définition des colonnes */
const columns: Column[] = [
  { key: "term", label: "Terme", sortable: true, width: "15%" },
  { key: "translation", label: "Traduction", sortable: true, width: "20%" },
  { key: "category", label: "Catégorie", sortable: true, width: "12%" },
  { key: "priority", label: "Priorité", sortable: true, width: "8%" },
  { key: "locked", label: "Verrou", sortable: true, width: "6%" },
  { key: "aliases", label: "Alias", width: "25%" },
];

/** Position du menu contextuel */
const contextMenu = ref<{
  visible: boolean;
  x: number;
  y: number;
  entry: LexiconEntry | null;
}>({ visible: false, x: 0, y: 0, entry: null });

function onRowClick(row: Record<string, unknown>): void {
  emit("edit", row as unknown as LexiconEntry);
}

function onRowContext(row: Record<string, unknown>, e: MouseEvent): void {
  const entry = row as unknown as LexiconEntry;
  contextMenu.value = {
    visible: true,
    x: Math.max(0, Math.min(e.clientX, window.innerWidth - 180)),
    y: Math.max(0, Math.min(e.clientY, window.innerHeight - 120)),
    entry,
  };
}

function closeContextMenu(): void {
  contextMenu.value.visible = false;
}

function handleEdit(): void {
  if (contextMenu.value.entry) {emit("edit", contextMenu.value.entry);}
  closeContextMenu();
}

function handleDuplicate(): void {
  if (contextMenu.value.entry) {emit("duplicate", contextMenu.value.entry);}
  closeContextMenu();
}

function handleDelete(): void {
  if (contextMenu.value.entry) {emit("delete", contextMenu.value.entry);}
  closeContextMenu();
}

function handleMerge(): void {
  if (contextMenu.value.entry) {emit("merge", contextMenu.value.entry);}
  closeContextMenu();
}

/** Affiche un aperçu compact des alias */
function aliasPreview(aliases: string[]): string {
  if (!aliases || aliases.length === 0) {return "—";}
  return aliases.slice(0, 3).join(", ") + (aliases.length > 3 ? "…" : "");
}
</script>

<template>
  <div @click="closeContextMenu">
    <NtTable
      :columns="columns"
      :rows="entries as unknown as Record<string, unknown>[]"
      @row-click="onRowClick"
      @row-context="onRowContext"
    >
      <!-- Colonne Verrou : icône 🔒 -->
      <template #cell-locked="{ value }">
        <span v-if="value">🔒</span>
        <span v-else style="opacity: 0.3">🔓</span>
      </template>

      <!-- Colonne Alias : aperçu -->
      <template #cell-aliases="{ value }">
        <span class="alias-preview">
          {{ aliasPreview(value as string[]) }}
        </span>
      </template>

      <!-- Ligne vide -->
      <template #empty> Aucune entrée dans le lexique. </template>
    </NtTable>

    <!-- Menu contextuel -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{
        left: contextMenu.x + 'px',
        top: contextMenu.y + 'px',
      }"
    >
      <button class="context-item" @click="handleEdit">Modifier</button>
      <button class="context-item" @click="handleDuplicate">Dupliquer</button>
      <button class="context-item" @click="handleMerge">Fusionner</button>
      <hr class="context-divider">
      <button class="context-item context-item--danger" @click="handleDelete">
        Supprimer
      </button>
    </div>
  </div>
</template>

<style scoped>
.alias-preview {
  color: var(--text-secondary);
  font-size: 13px;
}

.context-menu {
  position: fixed;
  z-index: 1100;
  background-color: var(--bg-secondary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  padding: 4px 0;
  min-width: 160px;
}

.context-item {
  display: block;
  width: 100%;
  padding: 8px 16px;
  background: none;
  border: none;
  color: var(--text-primary);
  text-align: left;
  font-size: 13px;
  cursor: pointer;
}

.context-item:hover {
  background-color: var(--bg-tertiary);
}

.context-item--danger {
  color: var(--error);
}

.context-item--danger:hover {
  background-color: rgba(239, 68, 68, 0.1);
}

.context-divider {
  border: none;
  border-top: 1px solid var(--bg-tertiary);
  margin: 4px 0;
}
</style>
