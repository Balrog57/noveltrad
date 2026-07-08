# Volume 15 — Plugins

## 15.1 Objectif

Permettre d’étendre NovelTrad sans modifier son cœur : nouveaux agents, modèles, exporteurs, prompts, workflows ou thèmes visuels. Le système de plugins est conçu comme une API stable et documentée, pas comme un mécanisme ad-hoc.

---

## 15.2 Types de plugins

| Type | Extension possible | Exemple |
|------|--------------------|---------|
| `provider` | Nouveau provider IA | Provider local `llama.cpp` |
| `agent` | Nouvel agent de workflow | Agent spécifique au xianxia |
| `export` | Nouveau format d’export | PDF, MOBI |
| `prompt-pack` | Prompts optimisés | Pack “français littéraire” |
| `workflow` | Workflow alternatif | Résumé avant traduction |
| `ui-theme` | Thème visuel | Thème haute contrast |
| `parser` | Nouveau parser de source | PDF, HTML |
| `tool` | Outil utilitaire | Compteur de mots avancé |

---

## 15.3 Structure d’un plugin

```text
my-plugin/
├── package.json              # Dépendances npm
├── manifest.json             # Métadonnées NovelTrad
├── index.ts                  # Point d’entrée
├── prompts/                  # Prompts optionnels
├── schemas/                  # Schémas JSON optionnels
├── README.md                 # Documentation
└── tests/                    # Tests du plugin
```

### `manifest.json`

```json
{
  "id": "com.example.xianxia-agent",
  "name": "Xianxia Consistency Agent",
  "version": "1.0.0",
  "author": "Example",
  "type": "agent",
  "entry": "index.ts",
  "permissions": ["ai", "lexicon", "project-read"],
  "contributions": {
    "agents": [{
      "stage": "xianxia_check",
      "name": "Xianxia Check",
      "description": "Vérifie la cohérence des termes de cultivation."
    }]
  },
  "configSchema": {
    "strictness": { "type": "number", "default": 0.8 }
  }
}
```

### Permissions disponibles

| Permission | Description |
|------------|-------------|
| `ai` | Appeler les providers IA via `AiRouter`. |
| `lexicon` | Lire/écrire dans le lexique. |
| `project-read` | Lire les chapitres et paragraphes du projet courant. |
| `project-write` | Modifier les paragraphes traduits. |
| `fs-read` | Lire des fichiers dans le dossier projet. |
| `fs-write` | Écrire des fichiers dans le dossier projet. |
| `network` | Effectuer des requêtes HTTP. |
| `ui` | Enregistrer des composants UI (v2.0). |

---

## 15.4 API Plugin

### Interface principale

```typescript
export interface NovelTradPlugin {
  readonly manifest: PluginManifest
  readonly apiVersion: string // ex. "1.0"

  activate(context: PluginContext): void | Promise<void>
  deactivate(): void | Promise<void>
}

export interface PluginContext {
  readonly pluginId: string
  readonly projectId: string | null
  readonly aiRouter: AiRouter
  readonly lexiconEngine: LexiconEngine
  readonly logger: Logger

  registerAgent(stage: string, factory: AgentFactory): void
  registerExport(format: string, exporter: ExportPlugin): void
  registerProvider(id: string, provider: ProviderConstructor): void
  registerPrompt(id: string, prompt: PromptTemplate): void
  registerParser(extension: string, parser: SourceParser): void
  registerCommand(id: string, handler: CommandHandler): void
  registerConfigChangeListener(listener: ConfigChangeListener): void

  getConfig<T>(): T
  setConfig<T>(config: T): void
}
```

### Exemple de plugin agent

```typescript
// index.ts
import type { NovelTradPlugin, PluginContext, Agent, AgentInput, AgentOutput } from '@noveltrad/plugin-api'

export default class XianxiaPlugin implements NovelTradPlugin {
  readonly apiVersion = '1.0'
  readonly manifest = {
    id: 'com.example.xianxia-agent',
    name: 'Xianxia Consistency Agent',
    version: '1.0.0',
    type: 'agent'
  }

  activate(context: PluginContext): void {
    context.registerAgent('xianxia_check', (config) => new XianxiaAgent(config, context))
  }

  deactivate(): void {
    // nettoyage
  }
}

class XianxiaAgent implements Agent {
  readonly id = 'xianxia_check'
  readonly name = 'Xianxia Check'
  readonly stage = 'xianxia_check'

  async execute(input: AgentInput): Promise<AgentOutput> {
    // ...
    return { report: { score: 95, warnings: [] } }
  }
}
```

---

## 15.5 PluginHost

```typescript
class PluginHost {
  constructor(
    private pluginDir: string,
    private services: PluginServices
  ) {}

  async load(pluginPath: string): Promise<LoadedPlugin> {
    // 1. Lire manifest.json
    // 2. Valider schéma
    // 3. Vérifier permissions demandées
    // 4. Charger le module
    // 5. Appeler activate()
    // 6. Enregistrer les contributions
  }

  async unload(pluginId: string): Promise<void> {
    // 1. Appeler deactivate()
    // 2. Désenregistrer contributions
    // 3. Vider le require cache
  }

  list(): LoadedPlugin[]
  getAgent(stage: string): AgentConstructor | undefined
  getExport(format: string): ExportPlugin | undefined
  getProvider(id: string): ProviderConstructor | undefined
  getParser(extension: string): SourceParser | undefined
}
```

