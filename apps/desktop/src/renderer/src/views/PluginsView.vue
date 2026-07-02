<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { usePluginsStore, type PluginInfo } from "../stores/plugins";
import NtCard from "../components/ui/NtCard.vue";
import NtButton from "../components/ui/NtButton.vue";
import NtBadge from "../components/ui/NtBadge.vue";
import NtModal from "../components/ui/NtModal.vue";
import NtEmptyState from "../components/ui/NtEmptyState.vue";
import NtToast from "../components/ui/NtToast.vue";

const store = usePluginsStore();

const showPermissionModal = ref(false);
const toastMessage = ref("");
const toastVisible = ref(false);

const SENSITIVE_PERMISSIONS = ["project-write", "fs-write", "network"];

// ── État de la configuration du plugin ──

/** Plugin en cours de configuration (null = modal fermée) */
const configPluginId = ref<string | null>(null);
/** Schéma de configuration du plugin (depuis le manifest) */
const configSchema = ref<Record<string, unknown>>({});
/** Valeurs actuelles du formulaire */
const configValues = ref<Record<string, unknown>>({});
/** Erreur de sauvegarde */
const configError = ref("");

const configModalVisible = computed(() => configPluginId.value !== null);
const configPluginName = computed(() => {
  if (!configPluginId.value) return "";
  const plugin = store.plugins.find((p) => p.id === configPluginId.value);
  return plugin?.name || configPluginId.value;
});

/** Champs du formulaire générés depuis le configSchema */
const configFields = computed(() => {
  const fields: Array<{ key: string; type: string; label: string; description?: string }> = [];
  for (const [key, value] of Object.entries(configSchema.value)) {
    if (typeof value === "object" && value !== null) {
      const fieldDef = value as Record<string, unknown>;
      fields.push({
        key,
        type: (fieldDef.type as string) || "string",
        label: (fieldDef.label as string) || key,
        description: fieldDef.description as string | undefined,
      });
    }
  }
  return fields;
});

onMounted(async () => {
  await store.load();
  // Vérifier les permissions en attente au démarrage
  const pending = await store.requestPermissions();
  if (pending.length > 0) {
    showPermissionModal.value = true;
  }
});

function hasSensitivePermission(permissions: string[]): boolean {
  return permissions.some((p) => SENSITIVE_PERMISSIONS.includes(p));
}

function statusLabel(status: string): string {
  switch (status) {
    case "active":
      return "Actif";
    case "inactive":
      return "Inactif";
    case "error":
      return "Erreur";
    default:
      return status;
  }
}

function statusColor(status: string): "success" | "warning" | "error" | "info" {
  switch (status) {
    case "active":
      return "success";
    case "inactive":
      return "info";
    case "error":
      return "error";
    default:
      return "info";
  }
}

function permissionLabel(perm: string): string {
  const labels: Record<string, string> = {
    ai: "IA",
    lexicon: "Lexique",
    "project-read": "Lecture projet",
    "project-write": "Écriture projet",
    "fs-read": "Lecture fichiers",
    "fs-write": "Écriture fichiers",
    network: "Réseau",
    ui: "Interface",
  };
  return labels[perm] || perm;
}

async function togglePlugin(plugin: PluginInfo) {
  if (plugin.status === "active") {
    const result = await store.disable(plugin.id);
    if (result.success) {
      showToast(`Plugin "${plugin.name}" désactivé`);
    } else {
      showToast(`Erreur : ${result.error}`);
    }
  } else {
    const result = await store.enable(plugin.id);
    if (result.success) {
      showToast(`Plugin "${plugin.name}" activé`);
    } else {
      showToast(`Erreur : ${result.error}`);
    }
  }
}

async function removePlugin(plugin: PluginInfo) {
  const result = await store.uninstall(plugin.id);
  if (result.success) {
    showToast(`Plugin "${plugin.name}" supprimé`);
  } else {
    showToast(`Erreur : ${result.error}`);
  }
}

