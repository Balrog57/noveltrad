<script setup lang="ts">
withDefaults(
  defineProps<{
    /** Valeur de progression (0-100). -1 = indeterminé */
    value: number;
    /** Libellé optionnel affiché à droite de la barre */
    label?: string;
  }>(),
  { label: undefined },
);

/** Pourcentage affiché */
function percentText(value: number): string {
  if (value < 0) {return "...";}
  return `${Math.round(Math.max(0, Math.min(100, value)))}%`;
}

/** Largeur de remplissage */
function fillWidth(value: number): string {
  if (value < 0) {return "100%";}
  return `${Math.max(0, Math.min(100, value))}%`;
}

/** Si la barre est en mode indéterminé */
function isIndeterminate(value: number): boolean {
  return value < 0;
}
</script>

<template>
  <div class="nt-progress">
    <div class="nt-progress-track">
      <div
        class="nt-progress-fill"
        :class="{ 'nt-progress-fill--indeterminate': isIndeterminate(value) }"
        :style="{ width: fillWidth(value) }"
      />
    </div>
    <span
      v-if="label !== undefined || !isIndeterminate(value)"
      class="nt-progress-label"
    >
      {{ label ?? percentText(value) }}
    </span>
  </div>
</template>

<style scoped>
.nt-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nt-progress-track {
  flex: 1;
  height: 8px;
  background-color: var(--bg-tertiary);
  border-radius: 999px;
  overflow: hidden;
}

.nt-progress-fill {
  height: 100%;
  background-color: var(--accent);
  border-radius: 999px;
  transition: width 0.3s ease;
}

.nt-progress-fill--indeterminate {
  width: 40% !important;
  animation: nt-progress-indeterminate 1.5s ease-in-out infinite;
}

@keyframes nt-progress-indeterminate {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(350%);
  }
}

.nt-progress-label {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
