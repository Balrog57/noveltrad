<script setup lang="ts" generic="TRow extends Record<string, unknown>">
import { ref, computed } from "vue";

export interface Column {
  /** Clé unique de la colonne (correspond à une propriété de la ligne) */
  key: string;
  /** Libellé affiché dans l'en-tête */
  label: string;
  /** Colonne triable ? */
  sortable?: boolean;
  /** Largeur CSS (ex: "120px", "20%") */
  width?: string;
}

const props = withDefaults(
  defineProps<{
    /** Définition des colonnes */
    columns: Column[];
    /** Lignes de données */
    rows: TRow[];
    /** Le tableau est-il triable ? (active le tri au clic sur les headers triables) */
    sortable?: boolean;
  }>(),
  { sortable: true },
);

const emit = defineEmits<{
  /** Clic sur une ligne */
  "row-click": [row: TRow];
  /** Clic droit sur une ligne (menu contextuel) */
  "row-context": [row: TRow, event: MouseEvent];
  /** Changement de tri */
  sort: [key: string, direction: "asc" | "desc"];
}>();

/** Colonne actuellement triée (null = pas de tri) */
const sortKey = ref<string | null>(null);
/** Direction du tri */
const sortDir = ref<"asc" | "desc">("asc");

/** Lignes triées (si le tri est actif) */
const sortedRows = computed(() => {
  if (!props.sortable || !sortKey.value) return props.rows;
  const dir = sortDir.value === "asc" ? 1 : -1;
  return [...props.rows].sort((a, b) => {
    const va = a[sortKey.value!];
    const vb = b[sortKey.value!];
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    const sa = String(va);
    const sb = String(vb);
    return sa.localeCompare(sb, "fr", { sensitivity: "base" }) * dir;
  });
});

/** Gère le clic sur un en-tête de colonne pour le tri */
function onHeaderClick(col: Column): void {
  if (!props.sortable || !col.sortable) return;
  if (sortKey.value === col.key) {
    // Inverse la direction
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  } else {
    sortKey.value = col.key;
    sortDir.value = "asc";
  }
  emit("sort", sortKey.value, sortDir.value);
}

/** Icône de tri pour une colonne */
function sortIcon(col: Column): string {
  if (sortKey.value !== col.key) return "↕";
  return sortDir.value === "asc" ? "↑" : "↓";
}
</script>

<template>
  <div class="nt-table-wrapper">
    <table class="nt-table">
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            :style="col.width ? { width: col.width } : undefined"
            :class="{
              'nt-th--sortable': sortable && col.sortable !== false,
              'nt-th--active': sortKey === col.key,
            }"
            :tabindex="sortable && col.sortable !== false ? 0 : undefined"
            @click="onHeaderClick(col)"
            @keydown.enter="onHeaderClick(col)"
            @keydown.space.prevent="onHeaderClick(col)"
          >
            <span class="nt-th-label">{{ col.label }}</span>
            <span
              v-if="sortable && col.sortable !== false"
              class="nt-th-sort-icon"
            >
              {{ sortIcon(col) }}
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, idx) in sortedRows"
          :key="(row.id as string) ?? idx"
          class="nt-tr"
          :class="{ 'nt-tr--odd': idx % 2 === 0 }"
          tabindex="0"
          @click="emit('row-click', row)"
          @keydown.enter="emit('row-click', row)"
          @keydown.space.prevent="emit('row-click', row)"
          @contextmenu.prevent="emit('row-context', row, $event)"
        >
          <td v-for="col in columns" :key="col.key">
            <!-- Slot nommé pour rendu personnalisé -->
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
              {{ row[col.key] }}
            </slot>
          </td>
        </tr>
        <tr v-if="rows.length === 0">
          <td :colspan="columns.length" class="nt-empty">
            <slot name="empty">Aucune donnée.</slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.nt-table-wrapper {
  overflow-x: auto;
  width: 100%;
}

.nt-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

thead th {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  font-weight: 600;
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid var(--bg-secondary);
  user-select: none;
  white-space: nowrap;
}

.nt-th--sortable {
  cursor: pointer;
}

.nt-th--sortable:hover {
  background-color: var(--accent-hover);
}

.nt-th--sortable:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

.nt-th--active {
  color: var(--accent);
}

.nt-th-label {
  margin-right: 4px;
}

.nt-th-sort-icon {
  font-size: 12px;
  opacity: 0.6;
}

tbody td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--bg-tertiary);
  color: var(--text-primary);
}

.nt-tr {
  cursor: pointer;
}

.nt-tr:hover {
  background-color: var(--bg-tertiary);
}

.nt-tr:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

.nt-tr--odd {
  background-color: var(--bg-secondary);
}

.nt-tr--odd:hover {
  background-color: var(--bg-tertiary);
}

.nt-empty {
  text-align: center;
  padding: 24px;
  color: var(--text-secondary);
  font-style: italic;
}
</style>