/** Ouvre la modale de configuration d'un plugin */
async function configurePlugin(plugin: PluginInfo) {
  configError.value = "";
  const result = await store.getConfig(plugin.id);

  if (!result.success) {
    showToast(`Erreur chargement configuration : ${result.error}`);
    return;
  }

  // Utiliser le configSchema du manifest + les valeurs runtime du PluginContext
  configSchema.value = result.configSchema || {};
  configValues.value = { ...(result.config || {}) };

  // Pour chaque champ du schéma, initialiser la valeur par défaut si absente
  for (const [key, value] of Object.entries(configSchema.value)) {
    if (typeof value === "object" && value !== null) {
      const fieldDef = value as Record<string, unknown>;
      if (configValues.value[key] === undefined && "default" in fieldDef) {
        configValues.value[key] = fieldDef.default;
      }
    }
  }

  configPluginId.value = plugin.id;
}

/** Ferme la modale sans sauvegarder */
function cancelConfig() {
  configPluginId.value = null;
  configSchema.value = {};
  configValues.value = {};
  configError.value = "";
}

/** Sauvegarde la configuration du plugin */
async function saveConfig() {
  if (!configPluginId.value) return;
  configError.value = "";
  const result = await store.setConfig(configPluginId.value, { ...configValues.value });
  if (result.success) {
    showToast(`Configuration de "${configPluginName.value}" enregistrée`);
    cancelConfig();
  } else {
    configError.value = result.error || "Erreur inconnue";
    showToast(`Erreur : ${configError.value}`);
  }
}

async function confirmPermissions() {
  const allIds = store.pendingPermissions.map((p) => p.id);
  await store.confirmPermissions(allIds);
  showPermissionModal.value = false;
  await store.load();
  showToast("Plugins activés");
}

function rejectPermissions() {
  showPermissionModal.value = false;
}

function showToast(message: string) {
  toastMessage.value = message;
  toastVisible.value = true;
  setTimeout(() => {
    toastVisible.value = false;
  }, 3000);
}
</script>