---

## 15.6 Cycle de vie

```text
Dossier plugins/ découvert au démarrage
    ↓
Pour chaque plugin :
    ↓
Lecture manifest.json
    ↓
Validation
    ↓
Confirmation utilisateur (si permissions dangereuses)
    ↓
Chargement du module
    ↓
activate()
    ↓
Contributions enregistrées
    ↓
Utilisation dans l’application
    ↓
Désactivation manuelle ou à la fermeture
    ↓
deactivate()
    ↓
Déchargement
```

### Hot-reload (mode dev)

- Surveillance du dossier `plugins/`.
- Si un fichier change, unload + reload automatique.
- À désactiver en production.

---

## 15.7 Sandbox et sécurité

### Modèle de confiance

- Les plugins tournent dans le **main process** avec les mêmes privilèges que l’application.
- Il n’y a pas de sandbox V8 isolé en v1.0 (complexité élevée).
- Le modèle de confiance repose sur :
  - Permissions explicites dans le manifest.
  - Confirmation utilisateur pour les permissions sensibles (`project-write`, `fs-write`, `network`).
  - Signature optionnelle des plugins (v2.0).

### Restrictions

- Un plugin ne peut pas accéder aux canaux IPC non déclarés.
- Les écritures fichier sont limitées au dossier projet (sauf permission explicite).
- Les clés API ne sont pas transmises aux plugins sauf via `AiRouter`.

### Politique de compatibilité apiVersion

- L'hôte accepte les plugins déclarant `apiVersion` `"1.x"` (toute version mineure 1.0–1.9).
- Un plugin déclarant un `apiVersion` incompatible (ex. `"2.0"`) est rejeté au chargement avec une erreur explicite : *« Plugin {name} requires apiVersion 2.0, host supports 1.x »*.
- En cas de montée de version de l'API hôte (ex. 1.x → 2.0), une période de grâce d'une version mineure est accordée (les plugins 1.x continuent de fonctionner en mode déprécié avec un log `warn`).
- `apiVersion` est indépendant de `version` (version du plugin) et de `type` (type de contribution).

### Validation du manifest

```typescript
function validateManifest(manifest: unknown): PluginManifest {
  const schema = z.object({
    id: z.string().regex(/^[a-z0-9.-]+$/),
    name: z.string().min(1).max(100),
    version: z.string().regex(/^\d+\.\d+\.\d+$/),
    type: z.enum(['provider', 'agent', 'export', 'prompt-pack', 'workflow', 'ui-theme', 'parser', 'tool']),
    entry: z.string(),
    permissions: z.array(z.string()),
    contributions: z.record(z.unknown()).optional(),
    configSchema: z.record(z.unknown()).optional()
  })
  return schema.parse(manifest)
}
```

---

## 15.8 Installation d’un plugin

### Manuelle

- L’utilisateur copie un dossier dans `plugins/`.
- L’application le détecte au redémarrage.

### Par marketplace (v2.0)

- Catalogue en ligne.
- Téléchargement zip.
- Vérification de signature.
- Installation en un clic.

---

## 15.9 Gestion des dépendances

- Chaque plugin a son propre `package.json`.
- L’application exécute `npm install` dans le dossier plugin au chargement si `node_modules` est absent.
- Isolation via `require` du chemin plugin.

---

## 15.10 UI des plugins

### Écran Paramètres → Plugins

- Liste des plugins chargés.
- Nom, version, auteur, permissions.
- Boutons : Activer/Désactiver, Configurer, Supprimer.
- Avertissement si un plugin demande des permissions sensibles.

---

## 15.11 Exemples de plugins

### Plugin export PDF (v2.0)

```typescript
{
  "id": "com.example.pdf-export",
  "type": "export",
  "permissions": ["fs-write"],
  "contributions": {
    "exports": [{ "format": "pdf", "name": "PDF" }]
  }
}
```

### Provider LM Studio

```typescript
{
  "id": "com.example.lmstudio-provider",
  "type": "provider",
  "permissions": ["network"],
  "contributions": {
    "providers": [{ "id": "lmstudio", "name": "LM Studio" }]
  }
}
```

---

## ✅ Critères d’acceptation des plugins

- [ ] Un plugin peut ajouter un agent.
- [ ] Un plugin peut ajouter un format d’export.
- [ ] Un plugin peut ajouter un provider IA.
- [ ] Le manifeste est validé avant chargement.
- [ ] Les permissions sont affichées et confirmées par l’utilisateur.
- [ ] Les plugins sont listés et configurables dans Paramètres.
- [ ] Le cycle de vie activate/deactivate est respecté.
- [ ] Le hot-reload fonctionne en mode développement.

---

## 📚 Références Context7

- `/electron/electron` — Sécurité Electron, sandbox, contextBridge.
- `/vitejs/vite` — Bundling de plugins en mode ESM.
