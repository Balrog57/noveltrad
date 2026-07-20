<script setup lang="ts">
import { computed, ref } from "vue";

/** Option du select */
export interface SelectOption {
  /** Valeur de l'option */
  value: string;
  /** Libellé affiché */
  label: string;
}

const props = withDefaults(
  defineProps<{
    /** Valeur liée (v-model) */
    modelValue?: string;
    /** Libellé affiché au-dessus du champ */
    label?: string;
    /** Désactive le champ */
    disabled?: boolean;
    /** Liste des options { value, label } */
    options: SelectOption[];
    /** Identifiant accessible (généré si absent) */
    id?: string;
    /** Champ obligatoire */
    required?: boolean;
  }>(),
  {
    modelValue: "",
    label: undefined,
    disabled: false,
    id: undefined,
    required: false,
  },
);

const emit = defineEmits<{
  /** Émis au changement de valeur (v-model) */
  "update:modelValue": [value: string];
}>();

/** Identifiant unique généré si non fourni */
const generatedId = ref(`nt-select-${Math.random().toString(36).slice(2, 9)}`);
const selectId = computed(() => props.id ?? generatedId.value);

/** Gère le changement de sélection */
function onChange(event: Event): void {
  const target = event.target as HTMLSelectElement;
  emit("update:modelValue", target.value);
}
</script>

<template>
  <div
    class="nt-select-wrapper"
    :class="{ 'nt-select-wrapper--disabled': disabled }"
  >
    <label v-if="label" class="nt-select-label" :for="selectId">
      {{ label }}
      <span v-if="required" class="nt-required-indicator" aria-hidden="true">*</span>
    </label>
    <div class="nt-select-field">
      <select
        :id="selectId"
        class="nt-select"
        :value="modelValue"
        :disabled="disabled"
        :required="required"
        :aria-required="required || undefined"
        @change="onChange"
      >
        <option v-for="opt in options" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
      <span class="nt-select-arrow" aria-hidden="true">▾</span>
    </div>
  </div>
</template>

<style scoped>
.nt-select-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.nt-select-wrapper--disabled {
  opacity: 0.5;
}

.nt-select-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.nt-select-field {
  position: relative;
  display: flex;
  align-items: center;
  background-color: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: var(--border-radius);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.nt-select-field:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

.nt-select {
  flex: 1;
  padding: 8px 28px 8px 12px;
  background: transparent;
  border: none;
  border-radius: var(--border-radius);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 14px;
  outline: none;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  min-width: 0;
}

.nt-select:disabled {
  cursor: not-allowed;
}

.nt-select option {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
}

.nt-select-arrow {
  position: absolute;
  right: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  pointer-events: none;
}

.nt-required-indicator {
  color: var(--error);
  margin-left: 2px;
}
</style>
