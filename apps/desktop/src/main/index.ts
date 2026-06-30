import { app, BrowserWindow } from 'electron'
import path from 'node:path'
import { registerIpcRouter } from './ipc/router.js'
import { SettingsManager } from './managers/SettingsManager.js'
import { UpdateManager } from './managers/UpdateManager.js'
import { logger } from './utils/logger.js'

const settings = new SettingsManager()
let mainWindow: BrowserWindow | null = null
let updateManager: UpdateManager | null = null

async function createWindow(): Promise<BrowserWindow> {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    webPreferences: {
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      allowRunningInsecureContent: false,
      webSecurity: true,
      preload: path.join(__dirname, '../preload/index.mjs')
    }
  })

  const devServerUrl = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173/'
  if (devServerUrl) {
    await mainWindow.loadURL(devServerUrl)
    mainWindow.webContents.openDevTools()
  } else {
    await mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'))
  }

  return mainWindow
}

function getMainWindow(): BrowserWindow | null {
  return mainWindow
}

app.whenReady().then(async () => {
  logger.info('NovelTrad starting...')
  registerIpcRouter()
  await createWindow()

  updateManager = new UpdateManager(settings.get('updateChannel'), getMainWindow)
  setTimeout(() => {
    updateManager?.check().catch((err) => {
      logger.warn('Initial update check failed', err)
    })
  }, 30_000)

  app.on('activate', async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
