<script setup lang="ts">
import { onMounted, ref } from "vue";
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
          <NtButton variant="danger" size="sm" @click="removePlugin(plugin)">
            Supprimer
          </NtButton>
        </div>
      </NtCard>
    </div>

    <!-- Modal de confirmation des permissions -->
    <NtModal
      :visible="showPermissionModal"
      title="Permissions requises"
      @close="rejectPermissions"
    >
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

    <!-- Toast notification -->
    <NtToast v-if="toastVisible" :message="toastMessage" type="info" @close="toastVisible = false" />
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
</style>
