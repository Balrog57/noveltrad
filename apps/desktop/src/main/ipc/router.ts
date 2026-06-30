import { ipcMain } from 'electron'
import { IPC_CHANNELS } from './channels.js'
import { registerProjectHandlers } from './handlers/project.js'
import { registerOllamaHandlers } from './handlers/ollama.js'
import { registerSettingsHandlers } from './handlers/settings.js'

export function registerIpcRouter(): void {
  registerProjectHandlers()
  registerOllamaHandlers()
  registerSettingsHandlers()

  ipcMain.on('message', (event, channel) => {
    if (!IPC_CHANNELS.includes(channel)) {
      event.preventDefault()
      console.warn(`Unknown IPC channel: ${channel}`)
    }
  })
}
