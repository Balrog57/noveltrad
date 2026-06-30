<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";

const props = withDefaults(
  defineProps<{
    /** Message affiché dans le toast */
    message: string;
    /** Type de notification */
    type: "success" | "error" | "info" | "warning";
    /** Durée d'affichage en ms (0 = ne pas auto-fermer, les erreurs persistent) */
    duration?: number;
  }>(),
  { duration: 4000 },
);

const emit = defineEmits<{
  /** Émis quand le toast se ferme (auto ou manuel) */
  close: [];
}>();

const visible = ref(true);
let timer: ReturnType<typeof setTimeout> | null = null;

/** Couleur de fond selon le type */
function bgColor(): string {
  switch (props.type) {
    case "success":
      return "var(--success)";
    case "error":
      return "var(--error)";
    case "warning":
      return "var(--warning)";
    case "info":
      return "var(--accent)";
  }
}

/** Icône selon le type */
function icon(): string {
  switch (props.type) {
    case "success":
      return "\u2713";
    case "error":
      return "\u2717";
    case "warning":
      return "\u26a0";
    case "info":
      return "\u2139";
  }
}

function dismiss(): void {
  visible.value = false;
  // Délai pour laisser l'animation de sortie se jouer
  setTimeout(() => {
    emit("close");
  }, 300);
}

onMounted(() => {
  // Pas d'auto-dismiss pour les erreurs
  if (props.type === "error") return;
  if (props.duration > 0) {
    timer = setTimeout(dismiss, props.duration);
  }
});

onUnmounted(() => {
  if (timer) clearTimeout(timer);
});
</script>

<template>
  <Teleport to="body">
    <Transition name="nt-toast-slide">
      <div
        v-if="visible"
        class="nt-toast"
        :class="`nt-toast--${type}`"
        role="alert"
        :aria-live="type === 'error' ? 'assertive' : 'polite'"
      >
        <span class="nt-toast-icon">{{ icon() }}</span>
        <span class="nt-toast-message">{{ message }}</span>
        <button class="nt-toast-close" aria-label="Fermer" @click="dismiss">
          \u2715
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.nt-toast {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 2000;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--border-radius);
  font-size: 14px;
  color: #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  max-width: 420px;
  min-width: 280px;
  pointer-events: all;
}

.nt-toast--success {
  background-color: var(--success);
}

.nt-toast--error {
  background-color: var(--error);
}

.nt-toast--warning {
  background-color: var(--warning);
  color: #1e293b;
}

.nt-toast--info {
  background-color: var(--accent);
  color: #0f172a;
}

.nt-toast-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.nt-toast-message {
  flex: 1;
  line-height: 1.4;
}

.nt-toast-close {
  background: none;
  border: none;
  color: inherit;
  opacity: 0.7;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  flex-shrink: 0;
}

.nt-toast-close:hover {
  opacity: 1;
}

/* Animation slide-in depuis le haut-droit */
.nt-toast-slide-enter-active {
  transition: all 0.3s ease;
}

.nt-toast-slide-leave-active {
  transition: all 0.3s ease;
}

.nt-toast-slide-enter-from {
  opacity: 0;
  transform: translateY(-20px) translateX(20px);
}

.nt-toast-slide-leave-to {
  opacity: 0;
  transform: translateY(-20px) translateX(20px);
}
</style>
