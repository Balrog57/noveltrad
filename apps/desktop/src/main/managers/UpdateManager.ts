import { EventEmitter } from 'node:events'
import { autoUpdater } from 'electron-updater'
import { dialog, BrowserWindow } from 'electron'
import { logger } from '../utils/logger.js'

export interface UpdateInfo {
  version: string
  releaseDate?: string
  releaseNotes?: string
}

export class UpdateManager extends EventEmitter {
  private checking = false

  constructor(
    private channel: string = 'latest',
    private getMainWindow?: () => BrowserWindow | null
  ) {
    super()
    autoUpdater.channel = channel
    autoUpdater.allowDowngrade = false
    autoUpdater.autoDownload = false
    autoUpdater.autoInstallOnAppQuit = false

    autoUpdater.on('checking-for-update', () => {
      logger.info('Checking for updates...')
      this.emit('checking')
      this.notifyRenderer('update:checking')
    })

    autoUpdater.on('update-available', (info) => {
      logger.info('Update available', info)
      this.emit('available', info)
      this.notifyRenderer('update:available', info)
      this.promptAndDownload()
    })

    autoUpdater.on('update-not-available', () => {
      logger.info('No update available')
      this.emit('not-available')
      this.notifyRenderer('update:not-available')
    })

    autoUpdater.on('download-progress', (progress) => {
      this.emit('progress', progress)
      this.notifyRenderer('update:progress', progress)
    })

    autoUpdater.on('update-downloaded', (info) => {
      logger.info('Update downloaded', info)
      this.emit('downloaded', info)
      this.notifyRenderer('update:downloaded', info)
      this.promptInstall()
    })

    autoUpdater.on('error', (err) => {
      logger.error('Auto-update error', err)
      this.emit('error', err)
      this.notifyRenderer('update:error', { message: err.message })
    })
  }

  async check(): Promise<void> {
    if (this.checking) return
    this.checking = true
    try {
      await autoUpdater.checkForUpdates()
    } finally {
      this.checking = false
    }
  }

  async download(): Promise<void> {
    await autoUpdater.downloadUpdate()
  }

  install(): void {
    autoUpdater.quitAndInstall()
  }

  setChannel(channel: string): void {
    this.channel = channel
    autoUpdater.channel = channel
  }

  private async promptAndDownload(): Promise<void> {
    const { response } = await dialog.showMessageBox({
      type: 'info',
      title: 'Mise a jour disponible',
      message: 'Une nouvelle version de NovelTrad est disponible.',
      detail: 'Telecharger maintenant et installer au prochain redemarrage ?',
      buttons: ['Telecharger', 'Plus tard'],
      defaultId: 0
    })

    if (response === 0) {
      await autoUpdater.downloadUpdate()
    }
  }

  private async promptInstall(): Promise<void> {
    const { response } = await dialog.showMessageBox({
      type: 'info',
      title: 'Mise a jour prete',
      message: 'La mise a jour a ete telechargee.',
      buttons: ['Installer et redemarrer', 'Plus tard'],
      defaultId: 0
    })

    if (response === 0) {
      autoUpdater.quitAndInstall()
    }
  }

  private notifyRenderer(channel: string, payload?: unknown): void {
    const win = this.getMainWindow?.()
    if (win && !win.isDestroyed()) {
      win.webContents.send(channel, payload)
    }
  }
}
