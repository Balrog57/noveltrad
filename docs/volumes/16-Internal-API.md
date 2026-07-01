# Volume 16 — API interne

## 16.1 IPC

Les canaux IPC sont définis dans `src/main/ipc/channels.ts` et exposés via le preload script. Chaque canal a un schéma Zod pour valider le payload côté main.

---

## 16.2 Canaux principaux

| Channel | Direction | Usage |
|---------|-----------|-------|
| `project:create` | Renderer → Main | Créer un projet |
| `project:open` | Renderer → Main | Ouvrir un projet |
| `project:close` | Renderer → Main | Fermer le projet courant |
| `project:delete` | Renderer → Main | Supprimer un projet |
| `chapter:list` | Renderer → Main | Lister les chapitres |
| `chapter:import` | Renderer → Main | Importer un fichier source |
| `chapter:save` | Renderer → Main | Sauvegarder la traduction manuelle |
| `workflow:start` | Renderer → Main | Lancer un workflow |
| `workflow:pause` | Renderer → Main | Mettre en pause |
| `workflow:resume` | Renderer → Main | Reprendre |
| `workflow:retry-step` | Renderer → Main | Relancer une étape |
| `lexicon:list` | Renderer → Main | Lister le lexique |
| `lexicon:save` | Renderer → Main | Sauvegarder une entrée |
| `lexicon:delete` | Renderer → Main | Supprimer une entrée |
| `model:list` | Renderer → Main | Lister les modèles configurés |
| `model:test` | Renderer → Main | Tester un provider |
| `model:pull` | Renderer → Main | Télécharger un modèle Ollama |
| `export:run` | Renderer → Main | Exporter un chapitre |
| `settings:get` | Renderer → Main | Lire une préférence |
| `settings:set` | Renderer → Main | Écrire une préférence |
| `log` | Main → Renderer | Événement log |
| `workflow:*` | Main → Renderer | Événements workflow |

---

## 16.3 Validation des payloads avec Zod

### Exemple : `project:create`

```typescript
// src/main/ipc/schemas/project.ts
import { z } from 'zod'

export const createProjectSchema = z.object({
  name: z.string().min(1).max(100),
  author: z.string().max(100).optional(),
  sourceLanguage: z.string().length(2),
  targetLanguage: z.string().length(2),
  parentPath: z.string().min(1)
})

export type CreateProjectPayload = z.infer<typeof createProjectSchema>
```

```typescript
// src/main/ipc/handlers/project.ts
import { ipcMain } from 'electron'
import { createProjectSchema } from '../schemas/project'

export function registerProjectHandlers(projectManager: ProjectManager) {
  ipcMain.handle('project:create', async (_event, payload) => {
    const parsed = createProjectSchema.parse(payload)
    return projectManager.create(parsed)
  })
}
```

### Exemple : `workflow:start`

```typescript
export const startWorkflowSchema = z.object({
  projectId: z.string().uuid(),
  chapterId: z.string().uuid(),
  options: z.object({
    modelId: z.string().optional(),
    skipStages: z.array(z.string()).optional()
  }).optional()
})
```

---

## 16.4 Router IPC

```typescript
// src/main/ipc/router.ts
import { ipcMain } from 'electron'
import { registerProjectHandlers } from './handlers/project'
import { registerWorkflowHandlers } from './handlers/workflow'

export function registerIpcRouter(container: Container) {
  registerProjectHandlers(container.projectManager)
  registerWorkflowHandlers(container.workflowEngine)
  // ... autres handlers
}
```

### Rejection des canaux inconnus

```typescript
ipcMain.on('message', (event, channel) => {
  if (!knownChannels.includes(channel)) {
    event.preventDefault()
    logger.warn(`Unknown IPC channel: ${channel}`)
  }
})
```

---

## 16.5 Preload script

