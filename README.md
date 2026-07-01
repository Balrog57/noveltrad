# NovelTrad 2.0

Moteur de traduction littéraire multi-agent. Application desktop Electron + Vue 3 + TypeScript.

Traduit des romans du chinois/anglais/japonais/coréen vers le français via un pipeline de 10 agents IA spécialisés (découpage, pré-traduction, traduction, cohérence, lexique, grammaire, style, polish, QA, export), le tout orchestré localement avec Ollama.

---

## Prérequis

- **Node.js** ≥ 22 (LTS)
- **npm** ≥ 10
- **[Ollama](https://ollama.com)** installé et en cours d'exécution (`http://localhost:11434`)
- Modèle recommandé : `qwen3.5:9b` (pull via `ollama pull qwen3.5:9b`)

## Démarrage rapide

```bash
git clone https://github.com/Balrog57/noveltrad.git
cd noveltrad
npm install
npm run dev                    # Electron + Vite dev server
```

## Build

```bash
npm run build --workspace=apps/desktop
```

Le `.exe` est généré dans `apps/desktop/dist/NovelTrad-2.0.0-setup.exe`.

### Build sans publish

```bash
cd apps/desktop
npx electron-vite build
npx electron-builder             # sans --publish → pas de release GitHub
```

## Tests

```bash
npm test                         # 145 tests unitaires (Vitest)
npm run test:e2e --workspace=apps/desktop   # Playwright + Electron
npm run type-check --workspace=apps/desktop # vue-tsc --noEmit
```

## Release & Auto-update

### Publier une nouvelle version

```bash
cd apps/desktop
# Bump version dans package.json ("2.0.0" → "2.0.1")
git add -A && git commit -m "release v2.0.1"
git tag v2.0.1
git push --tags
```

Le workflow `.github/workflows/release.yml` build et publie automatiquement sur GitHub Releases.

### Canaux de mise à jour

| Tag | Canal | Usage |
|-----|-------|-------|
| `v2.0.0` | `latest` | Stable |
| `v2.1.0-beta` | `beta` | Pré-release |
| `v2.1.0-alpha` | `alpha` | Dev |

L'auto-update (`electron-updater`) vérifie les nouvelles versions 30 secondes après le lancement et propose le téléchargement.

### CI/CD

| Workflow | Trigger | Actions |
|----------|---------|---------|
| `ci.yml` | PR / push main | Type-check → lint → 145 tests unitaires |
| `release.yml` | Tag `v*` | Type-check → lint → tests → build → publish GitHub Release |

## Structure du projet

```
noveltrad/
├── .github/workflows/          # CI/CD
│   ├── ci.yml                  # PR checks
│   └── release.yml             # Build + publish on tag
├── apps/desktop/
│   ├── electron-builder.yml    # Packaging + auto-update config
│   ├── electron.vite.config.ts
│   ├── playwright.config.ts
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── main/               # Process principal Electron
│   │   │   ├── index.ts        # Entry point, window, CSP, shortcuts
│   │   │   ├── ipc/            # Handlers IPC (project, ollama, workflow, etc.)
│   │   │   ├── managers/       # ProjectManager, WorkflowEngine, UpdateManager
│   │   │   ├── services/       # AiRouter, ExportEngine, LexiconEngine, TM, RAG
│   │   │   ├── services/agents/# 10 agents IA (split → export)
│   │   │   └── db/             # SQLite (connection, migrations, repositories)
│   │   ├── preload/            # contextBridge (novelTradAPI)
│   │   └── renderer/           # Vue 3 + Pinia + Vue Router
│   │       └── src/
│   │           ├── views/      # Home, Project, Chapters, Editor, Lexicon, History, etc.
│   │           ├── stores/     # Pinia stores (project, editor, workflow, lexicon, etc.)
│   │           └── components/ # UI (NtBadge, NtTooltip, export, wizard, etc.)
│   └── tests/
│       ├── unit/               # Vitest (145 tests)
│       └── e2e/                # Playwright + Electron
└── packages/shared/            # Types + schémas Zod partagés
```

## Architecture du workflow de traduction

```
Chapitre source
    │
    ▼
┌──────────────┐   ┌────────────────┐   ┌────────────┐
│ 1. Split     │──▶│ 2. Pre-Trad    │──▶│ 3. Traduire │
│ (découpage)  │   │ (TM + lexique) │   │ (IA + RAG)  │
└──────────────┘   └────────────────┘   └────────────┘
                                                │
    ┌───────────────────────────────────────────┘
    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ 4. Cohérence │──▶│ 5. Lexique   │──▶│ 6. Grammaire │
└──────────────┘   └──────────────┘   └──────────────┘
                                                │
    ┌───────────────────────────────────────────┘
    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ 7. Style     │──▶│ 8. Polish    │──▶│ 9. QA        │──▶│ 10. Export   │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

### Traitement par lot (batch)

Tous les chapitres peuvent être traduits séquentiellement via le bouton **"Tout traduire"** dans la vue Chapitres, avec progression `[1/N]`.

## Formats supportés

| Import | Export |
|--------|--------|
| TXT, Markdown, DOCX, EPUB | Markdown, TXT, HTML, DOCX, EPUB |
| TMX (mémoire de traduction) | TMX (mémoire de traduction) |
| CSV, JSON, TSV (lexique) | CSV, JSON, TSV (lexique) |

## Stack technique

| Domaine | Choix |
|---------|-------|
| Desktop | Electron 31 + electron-builder + electron-updater |
| UI | Vue 3 (Composition API) + Vue Router + Pinia |
| Bundler | electron-vite (Vite 5) |
| Langage | TypeScript strict |
| Validation | Zod |
| Base de données | node-sqlite3-wasm (WAL mode) |
| IA | Ollama (local), multi-provider via AiRouter |
| Parsing | mammoth.js (DOCX), adm-zip (EPUB), franc (langue) |
| Export | docx (dolanmiu), archiver (EPUB) |
| Tests | Vitest + Playwright |
| CI/CD | GitHub Actions |

## Documentation

La documentation complète (SDD, guides, REUSE_MAP, inspirations) est disponible dans
[`docs/`](docs/) et publiée sur GitHub Pages :

➡️ **[https://balrog57.github.io/noveltrad/](https://balrog57.github.io/noveltrad/)**

```bash
npm run docs:dev     # Serveur local VitePress (port 5174)
npm run docs:build   # Build statique
```
