<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useSettingsStore } from "../../stores/settings";
import { useOllamaStore } from "../../stores/ollama";

const emit = defineEmits<{
  close: [];
}>();

const settings = useSettingsStore();
const ollama = useOllamaStore();

// Étapes du wizard
const step = ref(1);
const totalSteps = 5;

// Étape 2 : détection Ollama
const ollamaStatus = ref<"checking" | "available" | "unavailable">("checking");
const ollamaError = ref("");

// Étape 3 : modèle IA
const modelsLoading = ref(false);
const suggestedModel = "qwen3.5:9b";
const modelPresent = ref(false);
const pullingModel = ref(false);
const pullProgress = ref("");

// Étape 4 : configuration rapide
const sourceLanguage = ref("zh");
const targetLanguage = ref("fr");
const projectsPath = ref("~/NovelTrad Projects");

// Validation des étapes
const canProceed = computed(() => {
  switch (step.value) {
    case 1:
      return true;
    case 2:
      return ollamaStatus.value === "available";
    case 3:
      return modelsLoading.value === false;
    case 4:
      return sourceLanguage.value && targetLanguage.value && projectsPath.value;
    case 5:
      return true;
    default:
      return false;
  }
});

const nextLabel = computed(() => {
  switch (step.value) {
    case 1:
      return "Démarrer";
    case 4:
      return "Suivant";
    case 5:
      return "Commencer";
    default:
      return "Suivant";
  }
});

function nextStep(): void {
  if (step.value === 3 && !modelPresent.value) {
    // Suggérer de télécharger le modèle avant de continuer
    // On peut continuer sans — l'utilisateur installera plus tard
  }
  if (step.value < totalSteps) {
    step.value++;
    if (step.value === 2) detectOllama();
    if (step.value === 3) detectModel();
    if (step.value === 5) void settings.set("firstRunCompleted", true);
  }
}

function prevStep(): void {
  if (step.value > 1) step.value--;
}

function skip(): void {
  // Passer directement à l'étape finale
  step.value = totalSteps;
  void settings.set("firstRunCompleted", true);
}

async function detectOllama(): Promise<void> {
  ollamaStatus.value = "checking";
  ollamaError.value = "";
  try {
    await ollama.check();
    if (ollama.available) {
      ollamaStatus.value = "available";
    } else {
      ollamaStatus.value = "unavailable";
    }
  } catch {
    ollamaStatus.value = "unavailable";
    ollamaError.value =
      "Impossible de contacter Ollama. Vérifiez qu'il est bien lancé.";
  }
}

function openOllamaSite(): void {
  const { shell } = window.require
    ? window.require("electron")
    : { shell: undefined };
  if (shell) {
    shell.openExternal("https://ollama.com/download/windows");
  }
}

async function detectModel(): Promise<void> {
  modelsLoading.value = true;
  try {
    await ollama.check();
    modelPresent.value = ollama.models.some(
      (m) => m.name === suggestedModel || m.name.startsWith(suggestedModel),
    );
  } catch {
    modelPresent.value = false;
  } finally {
    modelsLoading.value = false;
  }
}

async function pullModel(): Promise<void> {
  if (pullingModel.value) return;
  pullingModel.value = true;
  pullProgress.value = "Téléchargement en cours...";
  try {
    await window.novelTradAPI.invoke("ollama:pull-model", suggestedModel);
    modelPresent.value = true;
    pullProgress.value = "";
  } catch (e) {
    pullProgress.value =
      e instanceof Error ? e.message : "Échec du téléchargement.";
  } finally {
    pullingModel.value = false;
  }
}

async function saveConfig(): Promise<void> {
  await settings.set("sourceLanguage", sourceLanguage.value);
  await settings.set("targetLanguage", targetLanguage.value);
  await settings.set("defaultProjectsPath", projectsPath.value);
}

async function finish(): Promise<void> {
  await saveConfig();
  await settings.set("firstRunCompleted", true);
  emit("close");
}

onMounted(() => {
  if (ollama.available) {
    ollamaStatus.value = "available";
  }
});
</script>

