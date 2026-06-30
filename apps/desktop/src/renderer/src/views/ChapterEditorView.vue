<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "../stores/project";
import { useEditorStore } from "../stores/editor";
import NtSplitPane from "../components/editor/NtSplitPane.vue";
import type { Paragraph } from "@shared/types/index.js";

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const editorStore = useEditorStore();

const projectId = computed(() => route.params.projectId as string);
const chapterId = computed(() => route.params.chapterId as string);

/** Titre du chapitre courant (récupéré depuis le store projet) */
const chapterTitle = computed(() => {
  const ch = projectStore.chapters.find((c) => c.id === chapterId.value);
  return ch?.title ?? "Chapitre sans titre";
});

/** Statut du chapitre courant */
const chapterStatus = computed(() => {
  const ch = projectStore.chapters.find((c) => c.id === chapterId.value);
  return ch?.status ?? "pending";
});

// --- Références pour le scroll lié ---
const leftPanelRef = ref<HTMLElement | null>(null);
const rightPanelRef = ref<HTMLElement | null>(null);

// --- Références vers les éléments de paragraphe (pour IntersectionObserver) ---
const sourceParagraphRefs = ref<Map<string, HTMLElement>>(new Map());
const targetParagraphRefs = ref<Map<string, HTMLElement>>(new Map());

/** Paragraphe actuellement visible dans le panneau source */
const visibleSourceIndex = ref(0);
/** Paragraphe actuellement visible dans le panneau cible */
const visibleTargetIndex = ref(0);

// Flag pour éviter les boucles de scroll réciproques
let syncingScroll = false;

// --- IntersectionObserver pour le panneau source ---
let sourceObserver: IntersectionObserver | null = null;
let targetObserver: IntersectionObserver | null = null;

function setupSourceObserver(): void {
  if (!leftPanelRef.value) return;
  sourceObserver?.disconnect();
  sourceObserver = new IntersectionObserver(
    (entries) => {
      if (syncingScroll) return;
      const visible = entries.filter((e) => e.isIntersecting);
      if (visible.length === 0) return;
      const indices = visible
        .map((e) => {
          const el = e.target as HTMLElement;
          return Number(el.dataset.paragraphIndex) || 0;
        })
        .sort((a, b) => a - b);
      visibleSourceIndex.value = indices[0];
    },
    { root: leftPanelRef.value, threshold: 0.5 },
  );
}

function setupTargetObserver(): void {
  if (!rightPanelRef.value) return;
  targetObserver?.disconnect();
  targetObserver = new IntersectionObserver(
    (entries) => {
      if (syncingScroll) return;
      const visible = entries.filter((e) => e.isIntersecting);
      if (visible.length === 0) return;
      const indices = visible
        .map((e) => {
          const el = e.target as HTMLElement;
          return Number(el.dataset.paragraphIndex) || 0;
        })
        .sort((a, b) => a - b);
      visibleTargetIndex.value = indices[0];
    },
    { root: rightPanelRef.value, threshold: 0.5 },
  );
}

/**
 * Synchronise le scroll entre les panneaux.
 * Quand l'utilisateur fait défiler le panneau source → le panneau cible suit.
 */
function syncTargetScroll(): void {
  if (syncingScroll || !rightPanelRef.value) return;
  syncingScroll = true;
  const targetEl = targetParagraphRefs.value.get(
    `target-${visibleSourceIndex.value}`,
  );
  if (targetEl) {
    targetEl.scrollIntoView({ block: "start", behavior: "instant" });
  }
  // Fix 2 : Réinitialiser le flag de manière asynchrone pour éviter la boucle infinie
  // Les callbacks IntersectionObserver s'exécutent après les microtasks,
  // donc si on réinitialise trop tôt, l'observer se déclenche à nouveau.
  nextTick(() => {
    syncingScroll = false;
  });
}

/**
 * Synchronise le scroll quand l'utilisateur fait défiler le panneau cible → le panneau source suit.
 */
function syncSourceScroll(): void {
  if (syncingScroll || !leftPanelRef.value) return;
  syncingScroll = true;
  const sourceEl = sourceParagraphRefs.value.get(
    `source-${visibleTargetIndex.value}`,
  );
  if (sourceEl) {
    sourceEl.scrollIntoView({ block: "start", behavior: "instant" });
  }
  // Fix 2 : Réinitialiser le flag de manière asynchrone pour éviter la boucle infinie
  nextTick(() => {
    syncingScroll = false;
  });
}

// Observer le paragraphe visible dans le panneau source → faire défiler le panneau cible
watch(visibleSourceIndex, () => {
  nextTick(() => syncTargetScroll());
});

// Observer le paragraphe visible dans le panneau cible → faire défiler le panneau source
watch(visibleTargetIndex, () => {
  nextTick(() => syncSourceScroll());
});

// --- Fonctions d'enregistrement des refs de paragraphes ---
function setSourceRef(index: number, el: HTMLElement | null): void {
  if (el) {
    sourceParagraphRefs.value.set(`source-${index}`, el);
    sourceObserver?.observe(el);
  }
}

