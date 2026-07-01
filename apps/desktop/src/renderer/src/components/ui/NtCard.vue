<script setup lang="ts">
withDefaults(
  defineProps<{
    /** Titre affiché dans l'en-tête (optionnel) */
    title?: string;
  }>(),
  { title: undefined },
);
</script>

<template>
  <div class="nt-card">
    <header
      v-if="title || $slots.header || $slots.actions"
      class="nt-card-header"
    >
      <slot name="header">
        <h3 v-if="title" class="nt-card-title">{{ title }}</h3>
      </slot>
      <div v-if="$slots.actions" class="nt-card-actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="nt-card-body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.nt-card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.nt-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.nt-card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}

.nt-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.nt-card-body {
  flex: 1;
  min-width: 0;
}
</style>