<template>
  <Teleport to="body">
    <div class="wizard-overlay">
      <div
        class="wizard"
        role="dialog"
        aria-modal="true"
        aria-label="Assistant de premier lancement"
      >
        <!-- Barre de progression -->
        <div class="wizard-progress">
          <div
            class="wizard-progress-bar"
            :style="{ width: (step / totalSteps) * 100 + '%' }"
          />
        </div>

        <!-- Étape 1 : Bienvenue -->
        <div v-if="step === 1" class="wizard-step">
          <div class="wizard-logo">📖</div>
          <h2>Bienvenue dans NovelTrad 2.0</h2>
          <p class="wizard-subtitle">
            Votre moteur de traduction de romans assisté par IA multi-agent.
          </p>
          <p class="wizard-description">
            Cet assistant va vous guider pour configurer les éléments essentiels
            avant de commencer à traduire.
          </p>
        </div>

        <!-- Étape 2 : Détection Ollama -->
        <div v-else-if="step === 2" class="wizard-step">
          <h2>Détection d'Ollama</h2>
          <p class="wizard-description">
            NovelTrad utilise Ollama pour exécuter les modèles d'IA localement.
          </p>

          <div class="wizard-status" :class="ollamaStatus">
            <template v-if="ollamaStatus === 'checking'">
              <span class="spinner" />
              <span>Vérification de la connexion à Ollama...</span>
            </template>
            <template v-else-if="ollamaStatus === 'available'">
              <span class="status-dot ok" />
              <span
                >✅ Ollama détecté — {{ ollama.models.length }} modèle(s)
                trouvé(s)</span
              >
            </template>
            <template v-else>
              <span class="status-dot error" />
              <span>❌ Ollama non détecté</span>
            </template>
          </div>

          <p v-if="ollamaError" class="wizard-error">{{ ollamaError }}</p>

          <div v-if="ollamaStatus === 'unavailable'" class="wizard-actions-row">
            <button class="btn-secondary" @click="detectOllama">
              Réessayer
            </button>
            <button class="btn-primary" @click="openOllamaSite">
              Installer Ollama
            </button>
          </div>
        </div>

        <!-- Étape 3 : Modèle IA -->
        <div v-else-if="step === 3" class="wizard-step">
          <h2>Modèle IA</h2>
          <p class="wizard-description">
            Vérifions si le modèle recommandé est disponible.
          </p>

          <div class="wizard-model-check">
            <div v-if="modelsLoading" class="wizard-status checking">
              <span class="spinner" />
              <span>Recherche des modèles installés...</span>
            </div>
            <template v-else>
              <div class="wizard-model-info">
                <strong>{{ suggestedModel }}</strong>
                <span class="model-badge">Recommandé</span>
              </div>
              <p v-if="modelPresent" class="wizard-status available">
                ✅ Ce modèle est déjà installé.
              </p>
              <div v-else class="wizard-model-missing">
                <p>⚠️ Ce modèle n'est pas installé.</p>
                <p class="wizard-hint">
                  Sans ce modèle, la traduction ne pourra pas fonctionner. Vous
                  pouvez le télécharger maintenant (environ 5 Go).
                </p>
                <button
                  class="btn-primary"
                  :disabled="pullingModel"
                  @click="pullModel"
                >
                  {{
                    pullingModel
                      ? pullProgress || "Téléchargement..."
                      : `Télécharger ${suggestedModel}`
                  }}
                </button>
              </div>
            </template>
          </div>
        </div>

        <!-- Étape 4 : Configuration rapide -->
        <div v-else-if="step === 4" class="wizard-step">
          <h2>Configuration rapide</h2>
          <p class="wizard-description">
            Définissez vos préférences par défaut. Vous pourrez les modifier
            plus tard dans les paramètres.
          </p>

          <div class="wizard-config">
            <label>
              Langue source
              <select v-model="sourceLanguage">
                <option value="zh">Chinois (中文)</option>
                <option value="ja">Japonais (日本語)</option>
                <option value="ko">Coréen (한국어)</option>
                <option value="en">Anglais</option>
                <option value="fr">Français</option>
              </select>
            </label>

            <label>
              Langue cible
              <select v-model="targetLanguage">
                <option value="fr">Français</option>
                <option value="en">Anglais</option>
              </select>
            </label>

            <label>
              Dossier des projets
              <input
                v-model="projectsPath"
                type="text"
                placeholder="~/NovelTrad Projects"
              />
            </label>
          </div>
        </div>

        <!-- Étape 5 : Prêt -->
        <div v-else-if="step === 5" class="wizard-step">
          <div class="wizard-logo">🚀</div>
          <h2>Prêt !</h2>
          <p class="wizard-description">
            Tout est configuré. Voici un résumé de votre configuration :
          </p>

          <div class="wizard-summary">
            <div class="summary-item">
              <span class="summary-label">Ollama</span>
              <span class="summary-value">{{
                ollamaStatus === "available" ? "✅ Connecté" : "⚠️ À configurer"
              }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Modèle</span>
              <span class="summary-value">{{
                modelPresent ? suggestedModel : "⚠️ Non installé"
              }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Langue source</span>
              <span class="summary-value">{{ sourceLanguage }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Langue cible</span>
              <span class="summary-value">{{ targetLanguage }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Dossier projets</span>
              <span class="summary-value">{{ projectsPath }}</span>
            </div>
          </div>

          <p class="wizard-hint">
            Vous pouvez modifier ces paramètres à tout moment depuis ⚙️
            Paramètres.
          </p>
        </div>

        <!-- Barre d'actions -->
        <div class="wizard-footer">
          <button
            v-if="step > 1 && step < totalSteps"
            class="btn-secondary"
            @click="prevStep"
          >
            ← Retour
          </button>
          <div class="wizard-footer-right">
            <button v-if="step < totalSteps" class="btn-ghost" @click="skip">
              Passer
            </button>
            <button
              v-if="step < totalSteps"
              class="btn-primary"
              @click="step === 4 ? (nextStep(), saveConfig()) : nextStep()"
            >
              {{ nextLabel }}
            </button>
            <button
              v-if="step === totalSteps"
              class="btn-primary"
              @click="finish"
            >
              {{ nextLabel }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.wizard-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.wizard {
  background-color: var(--bg-primary);
  border: 1px solid var(--bg-tertiary);
  border-radius: var(--border-radius);
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
  width: 560px;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.wizard-progress {
  height: 4px;
  background-color: var(--bg-tertiary);
}

.wizard-progress-bar {
  height: 100%;
  background-color: var(--accent);
  transition: width 0.3s ease;
}

.wizard-step {
  padding: 32px 32px 16px;
  text-align: center;
  flex: 1;
  overflow-y: auto;
}

.wizard-logo {
  font-size: 48px;
  margin-bottom: 8px;
}

.wizard-step h2 {
  margin: 0 0 12px;
  font-size: 22px;
  color: var(--text-primary);
}

.wizard-subtitle {
  font-size: 15px;
  color: var(--accent);
  margin-bottom: 8px;
}

.wizard-description {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 20px;
}

.wizard-error {
  color: var(--error);
  font-size: 13px;
  margin-top: 8px;
}

.wizard-hint {
  color: var(--text-secondary);
  font-size: 12px;
  font-style: italic;
  margin-top: 12px;
}

/* Statut */
.wizard-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  margin-bottom: 16px;
  font-size: 14px;
  color: var(--text-primary);
}

.wizard-status.checking {
  color: var(--text-secondary);
}

.wizard-status.available {
  color: var(--success);
}

.wizard-status.unavailable {
  color: var(--error);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot.ok {
  background-color: var(--success);
}

.status-dot.error {
  background-color: var(--error);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--bg-tertiary);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.wizard-actions-row {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 16px;
}

/* Modèle IA */
.wizard-model-check {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 20px;
}

.wizard-model-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 16px;
  color: var(--text-primary);
}

.model-badge {
  background-color: var(--accent);
  color: var(--bg-primary);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.wizard-model-missing {
  color: var(--warning);
}

.wizard-model-missing p {
  margin-bottom: 12px;
}

/* Configuration */
.wizard-config {
  text-align: left;
}

.wizard-config label {
  display: block;
  margin-bottom: 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.wizard-config select,
.wizard-config input {
  display: block;
  width: 100%;
  margin-top: 4px;
  padding: 8px 12px;
  border-radius: var(--border-radius);
  border: 1px solid var(--bg-tertiary);
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 14px;
}

/* Résumé */
.wizard-summary {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 16px;
  text-align: left;
  margin-bottom: 16px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--bg-tertiary);
  font-size: 14px;
}

.summary-item:last-child {
  border-bottom: none;
}

.summary-label {
  color: var(--text-secondary);
}

.summary-value {
  color: var(--text-primary);
  font-weight: 500;
}

/* Pied */
.wizard-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  border-top: 1px solid var(--bg-tertiary);
  background-color: var(--bg-secondary);
}

.wizard-footer-right {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-left: auto;
}

/* Boutons */
.btn-primary {
  background-color: var(--accent);
  color: var(--bg-primary);
  border: none;
  padding: 8px 20px;
  border-radius: var(--border-radius);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s;
}

.btn-primary:hover {
  background-color: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border: none;
  padding: 8px 20px;
  border-radius: var(--border-radius);
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.btn-secondary:hover {
  background-color: var(--text-secondary);
  color: var(--bg-primary);
}

.btn-ghost {
  background: none;
  border: none;
  color: var(--text-secondary);
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
  border-radius: var(--border-radius);
}

.btn-ghost:hover {
  color: var(--text-primary);
  background-color: var(--bg-tertiary);
}
</style>
