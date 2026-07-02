<script setup lang="ts">
import { ref, computed } from "vue";
import type { DiffResult, ParagraphChange } from "@shared/types/index.js";
import { diff_match_patch as DiffMatchPatch } from "diff-match-patch";
import NtSplitPane from "../editor/NtSplitPane.vue";

const props = withDefaults(
  defineProps<{
    /** Résultat du diff à afficher */
    diff: DiffResult | null;
    /** Vue côte à côte ou unifiée */
    mode?: "side-by-side" | "unified";
  }>(),
  { mode: "side-by-side" },
);

/** Mode actif (toggle) */
const currentMode = ref<"side-by-side" | "unified">(props.mode);

/** Activer/désactiver le diff ligne à ligne */
const showLineLevel = ref(false);

const dmp = new DiffMatchPatch();

/**
 * Calcule le diff ligne à ligne entre deux textes.
 * Retourne un tableau de segments : { type: "equal"|"added"|"removed", text }
 */
function lineDiff(
  before: string,
  after: string,
): Array<{ type: "equal" | "added" | "removed"; text: string }> {
  const diffs = dmp.diff_main(before, after);
  dmp.diff_cleanupSemantic(diffs);
  return diffs.map(([op, text]) => ({
    type: op === -1 ? "removed" : op === 1 ? "added" : "equal",
    text,
  }));
}

/** Style CSS pour un changement */
function changeClass(change: ParagraphChange): string {
  switch (change.type) {
    case "added":
      return "diff-added";
    case "removed":
      return "diff-removed";
    case "modified":
      return "diff-modified";
    default:
      return "";
  }
}

/** Libellé du type de changement */
function changeLabel(change: ParagraphChange): string {
  switch (change.type) {
    case "added":
      return "Ajouté";
    case "removed":
      return "Supprimé";
    case "modified":
      return "Modifié";
    default:
      return "";
  }
}

/** Diffs ligne à ligne pour le mode unifié */
function paragraphLineDiffs(
  change: ParagraphChange,
): Array<{ type: "equal" | "added" | "removed"; text: string }> | null {
  if (!showLineLevel.value) return null;
  if (change.type === "added" && change.targetAfter) {
    return lineDiff("", change.targetAfter);
  }
  if (change.type === "removed" && change.targetBefore) {
    return lineDiff(change.targetBefore, "");
  }
  if (change.type === "modified") {
    return lineDiff(change.targetBefore ?? "", change.targetAfter ?? "");
  }
  return null;
}

function toggleMode(): void {
  currentMode.value =
    currentMode.value === "side-by-side" ? "unified" : "side-by-side";
}
</script>

