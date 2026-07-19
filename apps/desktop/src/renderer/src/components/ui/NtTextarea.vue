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
    /** Désactive le champ */
    disabled?: boolean;
    /** Placeholder */
    placeholder?: string;
    /** Nombre de lignes visibles */
    rows?: number;
    /** Identifiant accessible (généré si absent) */
    id?: string;
    /** Indique si le champ est obligatoire */
    required?: boolean;
  }>(),
  {
    modelValue: "",
    label: undefined,
    error: undefined,
    disabled: false,
    placeholder: undefined,
    rows: 4,
    id: undefined,
    required: false,
  },
);

const emit = defineEmits<{
  /** Émis à chaque changement de valeur (v-model) */
  "update:modelValue": [value: string];
}>();

/** Identifiant unique généré si non fourni */
const generatedId = ref(
  `nt-textarea-${Math.random().toString(36).slice(2, 9)}`,
);
const textareaId = computed(() => props.id ?? generatedId.value);

/** Le champ a-t-il une erreur ? */
const hasError = computed(() => Boolean(props.error));

/** Gère la saisie */
function onInput(event: Event): void {
  const target = event.target as HTMLTextAreaElement;
  emit("update:modelValue", target.value);
}
</script>

<template>
  <div
    class="nt-textarea-wrapper"
    :class="{ 'nt-textarea-wrapper--disabled': disabled }"
  >
    <label v-if="label" class="nt-textarea-label" :for="textareaId">
      {{ label }}
      <span v-if="required" class="required-indicator" aria-hidden="true">*</span>
    </label>
    <textarea
      :id="textareaId"
      class="nt-textarea"
      :class="{ 'nt-textarea--error': hasError }"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :rows="rows"
      :required="required"
      :aria-required="required || undefined"
      :aria-invalid="hasError || undefined"
      :aria-describedby="error ? `${textareaId}-error` : undefined"
      @input="onInput"
    />
    <p
      v-if="error"
      :id="`${textareaId}-error`"
      class="nt-textarea-error"
      role="alert"
    >
      {{ error }}
    </p>
  </div>
</template>

<style scoped>
.nt-textarea-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.nt-textarea-wrapper--disabled {
  opacity: 0.5;
}

.nt-textarea-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.required-indicator {
  color: var(--error);
  margin-left: 2px;
}

.nt-textarea {
  padding: 8px 12px;
  background-color: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: var(--border-radius);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  resize: vertical;
  outline: none;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
  min-height: 60px;
}

.nt-textarea::placeholder {
  color: var(--text-secondary);
}

.nt-textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

.nt-textarea:disabled {
  cursor: not-allowed;
}

.nt-textarea--error {
  border-color: var(--error);
}

.nt-textarea--error:focus {
  box-shadow: 0 0 0 1px var(--error);
}

.nt-textarea-error {
  margin: 0;
  font-size: 12px;
  color: var(--error);
  line-height: 1.3;
}
</style>