<template>
  <div class="plugins-view">
    <h1>Plugins</h1>

    <NtEmptyState
      v-if="store.plugins.length === 0 && !store.loading"
      icon="🔌"
      title="Aucun plugin installé"
      description="Copiez un dossier de plugin dans le dossier plugins/ de NovelTrad, puis redémarrez l'application."
    />

    <div v-else class="plugins-list">
      <NtCard v-for="plugin in store.plugins" :key="plugin.id" class="plugin-card">
        <div class="plugin-header">
          <div class="plugin-info">
            <h3 class="plugin-name">{{ plugin.name }}</h3>
            <span class="plugin-version">v{{ plugin.version }}</span>
            <span v-if="plugin.author" class="plugin-author">par {{ plugin.author }}</span>
          </div>
          <div class="plugin-status">
            <NtBadge :variant="statusColor(plugin.status)">
              {{ statusLabel(plugin.status) }}
            </NtBadge>
          </div>
        </div>

        <p v-if="plugin.description" class="plugin-description">
          {{ plugin.description }}
        </p>

        <div class="plugin-permissions">
          <span class="permissions-label">Permissions :</span>
          <NtBadge
            v-for="perm in plugin.permissions"
            :key="perm"
            :variant="hasSensitivePermission([perm]) ? 'warning' : 'info'"
          >
            {{ permissionLabel(perm) }}
          </NtBadge>
          <span v-if="plugin.permissions.length === 0" class="no-permissions">Aucune</span>
        </div>

        <div v-if="plugin.errorMessage" class="plugin-error">
          {{ plugin.errorMessage }}
        </div>

        <div class="plugin-actions">
          <NtButton
            :variant="plugin.status === 'active' ? 'secondary' : 'primary'"
            size="sm"
            @click="togglePlugin(plugin)"
          >
            {{ plugin.status === "active" ? "Désactiver" : "Activer" }}
          </NtButton>
          <NtButton
            v-if="plugin.configSchema && Object.keys(plugin.configSchema).length > 0"
            variant="secondary"
            size="sm"
            @click="configurePlugin(plugin)"
          >
            Configurer
          </NtButton>
          <NtButton variant="danger" size="sm" @click="removePlugin(plugin)"> Supprimer </NtButton>
        </div>
      </NtCard>
    </div>

    <!-- Modal de confirmation des permissions -->
    <NtModal :visible="showPermissionModal" title="Permissions requises" @close="rejectPermissions">
      <p>Les plugins suivants demandent des permissions sensibles :</p>
      <div v-for="p in store.pendingPermissions" :key="p.id" class="permission-item">
        <strong>{{ p.name }}</strong> (v{{ p.version }})
        <div class="perm-badges">
          <NtBadge v-for="perm in p.permissions" :key="perm" variant="warning">
            {{ permissionLabel(perm) }}
          </NtBadge>
        </div>
      </div>
      <template #footer>
        <NtButton variant="secondary" @click="rejectPermissions">Refuser</NtButton>
        <NtButton variant="primary" @click="confirmPermissions">Accepter</NtButton>
      </template>
    </NtModal>

    <!-- Modal de configuration du plugin -->
    <NtModal :visible="configModalVisible" title="Configuration" @close="cancelConfig">
      <p>
        Configuration du plugin <strong>{{ configPluginName }}</strong>
      </p>
      <div v-if="configFields.length === 0" class="config-empty">Aucun champ configurable.</div>
      <div v-else class="config-form">
        <div v-for="field in configFields" :key="field.key" class="config-field">
          <label class="config-label">{{ field.label }}</label>
          <span v-if="field.description" class="config-description">{{ field.description }}</span>
          <!-- Champ string / text -->
          <input
            v-if="field.type === 'string'"
            v-model="configValues[field.key]"
            class="config-input"
            type="text"
            :placeholder="field.label"
          />
          <!-- Champ number -->
          <input
            v-else-if="field.type === 'number'"
            v-model.number="configValues[field.key]"
            class="config-input"
            type="number"
            step="0.01"
          />
          <!-- Champ boolean -->
          <label v-else-if="field.type === 'boolean'" class="config-checkbox-label">
            <input v-model="configValues[field.key]" type="checkbox" class="config-checkbox" />
            Activer
          </label>
          <!-- Type inconnu : afficher en texte -->
          <input
            v-else
            v-model="configValues[field.key]"
            class="config-input"
            type="text"
            :placeholder="field.label"
          />
        </div>
      </div>
      <div v-if="configError" class="config-error-msg">{{ configError }}</div>
      <template #footer>
        <NtButton variant="secondary" @click="cancelConfig">Annuler</NtButton>
        <NtButton variant="primary" @click="saveConfig">Enregistrer</NtButton>
      </template>
    </NtModal>

    <!-- Toast notification -->
    <NtToast
      v-if="toastVisible"
      :message="toastMessage"
      type="info"
      @close="toastVisible = false"
    />
  </div>
</template>

<style scoped>
.plugins-view {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.plugins-view h1 {
  margin: 0 0 24px;
  font-size: 24px;
}

.plugins-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plugin-card {
  padding: 16px;
}

.plugin-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.plugin-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.plugin-name {
  margin: 0;
  font-size: 16px;
}

.plugin-version {
  color: var(--text-secondary);
  font-size: 13px;
}

.plugin-author {
  color: var(--text-secondary);
  font-size: 13px;
}

.plugin-description {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 8px 0;
  line-height: 1.4;
}

.plugin-permissions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin: 8px 0;
}

.permissions-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-right: 4px;
}

.no-permissions {
  font-size: 13px;
  color: var(--text-secondary);
  font-style: italic;
}

.plugin-error {
  background: var(--bg-tertiary);
  color: var(--danger);
  padding: 8px 12px;
  border-radius: var(--border-radius);
  font-size: 13px;
  margin: 8px 0;
}

.plugin-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.permission-item {
  margin: 12px 0;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: var(--border-radius);
}

.perm-badges {
  display: flex;
  gap: 4px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin: 12px 0;
}

.config-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-label {
  font-weight: 600;
  font-size: 14px;
}

.config-description {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.config-input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
}

.config-checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  cursor: pointer;
}

.config-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.config-error-msg {
  color: var(--danger);
  font-size: 13px;
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--border-radius);
  margin: 8px 0;
}

.config-empty {
  color: var(--text-secondary);
  font-style: italic;
  padding: 16px 0;
  text-align: center;
}
</style>