function setTargetRef(index: number, el: HTMLElement | null): void {
  if (el) {
    targetParagraphRefs.value.set(`target-${index}`, el);
    targetObserver?.observe(el);
  }
}

// --- Actions sur les paragraphes ---
function onTranslationBlur(paragraph: Paragraph): void {
  editorStore.updateParagraph(paragraph);
  // Auto-save différé
  debouncedSave();
}

function onTranslationInput(paragraph: Paragraph, event: Event): void {
  const target = event.target as HTMLTextAreaElement;
  const updated: Paragraph = { ...paragraph, translatedText: target.value };
  if (updated.translatedText && updated.translatedText.trim().length > 0) {
    updated.status = "translated";
  }
  // Fix 8 : Utiliser le store au lieu de muter l'objet directement
  editorStore.updateParagraph(updated);
}

// --- Sauvegarde avec debounce ---
let saveTimer: ReturnType<typeof setTimeout> | null = null;
function debouncedSave(): void {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    editorStore.saveAll();
  }, 2000); // 2 secondes après la dernière modification
}

async function saveManually(): Promise<void> {
  if (saveTimer) clearTimeout(saveTimer);
  await editorStore.saveAll();
}

// --- Menu contextuel (clic droit sur un paragraphe) ---
const contextMenu = ref<{
  x: number;
  y: number;
  paragraphId: string;
  index: number;
} | null>(null);

function onContextMenu(
  event: MouseEvent,
  paragraphId: string,
  index: number,
): void {
  event.preventDefault();
  // Fix 7 : Clamper la position pour que le menu reste dans la fenêtre
  const menuWidth = 240;
  const menuHeight = 140;
  const x = Math.max(0, Math.min(event.clientX, window.innerWidth - menuWidth));
  const y = Math.max(
    0,
    Math.min(event.clientY, window.innerHeight - menuHeight),
  );
  contextMenu.value = { x, y, paragraphId, index };
}

function closeContextMenu(): void {
  contextMenu.value = null;
}

function copySource(index: number): void {
  const text = editorStore.paragraphs[index]?.sourceText ?? "";
  navigator.clipboard.writeText(text);
  closeContextMenu();
}

function copyTranslation(index: number): void {
  const text = editorStore.paragraphs[index]?.translatedText ?? "";
  navigator.clipboard.writeText(text);
  closeContextMenu();
}

function resetTranslation(id: string): void {
  editorStore.resetParagraph(id);
  closeContextMenu();
}

// --- Navigation ---
function goBack(): void {
  router.push({ name: "chapters", params: { projectId: projectId.value } });
}

// --- Cycle de vie ---
onMounted(async () => {
  await editorStore.loadChapter(chapterId.value);
  // Charger les chapitres si pas encore fait
  if (projectStore.chapters.length === 0 && projectStore.currentProject) {
    projectStore.chapters = await window.novelTradAPI.invoke(
      "chapter:list",
      projectId.value,
    );
  }
  await nextTick();
  setupSourceObserver();
  setupTargetObserver();
  // Fix 1 : Observer tous les paragraphes déjà montés avant que les observers ne soient créés
  for (const [, el] of sourceParagraphRefs.value) {
    sourceObserver?.observe(el);
  }
  for (const [, el] of targetParagraphRefs.value) {
    targetObserver?.observe(el);
  }
});

onUnmounted(() => {
  if (saveTimer) clearTimeout(saveTimer);
  sourceObserver?.disconnect();
  targetObserver?.disconnect();
});
</script>

