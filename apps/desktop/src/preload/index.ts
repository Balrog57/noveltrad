import { contextBridge, ipcRenderer } from "electron";
import { IPC_CHANNELS } from "../main/ipc/channels";

export interface NovelTradAPI {
  invoke: <T = unknown>(channel: string, ...args: unknown[]) => Promise<T>;
  on: (channel: string, callback: (...args: unknown[]) => void) => () => void;
}

const api: NovelTradAPI = {
  invoke: (channel, ...args) => {
    if (IPC_CHANNELS.includes(channel as any)) {
      return ipcRenderer.invoke(channel, ...args);
    }
    return Promise.reject(new Error(`Invalid IPC channel: ${channel}`));
  },
  on: (channel, callback) => {
    if (IPC_CHANNELS.includes(channel as any)) {
      ipcRenderer.on(channel, (_event, ...args) => callback(...args));
      return () => {
        ipcRenderer.removeAllListeners(channel);
      };
    }
    console.error(`Invalid IPC channel: ${channel}`);
    return () => {};
  },
};

contextBridge.exposeInMainWorld("novelTradAPI", api);
