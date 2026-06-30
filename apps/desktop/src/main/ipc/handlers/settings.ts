import { ipcMain } from 'electron'
import { SettingsManager } from '../../managers/SettingsManager.js'

const settings = new SettingsManager()

export function registerSettingsHandlers(): void {
  ipcMain.handle('settings:get', async (_event, key?: string) => {
    if (key) return settings.get(key as keyof ReturnType<typeof settings.getAll>)
    return settings.getAll()
  })

  ipcMain.handle('settings:set', async (_event, key: string, value: unknown) => {
    settings.set(key as keyof ReturnType<typeof settings.getAll>, value as never)
    return settings.getAll()
  })
}
