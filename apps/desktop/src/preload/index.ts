import { contextBridge, ipcRenderer } from "electron";

export interface NovelTradAPI {
  invoke: <T = unknown>(channel: string, ...args: unknown[]) => Promise<T>;
  on: (channel: string, callback: (...args: unknown[]) => void) => () => void;
}

const api: NovelTradAPI = {
  invoke: (channel, ...args) => ipcRenderer.invoke(channel, ...args),
  on: (channel, callback) => {
    ipcRenderer.on(channel, (_event, ...args) => callback(...args));
    return () => {
      ipcRenderer.removeAllListeners(channel);
    };
  },
};

contextBridge.exposeInMainWorld("novelTradAPI", api);
