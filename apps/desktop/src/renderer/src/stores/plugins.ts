import { defineStore } from "pinia";
import { ref, computed } from "vue";

export interface PluginInfo {
  id: string;
  name: string;
  version: string;
  author?: string;
  description?: string;
  type: string;
  permissions: string[];
  status: "inactive" | "active" | "error";
  errorMessage?: string;
}

export interface PendingPermission {
  id: string;
  name: string;
  permissions: string[];
  version: string;
}

export const usePluginsStore = defineStore("plugins", () => {
  const plugins = ref<PluginInfo[]>([]);
  const loading = ref(false);
  const pendingPermissions = ref<PendingPermission[]>([]);

  const hasSensitivePlugins = computed(() => pendingPermissions.value.length > 0);

  async function load() {
    loading.value = true;
    try {
      const result = await window.novelTradAPI.invoke<PluginInfo[]>("plugin:list");
      plugins.value = result || [];
    } finally {
      loading.value = false;
    }
  }

  async function enable(pluginId: string) {
    const result = await window.novelTradAPI.invoke<{ success: boolean; error?: string }>(
      "plugin:enable",
      pluginId,
    );
    if (result.success) {
      await load();
    }
    return result;
  }

  async function disable(pluginId: string) {
    const result = await window.novelTradAPI.invoke<{ success: boolean; error?: string }>(
      "plugin:disable",
      pluginId,
    );
    if (result.success) {
      await load();
    }
    return result;
  }

  async function uninstall(pluginId: string) {
    const result = await window.novelTradAPI.invoke<{ success: boolean; error?: string }>(
      "plugin:uninstall",
      pluginId,
    );
    if (result.success) {
      await load();
    }
    return result;
  }

  async function getInstallInfo() {
    return window.novelTradAPI.invoke("plugin:install");
  }

  async function requestPermissions() {
    const result = await window.novelTradAPI.invoke<PendingPermission[]>("plugin:request-permissions");
    pendingPermissions.value = result || [];
    return pendingPermissions.value;
  }

  async function confirmPermissions(approvedIds: string[]) {
    return window.novelTradAPI.invoke<{ success: boolean }>(
      "plugin:confirm-permissions",
      approvedIds,
    );
  }

  return {
    plugins,
    loading,
    pendingPermissions,
    hasSensitivePlugins,
    load,
    enable,
    disable,
    uninstall,
    getInstallInfo,
    requestPermissions,
    confirmPermissions,
  };
});
