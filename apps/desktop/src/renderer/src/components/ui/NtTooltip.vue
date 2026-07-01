<script setup lang="ts">
withDefaults(
  defineProps<{
    text: string;
    position?: "top" | "bottom" | "left" | "right";
  }>(),
  { position: "top" },
);
</script>

<template>
  <span class="nt-tooltip-wrapper">
    <slot />
    <span
      class="nt-tooltip"
      :class="`nt-tooltip--${position}`"
      role="tooltip"
    >
      {{ text }}
    </span>
  </span>
</template>

<style scoped>
.nt-tooltip-wrapper {
  position: relative;
  display: inline-flex;
  cursor: pointer;
}

.nt-tooltip {
  position: absolute;
  z-index: 1000;
  padding: 6px 10px;
  font-size: 12px;
  line-height: 1.3;
  color: #fff;
  background-color: #1e293b;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
}

.nt-tooltip-wrapper:hover .nt-tooltip {
  opacity: 1;
}

.nt-tooltip--top {
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
}

.nt-tooltip--top::after {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: #1e293b;
}

.nt-tooltip--bottom {
  top: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
}

.nt-tooltip--bottom::after {
  content: "";
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-bottom-color: #1e293b;
}

.nt-tooltip--left {
  right: calc(100% + 6px);
  top: 50%;
  transform: translateY(-50%);
}

.nt-tooltip--left::after {
  content: "";
  position: absolute;
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  border: 4px solid transparent;
  border-left-color: #1e293b;
}

.nt-tooltip--right {
  left: calc(100% + 6px);
  top: 50%;
  transform: translateY(-50%);
}

.nt-tooltip--right::after {
  content: "";
  position: absolute;
  right: 100%;
  top: 50%;
  transform: translateY(-50%);
  border: 4px solid transparent;
  border-right-color: #1e293b;
}
</style>