<template>
  <div class="nt-diff-viewer">
    <div class="diff-toolbar">
      <span class="diff-stats" v-if="diff">
        {{ diff.changes.length }} changement{{
          diff.changes.length > 1 ? "s" : ""
        }}
      </span>
      <div class="diff-toggle-group">
        <label class="toggle-label">
          <input type="checkbox" v-model="showLineLevel" />
          Afficher au niveau ligne
        </label>
        <button class="btn-mode" @click="toggleMode">
          {{ currentMode === "side-by-side" ? "Vue unifiée" : "Côte à côte" }}
        </button>
      </div>
    </div>

    <div v-if="!diff" class="diff-empty">
      Sélectionnez deux versions pour comparer.
    </div>

    <!-- Mode côte à côte -->
    <NtSplitPane v-else-if="currentMode === 'side-by-side'" :initial-split="50">
      <template #left>
        <div class="diff-panel">
          <div class="diff-panel-header">Avant</div>
          <div
            v-for="change in diff.changes"
            :key="change.index"
            class="diff-row"
            :class="changeClass(change)"
          >
            <span class="diff-index">{{ change.index }}</span>
            <span class="diff-badge">{{ changeLabel(change) }}</span>
            <div class="diff-content">
              <p v-if="change.sourceBefore" class="diff-source">
                {{ change.sourceBefore }}
              </p>
              <p v-if="change.targetBefore" class="diff-target">
                {{ change.targetBefore }}
              </p>
              <!-- Line-level diff (côté Avant) -->
              <template v-if="showLineLevel">
                <div
                  v-for="(seg, i) in paragraphLineDiffs(change)"
                  :key="'l-' + i"
                  class="diff-segment"
                  :class="{
                    'seg-equal': seg.type === 'equal',
                    'seg-added': seg.type === 'added',
                    'seg-removed': seg.type === 'removed',
                  }"
                >
                  {{ seg.text }}
                </div>
              </template>
            </div>
          </div>
        </div>
      </template>
      <template #right>
        <div class="diff-panel">
          <div class="diff-panel-header">Après</div>
          <div
            v-for="change in diff.changes"
            :key="change.index"
            class="diff-row"
            :class="changeClass(change)"
          >
            <span class="diff-index">{{ change.index }}</span>
            <span class="diff-badge">{{ changeLabel(change) }}</span>
            <div class="diff-content">
              <p v-if="change.sourceAfter" class="diff-source">
                {{ change.sourceAfter }}
              </p>
              <p v-if="change.targetAfter" class="diff-target">
                {{ change.targetAfter }}
              </p>
              <!-- Line-level diff (côté Après) -->
              <template v-if="showLineLevel">
                <div
                  v-for="(seg, i) in paragraphLineDiffs(change)"
                  :key="'l-' + i"
                  class="diff-segment"
                  :class="{
                    'seg-equal': seg.type === 'equal',
                    'seg-added': seg.type === 'added',
                    'seg-removed': seg.type === 'removed',
                  }"
                >
                  {{ seg.text }}
                </div>
              </template>
            </div>
          </div>
        </div>
      </template>
    </NtSplitPane>

    <!-- Mode unifié -->
    <div v-else class="diff-panel diff-unified">
      <div
        v-for="change in diff.changes"
        :key="change.index"
        class="diff-row"
        :class="changeClass(change)"
      >
        <span class="diff-index">{{ change.index }}</span>
        <span class="diff-badge">{{ changeLabel(change) }}</span>
        <div class="diff-content">
          <!-- Avant (rouge) -->
          <template
            v-if="change.type === 'modified' || change.type === 'removed'"
          >
            <p v-if="change.sourceBefore" class="diff-source diff-before-text">
              <span class="diff-line-prefix">−</span>
              {{ change.sourceBefore }}
            </p>
            <p v-if="change.targetBefore" class="diff-target diff-before-text">
              <span class="diff-line-prefix">−</span>
              {{ change.targetBefore }}
            </p>
          </template>
          <!-- Après (vert) -->
          <template
            v-if="change.type === 'modified' || change.type === 'added'"
          >
            <p v-if="change.sourceAfter" class="diff-source diff-after-text">
              <span class="diff-line-prefix">+</span>
              {{ change.sourceAfter }}
            </p>
            <p v-if="change.targetAfter" class="diff-target diff-after-text">
              <span class="diff-line-prefix">+</span>
              {{ change.targetAfter }}
            </p>
          </template>
          <!-- Line-level diff -->
          <template v-if="showLineLevel">
            <div
              v-for="(seg, i) in paragraphLineDiffs(change)"
              :key="i"
              class="diff-segment"
              :class="{
                'seg-equal': seg.type === 'equal',
                'seg-added': seg.type === 'added',
                'seg-removed': seg.type === 'removed',
              }"
            >
              {{ seg.text }}
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nt-diff-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.diff-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--bg-tertiary);
  flex-shrink: 0;
}

.diff-stats {
  font-size: 13px;
  color: var(--text-secondary);
}

.diff-toggle-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toggle-label {
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.btn-mode {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: none;
  padding: 4px 12px;
  border-radius: var(--border-radius);
  font-size: 13px;
  cursor: pointer;
}

.btn-mode:hover {
  background-color: var(--accent-hover);
}

.diff-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-style: italic;
}

.diff-panel {
  padding: 8px;
  overflow-y: auto;
  height: 100%;
}

.diff-panel-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  padding: 6px 12px;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  margin-bottom: 8px;
}

.diff-unified {
  flex: 1;
}

.diff-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  margin-bottom: 4px;
  border-radius: var(--border-radius);
  border-left: 4px solid transparent;
}

.diff-row.diff-added {
  background-color: rgba(0, 200, 83, 0.08);
  border-left-color: var(--success);
}

.diff-row.diff-removed {
  background-color: rgba(255, 82, 82, 0.08);
  border-left-color: var(--error);
}

.diff-row.diff-modified {
  background-color: rgba(255, 193, 7, 0.08);
  border-left-color: var(--warning);
}

.diff-index {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  background-color: var(--bg-tertiary);
  border-radius: 50%;
  width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  flex-shrink: 0;
}

.diff-badge {
  font-size: 10px;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  flex-shrink: 0;
}

.diff-row.diff-added .diff-badge {
  background-color: var(--success);
  color: white;
}

.diff-row.diff-removed .diff-badge {
  background-color: var(--error);
  color: white;
}

.diff-row.diff-modified .diff-badge {
  background-color: var(--warning);
  color: white;
}

.diff-content {
  flex: 1;
  min-width: 0;
}

.diff-source,
.diff-target {
  margin: 0 0 4px;
  line-height: 1.6;
  font-size: 13px;
  word-break: break-word;
}

.diff-target {
  color: var(--text-secondary);
  font-style: italic;
}

.diff-before-text {
  color: var(--error);
  opacity: 0.8;
}

.diff-after-text {
  color: var(--success);
  opacity: 0.8;
}

.diff-line-prefix {
  font-weight: 700;
  margin-right: 4px;
}

/* Line-level diff segments */
.diff-segment {
  display: inline;
  line-height: 1.6;
  font-size: 13px;
}

.seg-added {
  background-color: rgba(0, 200, 83, 0.2);
}

.seg-removed {
  background-color: rgba(255, 82, 82, 0.2);
  text-decoration: line-through;
}

.seg-equal {
  color: var(--text-secondary);
  opacity: 0.7;
}
</style>
