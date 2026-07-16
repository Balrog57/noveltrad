<script setup lang="ts">
import { watch, onMounted, onUnmounted, ref, nextTick } from "vue";

const props = withDefaults(
  defineProps<{
    /** Visibilité du modal */
    visible: boolean;
    /** Titre affiché dans l'en-tête */
    title: string;
    /** Taille du modal */
    size?: "sm" | "md" | "lg";
  }>(),
  { size: "md" },
);

const emit = defineEmits<{
  /** Émis quand l'utilisateur ferme le modal */
  close: [];
}>();

const modalRef = ref<HTMLElement | null>(null);
const visibleLocal = ref(false);

// Synchroniser la visibilité locale avec la prop (avec délai pour animation)
watch(
  () => props.visible,
  (val) => {
    if (val) {
      visibleLocal.value = true;
      nextTick(() => focusTrap());
    } else {
      // Délai pour laisser l'animation de sortie se jouer
      setTimeout(() => {
        visibleLocal.value = false;
      }, 150);
    }
  },
  { immediate: true },
);

/** Gestionnaire clavier : Échap pour fermer */
function onKeydown(e: KeyboardEvent): void {
  if (!props.visible) {return;}
  if (e.key === "Escape") {
    emit("close");
  }
  // Focus trap : Tab dans le modal
  if (e.key === "Tab" && modalRef.value) {
    const focusable = modalRef.value.querySelectorAll<HTMLElement>(
      'input, button, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    if (focusable.length === 0) {return;}
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }
}

function focusTrap(): void {
  nextTick(() => {
    const firstInput = modalRef.value?.querySelector<HTMLElement>(
      'input, button, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    firstInput?.focus();
  });
}

onMounted(() => {
  document.addEventListener("keydown", onKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", onKeydown);
});

const sizeClass = {
  sm: "nt-modal--sm",
  md: "nt-modal--md",
  lg: "nt-modal--lg",
};
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visibleLocal || visible"
      class="nt-modal-overlay"
      :class="{ 'nt-modal-overlay--visible': visible }"
      @click.self="emit('close')"
    >
      <div
        ref="modalRef"
        class="nt-modal"
        :class="sizeClass[size]"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
      >
        <!-- En-tête -->
        <header class="nt-modal-header">
          <h2 class="nt-modal-title">{{ title }}</h2>
          <button
            class="nt-modal-close"
            aria-label="Fermer"
            title="Fermer"
            @click="emit('close')"
          >
            ✕
          </button>
        </header>

        <!-- Corps -->
        <div class="nt-modal-body">
          <slot />
        </div>

        <!-- Pied -->
        <footer v-if="$slots.footer" class="nt-modal-footer">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.nt-modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.nt-modal-overlay--visible {
  opacity: 1;
}

.nt-modal {
  background-color: var(--bg-primary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  transform: scale(0.95);
  transition: transform 0.15s ease;
}

.nt-modal-overlay--visible .nt-modal {
  transform: scale(1);
}

.nt-modal--sm {
  width: 400px;
}

.nt-modal--md {
  width: 560px;
}

.nt-modal--lg {
  width: 720px;
}

.nt-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--bg-tertiary);
}

.nt-modal-title {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
}

.nt-modal-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  line-height: 1;
}

.nt-modal-close:hover {
  color: var(--text-primary);
  background-color: var(--bg-tertiary);
}

.nt-modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.nt-modal-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--bg-tertiary);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