```typescript
// src/preload/index.ts
import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('novelTradAPI', {
  createProject: (payload) => ipcRenderer.invoke('project:create', payload),
  openProject: (path) => ipcRenderer.invoke('project:open', path),
  listChapters: (projectId) => ipcRenderer.invoke('chapter:list', projectId),
  startWorkflow: (payload) => ipcRenderer.invoke('workflow:start', payload),
  pauseWorkflow: (jobId) => ipcRenderer.invoke('workflow:pause', jobId),
  retryStep: (payload) => ipcRenderer.invoke('workflow:retry-step', payload),
  listLexicon: (projectId) => ipcRenderer.invoke('lexicon:list', projectId),
  saveLexiconEntry: (payload) => ipcRenderer.invoke('lexicon:save', payload),
  testModel: (payload) => ipcRenderer.invoke('model:test', payload),
  runExport: (payload) => ipcRenderer.invoke('export:run', payload),
  getSetting: (key) => ipcRenderer.invoke('settings:get', key),
  setSetting: (key, value) => ipcRenderer.invoke('settings:set', { key, value }),

  onLog: (callback) => ipcRenderer.on('log', (_event, value) => callback(value)),
  onWorkflowEvent: (callback) => ipcRenderer.on('workflow:event', (_event, value) => callback(value)),

  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel)
})
```

**Référence** (Context7: `/electron/electron`) : `contextBridge` expose des fonctions contrôlées au renderer sans exposer `ipcRenderer` directement.

---

## 16.6 Diagramme de séquence — Traduire un chapitre

```text
Renderer                        Main                           Workers
  |                               |                               |
  |-- workflow:start ------------->|                               |
  |                               |-- createJob()                 |
  |                               |-- save to SQLite              |
  |                               |                               |
  |                               |-- start job                   |
  |                               |-- spawn Worker              |
  |                               |                               |
  |                               |<-- step progress --------------|                               |
  |-- workflow:step-progress ---->| (forwarded)                  |
  |                               |                               |
  |                               |<-- step completed -------------|                               |
  |-- workflow:step-completed --->| (forwarded)                  |
  |                               |                               |
  |                               |-- export result               |
  |                               |-- save version                |
  |                               |<-- workflow:completed ----------|                               |
  |-- workflow:completed -------->| (forwarded)                  |
```

---

## 16.7 Gestion des erreurs IPC

### Format d’erreur standard

```typescript
interface IpcError {
  code: string
  message: string
  details?: unknown
}
```

### Comportement

- Si une validation Zod échoue : retourner `{ code: 'VALIDATION_ERROR', message: ... }`.
- Si une erreur métier survient : retourner `{ code: 'BUSINESS_ERROR', message: ... }`.
- Si une erreur inattendue survient : logger la stack trace côté main, retourner un message générique au renderer.

### Exemple

```typescript
ipcMain.handle('project:create', async (_event, payload) => {
  try {
    const parsed = createProjectSchema.parse(payload)
    return await projectManager.create(parsed)
  } catch (err) {
    if (err instanceof z.ZodError) {
      return { error: { code: 'VALIDATION_ERROR', message: err.message, details: err.errors } }
    }
    logger.error('project:create failed', err)
    return { error: { code: 'CREATE_FAILED', message: err instanceof Error ? err.message : 'Unknown error' } }
  }
})
```

---

## 16.8 Stores Pinia (renderer)

```typescript
// stores/project.ts
export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: null as Project | null,
    chapters: [] as Chapter[]
  }),
  actions: {
    async openProject(path: string) {
      this.currentProject = await window.novelTradAPI.openProject(path)
      this.chapters = await window.novelTradAPI.listChapters(this.currentProject.id)
    }
  }
})
```

---

## 16.9 Interfaces TypeScript partagées

Toutes les interfaces métier sont dans `packages/shared/src/types/`.

```typescript
// packages/shared/src/types/project.ts
export interface Project {
  id: string
  name: string
  author?: string
  sourceLanguage: string
  targetLanguage: string
  createdAt: string
  updatedAt: string
  path: string
}
```

---

## ✅ Critères d’acceptation de l’API interne

- [ ] Tous les canaux IPC sont listés et validés.
- [ ] Le preload script n’expose que les canaux déclarés.
- [ ] Chaque payload est validé avec Zod côté main.
- [ ] Les erreurs IPC suivent un format standard.
- [ ] Les stores Pinia sont typés.
- [ ] Les interfaces partagées sont utilisées par main et renderer.

---

## 📚 Références Context7

- `/electron/electron` — IPC sécurisé, `contextBridge`, `ipcRenderer`.
- `/colinhacks/zod` — Validation de schémas TypeScript.
