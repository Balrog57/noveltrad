<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: "default" | "success" | "warning" | "error" | "info";
    size?: "sm" | "md";
  }>(),
  { variant: "default", size: "md" },
);
</script>

<template>
  <span class="nt-badge" :class="[`nt-badge--${variant}`, `nt-badge--${size}`]">
    <slot />
  </span>
</template>

<style scoped>
.nt-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  border-radius: 999px;
  white-space: nowrap;
  line-height: 1;
}

.nt-badge--sm {
  font-size: 11px;
  padding: 2px 6px;
}

.nt-badge--md {
  font-size: 12px;
  padding: 3px 8px;
}

.nt-badge--default {
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
}

.nt-badge--success {
  background-color: var(--success);
  color: #fff;
}

.nt-badge--warning {
  background-color: var(--warning);
  color: #1e293b;
}

.nt-badge--error {
  background-color: var(--error);
  color: #fff;
}

.nt-badge--info {
  background-color: var(--accent);
  color: #0f172a;
}
</style>
