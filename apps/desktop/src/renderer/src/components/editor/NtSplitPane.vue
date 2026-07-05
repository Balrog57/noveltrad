<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";

const props = withDefaults(
  defineProps<{
    /** Fraction initiale du panneau gauche (en pourcentage) */
    initialSplit?: number;
    /** Largeur minimale de chaque panneau en pixels */
    minWidth?: number;
  }>(),
  { initialSplit: 50, minWidth: 200 },
);

/** Pourcentage courant du panneau gauche */
const splitPercent = ref(props.initialSplit);

/** Référence vers le conteneur racine */
const containerRef = ref<HTMLElement | null>(null);

/** Largeur du conteneur pour le calcul responsive */
const containerWidth = ref(0);

let observer: ResizeObserver | null = null;

onMounted(() => {
  if (containerRef.value) {
    observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        containerWidth.value = entry.contentRect.width;
      }
    });
    observer.observe(containerRef.value);
    containerWidth.value = containerRef.value.offsetWidth;
  }
});

onUnmounted(() => {
  observer?.disconnect();
});

/** Détermine si l'affichage responsive (mode empilé) est actif */
const isStacked = computed(() => containerWidth.value < 1024);

/** Style CSS grid dynamique */
const gridStyle = computed(() => {
  if (isStacked.value) {
    return { gridTemplateColumns: "100%", gridTemplateRows: "50% 1px 50%" };
  }
  return {
    gridTemplateColumns: `${splitPercent.value}% 4px ${100 - splitPercent.value}%`,
    gridTemplateRows: "100%",
  };
});

// --- Gestion du drag du séparateur ---
let dragging = false;
let startX = 0;
let startPercent = 0;

function onDividerMouseDown(e: MouseEvent): void {
  dragging = true;
  startX = e.clientX;
  startPercent = splitPercent.value;
  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
  e.preventDefault();
}

function onMouseMove(e: MouseEvent): void {
  if (!dragging || !containerRef.value) {return;}
  const dx = e.clientX - startX;
  const totalWidth = containerRef.value.offsetWidth;
  const newPercent = startPercent + (dx / totalWidth) * 100;
  const minPercent = (props.minWidth / totalWidth) * 100;
  const maxPercent = 100 - minPercent;
  splitPercent.value = Math.max(minPercent, Math.min(maxPercent, newPercent));
}

function onMouseUp(): void {
  dragging = false;
  document.removeEventListener("mousemove", onMouseMove);
  document.removeEventListener("mouseup", onMouseUp);
}
</script>

<template>
  <div ref="containerRef" class="nt-split-pane" :style="gridStyle">
    <!-- Panneau gauche -->
    <div class="nt-panel nt-panel--left">
      <slot name="left" />
    </div>

    <!-- Séparateur (sauf en mode responsive) -->
    <div
      v-if="!isStacked"
      class="nt-divider"
      :class="{ 'nt-divider--dragging': dragging }"
      @mousedown="onDividerMouseDown"
    />

    <!-- Panneau droit -->
    <div class="nt-panel nt-panel--right">
      <slot name="right" />
    </div>
  </div>
</template>

<style scoped>
.nt-split-pane {
  display: grid;
  height: 100%;
  overflow: hidden;
}

.nt-panel {
  overflow: auto;
  min-width: 0;
  min-height: 0;
}

.nt-panel--left {
  background-color: var(--bg-secondary);
}

.nt-panel--right {
  background-color: var(--bg-primary);
}

.nt-divider {
  background-color: var(--bg-tertiary);
  cursor: col-resize;
  user-select: none;
  transition: background-color 0.15s;
}

.nt-divider:hover,
.nt-divider--dragging {
  background-color: var(--accent);
}
</style>
