import { ipcMain, dialog } from 'electron'
import { z } from 'zod'
import { ProjectManager } from '../../managers/ProjectManager.js'
import { SettingsManager } from '../../managers/SettingsManager.js'
import { createProjectDatabase } from '../../db/connection.js'
import { ProjectRepository } from '../../db/repositories/ProjectRepository.js'

const settings = new SettingsManager()
const projectManager = new ProjectManager(settings)

const createProjectSchema = z.object({
  name: z.string().min(1).max(100),
  author: z.string().max(100).optional(),
  sourceLanguage: z.string().length(2),
  targetLanguage: z.string().length(2),
  parentPath: z.string().min(1)
})

export function registerProjectHandlers(): void {
  ipcMain.handle('project:create', async (_event, payload) => {
    const parsed = createProjectSchema.parse(payload)
    return projectManager.create(parsed)
  })

  ipcMain.handle('project:open', async (_event, projectPath: string) => {
    return projectManager.open(projectPath)
  })

  ipcMain.handle('project:path', async (_event, projectId: string) => {
    const recent = settings.get('recentProjects') as string[] | undefined ?? []
    const projectPath = recent.find((p) => {
      const db = createProjectDatabase(p)
      const found = new ProjectRepository(db).getById(projectId)
      db.close()
      return found !== undefined
    })
    if (!projectPath) throw new Error(`Projet non trouve : ${projectId}`)
    return projectPath
  })

  ipcMain.handle('project:list-recent', async () => {
    return projectManager.listRecent()
  })

  ipcMain.handle('project:delete', async (_event, projectId: string, removeFiles: boolean) => {
    return projectManager.delete(projectId, removeFiles)
  })

  ipcMain.handle('chapter:list', async (_event, projectId: string) => {
    return projectManager.listChapters(projectId)
  })

  ipcMain.handle('chapter:import', async (_event, projectId: string, filePath: string) => {
    return projectManager.importSource(projectId, filePath)
  })

  ipcMain.handle('dialog:open-file', async (_event, options) => {
    const result = await dialog.showOpenDialog(options)
    return { canceled: result.canceled, filePaths: result.filePaths }
  })
}
