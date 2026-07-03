import { contextBridge, ipcRenderer } from "electron";
import { IPC_CHANNELS, IpcChannel } from "../main/ipc/channels";

export interface NovelTradAPI {
  invoke: <T = unknown>(channel: IpcChannel, ...args: unknown[]) => Promise<T>;
  on: (channel: IpcChannel, callback: (...args: unknown[]) => void) => () => void;
}

const api: NovelTradAPI = {
  invoke: (channel, ...args) => {
    if (IPC_CHANNELS.includes(channel as IpcChannel)) {
      return ipcRenderer.invoke(channel, ...args);
    }
    throw new Error(`IPC channel "${channel}" is not allowed.`);
  },
  on: (channel, callback) => {
    if (IPC_CHANNELS.includes(channel as IpcChannel)) {
      ipcRenderer.on(channel, (_event, ...args) => callback(...args));
      return () => {
        ipcRenderer.removeAllListeners(channel);
      };
    }
    throw new Error(`IPC channel "${channel}" is not allowed.`);
  },
};

contextBridge.exposeInMainWorld("novelTradAPI", api);
