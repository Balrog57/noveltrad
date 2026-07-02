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
  configSchema?: Record<string, unknown>;
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
  const permissionNonce = ref("");

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

  async function getConfig(pluginId: string) {
    return window.novelTradAPI.invoke<{
      success: boolean;
      config: Record<string, unknown>;
      configSchema: Record<string, unknown>;
      error?: string;
    }>("plugin:get-config", pluginId);
  }

  async function setConfig(pluginId: string, config: Record<string, unknown>) {
    return window.novelTradAPI.invoke<{ success: boolean; error?: string }>("plugin:set-config", {
      pluginId,
      config,
    });
  }

  async function getInstallInfo() {
    return window.novelTradAPI.invoke("plugin:install");
  }

  async function requestPermissions() {
    const result = await window.novelTradAPI.invoke<{
      plugins: PendingPermission[];
      nonce: string;
    }>("plugin:request-permissions");
    pendingPermissions.value = result?.plugins || [];
    permissionNonce.value = result?.nonce || "";
    return pendingPermissions.value;
  }

  async function confirmPermissions(approvedIds: string[]) {
    return window.novelTradAPI.invoke<{ success: boolean }>(
      "plugin:confirm-permissions",
      { approvedIds, nonce: permissionNonce.value },
    );
  }

  return {
    plugins,
    loading,
    pendingPermissions,
    permissionNonce,
    hasSensitivePlugins,
    load,
    enable,
    disable,
    uninstall,
    getConfig,
    setConfig,
    getInstallInfo,
    requestPermissions,
    confirmPermissions,
  };
});
