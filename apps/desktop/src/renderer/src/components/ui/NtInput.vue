<script setup lang="ts">
import { computed, ref } from "vue";

const props = withDefaults(
  defineProps<{
    /** Valeur liée (v-model) */
    modelValue?: string;
    /** Libellé affiché au-dessus du champ */
    label?: string;
    /** Message d'erreur affiché sous le champ */
    error?: string;
    /** Icône optionnelle (emoji ou caractère) affichée à gauche */
    icon?: string;
    /** Désactive le champ */
    disabled?: boolean;
    /** Placeholder */
    placeholder?: string;
    /** Type HTML de l'input */
    type?: string;
    /** Identifiant accessible (généré si absent) */
    id?: string;
  }>(),
  {
    modelValue: "",
    label: undefined,
    error: undefined,
    icon: undefined,
    disabled: false,
    placeholder: undefined,
    type: "text",
    id: undefined,
  },
);

const emit = defineEmits<{
  /** Émis à chaque changement de valeur (v-model) */
  "update:modelValue": [value: string];
}>();

/** Identifiant unique généré si non fourni */
const generatedId = ref(`nt-input-${Math.random().toString(36).slice(2, 9)}`);
const inputId = computed(() => props.id ?? generatedId.value);

/** Le champ a-t-il une erreur ? */
const hasError = computed(() => Boolean(props.error));

/** Gère la saisie */
function onInput(event: Event): void {
  const target = event.target as HTMLInputElement;
  emit("update:modelValue", target.value);
}
</script>

<template>
  <div
    class="nt-input-wrapper"
    :class="{ 'nt-input-wrapper--disabled': disabled }"
  >
    <label v-if="label" class="nt-input-label" :for="inputId">{{
      label
    }}</label>
    <div class="nt-input-field" :class="{ 'nt-input-field--error': hasError }">
      <span v-if="icon" class="nt-input-icon" aria-hidden="true">{{
        icon
      }}</span>
      <input
        :id="inputId"
        class="nt-input"
        :class="{ 'nt-input--with-icon': icon }"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :aria-invalid="hasError || undefined"
        :aria-describedby="error ? `${inputId}-error` : undefined"
        @input="onInput"
      />
    </div>
    <p
      v-if="error"
      :id="`${inputId}-error`"
      class="nt-input-error"
      role="alert"
    >
      {{ error }}
    </p>
  </div>
</template>

<style scoped>
.nt-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.nt-input-wrapper--disabled {
  opacity: 0.5;
}

.nt-input-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.nt-input-field {
  display: flex;
  align-items: center;
  background-color: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: var(--border-radius);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.nt-input-field:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

.nt-input-field--error {
  border-color: var(--error);
}

.nt-input-field--error:focus-within {
  box-shadow: 0 0 0 1px var(--error);
}

.nt-input-icon {
  padding-left: 10px;
  font-size: 14px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.nt-input {
  flex: 1;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: var(--border-radius);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 14px;
  outline: none;
  min-width: 0;
}

.nt-input::placeholder {
  color: var(--text-secondary);
}

.nt-input:disabled {
  cursor: not-allowed;
}

.nt-input--with-icon {
  padding-left: 6px;
}

.nt-input-error {
  margin: 0;
  font-size: 12px;
  color: var(--error);
  line-height: 1.3;
}
</style>
