<script setup lang="ts">
defineProps<{
  icon: string;
  title: string;
  description?: string;
  actionLabel?: string;
}>();

const emit = defineEmits<{
  action: [];
}>();
</script>

<template>
  <div class="nt-empty-state">
    <span class="nt-empty-icon" aria-hidden="true">{{ icon }}</span>
    <h3 class="nt-empty-title">{{ title }}</h3>
    <p v-if="description" class="nt-empty-description">{{ description }}</p>
    <button
      v-if="actionLabel"
      type="button"
      class="nt-empty-action"
      @click="emit('action')"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>

<style scoped>
.nt-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
  color: var(--text-secondary);
}

.nt-empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.nt-empty-title {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.nt-empty-description {
  margin: 0 0 20px 0;
  font-size: 14px;
  max-width: 320px;
  line-height: 1.5;
}

.nt-empty-action {
  padding: 10px 20px;
  background-color: var(--accent);
  color: #0f172a;
  border: none;
  border-radius: var(--border-radius);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition:
    opacity 0.15s ease,
    transform 0.1s ease;
}

.nt-empty-action:hover {
  opacity: 0.85;
}

.nt-empty-action:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.nt-empty-action:active {
  transform: scale(0.97);
}
</style>