<template>
  <div class="chapter-editor">
    <!-- Barre d'outils -->
    <header class="toolbar">
      <div class="toolbar-left">
        <button class="btn-toolbar" @click="goBack">← Retour</button>
        <h2 class="chapter-title">{{ chapterTitle }}</h2>
        <span class="badge" :class="chapterStatus">{{ chapterStatus }}</span>
      </div>
      <div class="toolbar-right">
        <button class="btn-toolbar">Traduire</button>
        <button class="btn-toolbar">Exporter</button>
        <button class="btn-toolbar">Historique</button>
        <button
          class="btn-toolbar btn-save"
          :class="{ 'has-changes': editorStore.hasUnsavedChanges }"
          @click="saveManually"
        >
          {{ editorStore.hasUnsavedChanges ? "● Enregistrer" : "Enregistrer" }}
        </button>
      </div>
    </header>

    <!-- Éditeur principal -->
    <div class="editor-content">
      <p v-if="editorStore.loading" class="status-msg">
        Chargement des paragraphes...
      </p>
      <p v-else-if="editorStore.error" class="status-msg error">
        {{ editorStore.error }}
      </p>
      <p v-else-if="!editorStore.paragraphs.length" class="status-msg">
        Aucun paragraphe dans ce chapitre.
      </p>

      <NtSplitPane v-else :initial-split="40">
        <!-- Panneau gauche : texte source (lecture seule) -->
        <template #left>
          <div ref="leftPanelRef" class="panel source-panel">
            <div
              v-for="(paragraph, index) in editorStore.paragraphs"
              :key="paragraph.id"
              :ref="(el) => setSourceRef(index, el as HTMLElement | null)"
              class="paragraph-block source-block"
              :data-paragraph-index="index"
              @contextmenu="onContextMenu($event, paragraph.id, index)"
            >
              <span class="paragraph-number">{{
                paragraph.indexInChapter
              }}</span>
              <p class="source-text">{{ paragraph.sourceText }}</p>
            </div>
          </div>
        </template>

        <!-- Panneau droit : texte traduit (éditable) -->
        <template #right>
          <div ref="rightPanelRef" class="panel target-panel">
            <div
              v-for="(paragraph, index) in editorStore.paragraphs"
              :key="paragraph.id"
              :ref="(el) => setTargetRef(index, el as HTMLElement | null)"
              class="paragraph-block target-block"
              :class="{ 'is-dirty': editorStore.isDirty(paragraph.id) }"
              :data-paragraph-index="index"
              @contextmenu="onContextMenu($event, paragraph.id, index)"
            >
              <div class="paragraph-header">
                <span class="paragraph-number">{{
                  paragraph.indexInChapter
                }}</span>
                <span v-if="editorStore.isDirty(paragraph.id)" class="dirty-dot"
                  >●</span
                >
              </div>
              <textarea
                class="translation-textarea"
                :value="paragraph.translatedText ?? ''"
                :placeholder="`Traduction du paragraphe ${paragraph.indexInChapter}...`"
                @input="onTranslationInput(paragraph, $event)"
                @blur="onTranslationBlur(paragraph)"
              />
            </div>
          </div>
        </template>
      </NtSplitPane>
    </div>

    <!-- Menu contextuel -->
    <Teleport to="body">
      <div
        v-if="contextMenu"
        class="context-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        @click.stop
      >
        <button class="context-item" @click="copySource(contextMenu.index)">
          Copier la source
        </button>
        <button
          class="context-item"
          @click="copyTranslation(contextMenu.index)"
        >
          Copier la traduction
        </button>
        <button
          class="context-item context-item--danger"
          @click="resetTranslation(contextMenu.paragraphId)"
        >
          Réinitialiser la traduction
        </button>
      </div>
    </Teleport>

    <!-- Overlay pour fermer le menu contextuel -->
    <div v-if="contextMenu" class="context-overlay" @click="closeContextMenu" />
  </div>
</template>

<style scoped>
.chapter-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* --- Barre d'outils --- */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--bg-tertiary);
  gap: 16px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chapter-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-toolbar {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: none;
  padding: 6px 14px;
  border-radius: var(--border-radius);
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.15s;
}

.btn-toolbar:hover {
  background-color: var(--accent-hover);
}

.btn-save.has-changes {
  background-color: var(--accent);
  color: white;
}

.badge {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
  text-transform: uppercase;
}

.badge.completed {
  background-color: var(--success);
  color: white;
}

.badge.processing {
  background-color: var(--warning);
  color: white;
}

.badge.error {
  background-color: var(--error);
  color: white;
}

/* --- Contenu éditeur --- */
.editor-content {
  flex: 1;
  overflow: hidden;
}

.status-msg {
  padding: 24px;
  color: var(--text-secondary);
  text-align: center;
}

.status-msg.error {
  color: var(--error);
}

/* --- Panneaux --- */
.panel {
  padding: 12px;
  height: 100%;
}

/* --- Bloc paragraphe --- */
.paragraph-block {
  padding: 12px 8px;
  border-bottom: 1px solid var(--bg-tertiary);
}

.paragraph-block:last-child {
  border-bottom: none;
}

.paragraph-number {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  background-color: var(--bg-tertiary);
  border-radius: 50%;
  width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  margin-right: 8px;
  flex-shrink: 0;
}

.source-text {
  display: inline;
  color: var(--text-primary);
  line-height: 1.7;
  margin: 0;
  font-size: 14px;
}

/* --- Bloc cible --- */
.target-block {
  border-left: 3px solid transparent;
  transition: border-color 0.2s;
}

.target-block.is-dirty {
  border-left-color: var(--warning);
}

.paragraph-header {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}

.dirty-dot {
  color: var(--warning);
  font-size: 14px;
  margin-left: 4px;
}

.translation-textarea {
  width: 100%;
  min-height: 60px;
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.7;
  resize: vertical;
  outline: none;
  transition: border-color 0.2s;
}

.translation-textarea:focus {
  border-color: var(--accent);
}

.translation-textarea::placeholder {
  color: var(--text-secondary);
  font-style: italic;
}

/* --- Menu contextuel --- */
.context-menu {
  position: fixed;
  z-index: 1000;
  background-color: var(--bg-secondary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  padding: 4px 0;
  min-width: 220px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.context-item {
  display: block;
  width: 100%;
  padding: 8px 16px;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}

.context-item:hover {
  background-color: var(--bg-tertiary);
}

.context-item--danger {
  color: var(--error);
}

.context-overlay {
  position: fixed;
  inset: 0;
  z-index: 999;
}
</style>
