import { contextBridge, ipcRenderer } from 'electron'
import { IPC_CHANNELS } from '../main/ipc/channels.js'

export interface NovelTradAPI {
  invoke: <T = unknown>(channel: string, ...args: unknown[]) => Promise<T>
  on: (channel: string, callback: (...args: unknown[]) => void) => () => void
}

const validChannels = new Set<string>(IPC_CHANNELS)

const api: NovelTradAPI = {
  invoke: (channel, ...args) => {
    if (!validChannels.has(channel)) {
      return Promise.reject(new Error(`Unauthorized IPC channel: ${channel}`))
    }
    return ipcRenderer.invoke(channel, ...args)
  },
  on: (channel, callback) => {
    if (!validChannels.has(channel)) {
      console.warn(`Unauthorized IPC channel: ${channel}`)
      return () => {}
    }
    const subscription = (_event: Electron.IpcRendererEvent, ...args: unknown[]) => callback(...args)
    ipcRenderer.on(channel, subscription)
    return () => {
      ipcRenderer.removeListener(channel, subscription)
    }
  }
}

contextBridge.exposeInMainWorld('novelTradAPI', api)
