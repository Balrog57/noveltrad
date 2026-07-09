import { defineStore } from "pinia";
import { ref } from "vue";

export interface UpdateProgress {
  percent: number;
  bytesPerSecond: number;
  total: number;
  transferred: number;
}

export interface UpdatePayload {
  version?: string;
  releaseDate?: string;
  releaseNotes?: string;
  message?: string;
  progress?: UpdateProgress;
}

export const useUpdateStore = defineStore("update", () => {
  const available = ref(false);
  const notAvailable = ref(false);
  const checking = ref(false);
  const downloaded = ref(false);
  const progress = ref<UpdateProgress | null>(null);
  const error = ref<string | null>(null);
  const info = ref<UpdatePayload | null>(null);

  window.novelTradAPI.on("update:checking", () => {
    checking.value = true;
    notAvailable.value = false;
    error.value = null;
  });

  window.novelTradAPI.on("update:available", (payload: unknown) => {
    checking.value = false;
    available.value = true;
    notAvailable.value = false;
    info.value = payload as UpdatePayload;
  });

  window.novelTradAPI.on("update:not-available", () => {
    checking.value = false;
    notAvailable.value = true;
    available.value = false;
  });

  window.novelTradAPI.on("update:downloaded", () => {
    downloaded.value = true;
  });

  window.novelTradAPI.on("update:progress", (payload: unknown) => {
    progress.value =
      (payload as {
        percent: number;
        bytesPerSecond: number;
        total: number;
        transferred: number;
      }) ?? null;
  });

  window.novelTradAPI.on("update:error", (payload: unknown) => {
    checking.value = false;
    error.value = (payload as { message: string }).message;
  });

  async function check(): Promise<void> {
    checking.value = true;
    notAvailable.value = false;
    error.value = null;
    try {
      await window.novelTradAPI.invoke("update:check");
    } catch (err) {
      checking.value = false;
      error.value = err instanceof Error ? err.message : String(err);
    }
  }

  async function download(): Promise<void> {
    await window.novelTradAPI.invoke("update:download");
  }

  async function install(): Promise<void> {
    await window.novelTradAPI.invoke("update:install");
  }

  async function setChannel(
    channel: "latest" | "beta" | "alpha",
  ): Promise<void> {
    await window.novelTradAPI.invoke("update:set-channel", channel);
  }

  return {
    available,
    notAvailable,
    checking,
    downloaded,
    progress,
    error,
    info,
    check,
    download,
    install,
    setChannel,
  };
});
