<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    /** Variante visuelle du bouton */
    variant?: "primary" | "secondary" | "danger" | "ghost";
    /** Taille du bouton */
    size?: "sm" | "md" | "lg";
    /** Affiche un spinner et désactive le clic */
    loading?: boolean;
    /** Désactive le bouton (opacité réduite, curseur not-allowed) */
    disabled?: boolean;
    /** Type HTML du bouton */
    type?: "button" | "submit" | "reset";
  }>(),
  {
    variant: "primary",
    size: "md",
    loading: false,
    disabled: false,
    type: "button",
  },
);

const emit = defineEmits<{
  /** Émis au clic (sauf si loading ou disabled) */
  click: [event: MouseEvent];
}>();

/** Le bouton est-il inactif ? */
function isInactive(): boolean {
  return props.loading || props.disabled;
}

/** Gère le clic : bloque si loading ou disabled */
function onClick(event: MouseEvent): void {
  if (isInactive()) {return;}
  emit("click", event);
}
</script>

<template>
  <button
    class="nt-button"
    :class="[
      `nt-button--${variant}`,
      `nt-button--${size}`,
      { 'nt-button--loading': loading, 'nt-button--disabled': disabled },
    ]"
    :type="type"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    :aria-disabled="disabled || undefined"
    @click="onClick"
  >
    <span v-if="loading" class="nt-button-spinner" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.nt-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  border-radius: var(--border-radius);
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    opacity 0.15s ease,
    transform 0.1s ease;
  white-space: nowrap;
  line-height: 1;
}

.nt-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.nt-button:active:not(.nt-button--disabled):not(.nt-button--loading) {
  transform: scale(0.97);
}

/* --- Tailles --- */

.nt-button--sm {
  font-size: 12px;
  padding: 5px 10px;
}

.nt-button--md {
  font-size: 14px;
  padding: 8px 16px;
}

.nt-button--lg {
  font-size: 16px;
  padding: 12px 24px;
}

/* --- Variantes --- */

.nt-button--primary {
  background-color: var(--accent);
  color: #0f172a;
}

.nt-button--primary:hover:not(.nt-button--disabled):not(.nt-button--loading) {
  background-color: var(--accent-hover);
}

.nt-button--secondary {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.nt-button--secondary:hover:not(.nt-button--disabled):not(.nt-button--loading) {
  background-color: var(--accent-hover);
  color: #0f172a;
}

.nt-button--danger {
  background-color: var(--error);
  color: #fff;
}

.nt-button--danger:hover:not(.nt-button--disabled):not(.nt-button--loading) {
  opacity: 0.85;
}

.nt-button--ghost {
  background-color: transparent;
  color: var(--text-secondary);
}

.nt-button--ghost:hover:not(.nt-button--disabled):not(.nt-button--loading) {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

/* --- États --- */

.nt-button--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.nt-button--loading {
  cursor: wait;
}

.nt-button-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: nt-button-spin 0.6s linear infinite;
}

@keyframes nt-button-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
