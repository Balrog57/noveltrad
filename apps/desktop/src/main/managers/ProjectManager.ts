import fs from 'node:fs'
import path from 'node:path'

import type { CreateProjectPayload, Project, Chapter } from '@shared/types/index.js'
import type { SettingsManager } from './SettingsManager.js'
import { createProjectDatabase, runMigrations } from '../db/connection.js'
import { ProjectRepository } from '../db/repositories/ProjectRepository.js'
import { expandHome } from '../utils/paths.js'
import chardet from 'chardet'
import iconv from 'iconv-lite'

const migrationsDir = path.join(__dirname, '../../db/migrations')

export class ProjectManager {
  constructor(private settings: SettingsManager) {}

  async create(payload: CreateProjectPayload): Promise<Project> {
    const parentPath = expandHome(payload.parentPath)
    const projectDir = path.join(parentPath, payload.name)

    if (fs.existsSync(projectDir)) {
      throw new Error(`Le projet existe deja : ${projectDir}`)
    }

    fs.mkdirSync(projectDir, { recursive: true })
    fs.mkdirSync(path.join(projectDir, 'chapitres'))
    fs.mkdirSync(path.join(projectDir, 'source'))
    fs.mkdirSync(path.join(projectDir, 'traductions'))
    fs.mkdirSync(path.join(projectDir, 'lexique'))
    fs.mkdirSync(path.join(projectDir, 'exports'))
    fs.mkdirSync(path.join(projectDir, 'cache'))
    fs.mkdirSync(path.join(projectDir, 'logs'))

    const db = createProjectDatabase(projectDir)
    runMigrations(db, migrationsDir)

    const project: Project = {
      id: crypto.randomUUID(),
      name: payload.name,
      author: payload.author,
      sourceLanguage: payload.sourceLanguage,
      targetLanguage: payload.targetLanguage,
      path: projectDir,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }

    new ProjectRepository(db).create(project)
    db.close()

    await this.addToRecent(project)
    return project
  }

  async open(projectPath: string): Promise<Project> {
    const db = createProjectDatabase(projectPath)
    runMigrations(db, migrationsDir)
    const repo = new ProjectRepository(db)
    let project = repo.getByPath(projectPath)

    if (!project) {
      const projectName = path.basename(projectPath)
      project = {
        id: crypto.randomUUID(),
        name: projectName,
        sourceLanguage: 'zh',
        targetLanguage: 'fr',
        path: projectPath,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
      repo.create(project)
    }

    db.close()
    await this.addToRecent(project)
    return project
  }

  async listRecent(): Promise<Project[]> {
    const recent = this.settings.get('recentProjects') as string[] | undefined ?? []
    const projects: Project[] = []
    for (const projectPath of recent) {
      try {
        const project = await this.open(projectPath)
        projects.push(project)
      } catch (err) {
        console.warn(`Impossible d'ouvrir le projet recent ${projectPath}:`, err)
      }
    }
    return projects
  }

  async delete(projectId: string, removeFiles: boolean): Promise<void> {
    const recent = this.settings.get('recentProjects') as string[] | undefined ?? []
    const projectPath = recent.find((p) => {
      const dbPath = path.join(p, 'project.db')
      if (!fs.existsSync(dbPath)) return false
      const db = createProjectDatabase(p)
      const project = new ProjectRepository(db).getById(projectId)
      db.close()
      return project !== undefined
    })

    if (!projectPath) {
      throw new Error(`Projet non trouve : ${projectId}`)
    }

    if (removeFiles && fs.existsSync(projectPath)) {
      fs.rmSync(projectPath, { recursive: true, force: true })
    }

    const nextRecent = recent.filter((p) => p !== projectPath)
    this.settings.set('recentProjects', nextRecent)
  }

  async importSource(projectId: string, filePath: string): Promise<Chapter[]> {
    const projectPath = (this.settings.get('recentProjects') as string[] ?? []).find((p) => {
      const db = createProjectDatabase(p)
      const found = new ProjectRepository(db).getById(projectId)
      db.close()
      return found !== undefined
    })

    if (!projectPath) {
      throw new Error(`Projet non trouve : ${projectId}`)
    }

    const ext = path.extname(filePath).toLowerCase()
    if (ext !== '.txt' && ext !== '.md') {
      throw new Error(`Format non supporte en MVP : ${ext}`)
    }

    const encoding = chardet.detectFileSync(filePath) ?? 'utf-8'
    const buffer = fs.readFileSync(filePath)
    const text = iconv.decode(buffer, encoding as string)

    const fileName = path.basename(filePath, ext)
    const chapterId = crypto.randomUUID()
    const orderIndex = 0

    fs.copyFileSync(filePath, path.join(projectPath, 'chapitres', `${fileName}${ext}`))
    fs.writeFileSync(path.join(projectPath, 'source', `${fileName}.md`), text, 'utf-8')

    const paragraphs = text
      .split(/\n\n+/)
      .map((t) => t.trim())
      .filter(Boolean)
      .map((sourceText, index) => ({
        id: crypto.randomUUID(),
        chapter_id: chapterId,
        index_in_chapter: index + 1,
        source_text: sourceText,
        translated_text: null,
        status: 'pending'
      }))

    const db = createProjectDatabase(projectPath)
    runMigrations(db, migrationsDir)
    db.prepare(`
      INSERT INTO chapters (id, project_id, title, source_path, order_index, status, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run([
      chapterId,
      projectId,
      fileName,
      filePath,
      orderIndex,
      'pending',
      new Date().toISOString(),
      new Date().toISOString()
    ])

    const insertParagraph = db.prepare(`
      INSERT INTO paragraphs (id, chapter_id, index_in_chapter, source_text, translated_text, status)
      VALUES (?, ?, ?, ?, ?, ?)
    `)
    for (const p of paragraphs) {
      insertParagraph.run([p.id, p.chapter_id, p.index_in_chapter, p.source_text, p.translated_text, p.status])
    }

    db.close()

    return [{
      id: chapterId,
      projectId,
      title: fileName,
      sourcePath: filePath,
      orderIndex,
      status: 'pending',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }]
  }


  async listChapters(projectId: string): Promise<Chapter[]> {
    const projectPath = (this.settings.get('recentProjects') as string[] ?? []).find((p) => {
      const db = createProjectDatabase(p)
      const found = new ProjectRepository(db).getById(projectId)
      db.close()
      return found !== undefined
    })

    if (!projectPath) {
      throw new Error(`Projet non trouve : ${projectId}`)
    }

    const db = createProjectDatabase(projectPath)
    const rows = db.prepare('SELECT * FROM chapters WHERE project_id = ? ORDER BY order_index').all([projectId]) as Record<string, unknown>[]
    db.close()

    return rows.map((row) => ({
      id: String(row.id),
      projectId: String(row.project_id),
      title: row.title ? String(row.title) : undefined,
      sourcePath: row.source_path ? String(row.source_path) : undefined,
      orderIndex: Number(row.order_index),
      status: String(row.status) as Chapter['status'],
      createdAt: String(row.created_at),
      updatedAt: String(row.updated_at)
    }))
  }  private async addToRecent(project: Project): Promise<void> {
    const recent = (this.settings.get('recentProjects') as string[] | undefined) ?? []
    const next = [project.path, ...recent.filter((p) => p !== project.path)].slice(0, 10)
    this.settings.set('recentProjects', next)
  }
}



