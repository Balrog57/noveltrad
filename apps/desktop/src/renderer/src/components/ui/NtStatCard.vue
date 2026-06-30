<script setup lang="ts">
withDefaults(
  defineProps<{
    /** Icône (emoji ou caractère) */
    icon: string;
    /** Valeur à afficher */
    value: string | number;
    /** Libellé descriptif */
    label: string;
    /** Couleur d'accent (CSS color value) */
    color?: string;
  }>(),
  { color: "var(--accent)" },
);
</script>

<template>
  <div class="nt-stat-card">
    <div class="nt-stat-card-icon" :style="{ color }">{{ icon }}</div>
    <div class="nt-stat-card-content">
      <span class="nt-stat-card-value">{{ value }}</span>
      <span class="nt-stat-card-label">{{ label }}</span>
    </div>
  </div>
</template>

<style scoped>
.nt-stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background-color: var(--bg-secondary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  min-width: 140px;
}

.nt-stat-card-icon {
  font-size: 24px;
  line-height: 1;
  flex-shrink: 0;
}

.nt-stat-card-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.nt-stat-card-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.nt-stat-card-label {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
