# Plan NovelTrad 2.0 — Reset complet + v1.0

> Repo cible : `C:/Users/Marc/Documents/1G1R/_Programmation/noveltrad`  
> Scope : fondation + UI + projets + multi-agent + lexique/TM + export + auto-update  
> Base : SDD NovelTrad 2.0 (`NovelTrad-Documentation`)  
> Principe : reutiliser au maximum, creer le minimum  
> Date : 2026-06-30

---

## 1. Reset

- [x] Supprimer tout l'ancien code v4 (seul `.git` est conserve).

## 2. Stack et librairies (reutilisation)

| Domaine | Choix | Justification |
|---|---|---|
| Shell desktop | Electron + electron-builder + electron-updater | SDD Volumes 1, 17, 20 |
| UI | Vue 3 + Composition API + Vue Router + Pinia | SDD Volumes 1, 4 |
| Bundler | Vite + electron-vite | Standard Electron/Vue |
| Langage | TypeScript partout | SDD |
| Validation | Zod | SDD Volume 16 |
| Base de donnees | better-sqlite3 (WAL) | SDD Volume 6 |
| Client Ollama | package npm `ollama` | API officielle |
| Parsing DOCX | mammoth.js | REUSE_MAP |
| Parsing EPUB | adm-zip + jsdom | Alternative stable a valider |
| Detection langue | franc | REUSE_MAP |
| Detection encodage | chardet + iconv-lite | REUSE_MAP |
| Export DOCX | docx (dolanmiu) | REUSE_MAP |
| Export EPUB | generation manuelle archiver + jsdom | Alternative stable |
| Tests | Vitest + Playwright | SDD Volume 19 |

## 3. Structure du monorepo

```text
noveltrad/
├── package.json                  # workspaces root
├── .gitignore
├── README.md
├── apps/desktop/
│   ├── package.json
│   ├── electron.vite.config.ts
│   ├── electron-builder.yml
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main/
│   │   │   ├── index.ts
│   │   │   ├── ipc/
│   │   │   │   ├── channels.ts
│   │   │   │   ├── router.ts
│   │   │   │   └── handlers/
│   │   │   │       ├── project.ts
│   │   │   │       ├── ollama.ts
│   │   │   │       ├── settings.ts
│   │   │   │       └── workflow.ts
│   │   │   ├── managers/
│   │   │   │   ├── ProjectManager.ts
│   │   │   │   ├── OllamaManager.ts
│   │   │   │   ├── SettingsManager.ts
│   │   │   │   └── WorkflowEngine.ts
│   │   │   ├── services/
│   │   │   │   ├── AiRouter.ts
│   │   │   │   ├── agents/
│   │   │   │   │   ├── AgentFactory.ts
│   │   │   │   │   ├── SplitAgent.ts
│   │   │   │   │   ├── PreTranslateAgent.ts
│   │   │   │   │   ├── TranslateAgent.ts
│   │   │   │   │   ├── ConsistencyAgent.ts
│   │   │   │   │   ├── LexiconAgent.ts
│   │   │   │   │   ├── GrammarAgent.ts
│   │   │   │   │   ├── StyleAgent.ts
│   │   │   │   │   ├── PolishAgent.ts
│   │   │   │   │   ├── QaAgent.ts
│   │   │   │   │   └── ExportAgent.ts
│   │   │   │   ├── ConsistencyChecker.ts
│   │   │   │   ├── QualityChecker.ts
│   │   │   │   ├── LexiconEngine.ts
│   │   │   │   ├── TranslationMemoryEngine.ts
│   │   │   │   └── ExportEngine.ts
│   │   │   ├── db/
│   │   │   │   ├── connection.ts
│   │   │   │   ├── migrations/
│   │   │   │   │   └── 001_initial.sql
│   │   │   │   └── repositories/
│   │   │   ├── workers/
│   │   │   │   └── AgentWorker.ts
│   │   │   ├── preload/
│   │   │   │   └── index.ts
│   │   │   └── utils/
│   │   │       ├── logger.ts
│   │   │       └── paths.ts
│   │   └── renderer/
│   │       ├── index.html
│   │       ├── src/
│   │       │   ├── main.ts
│   │       │   ├── App.vue
│   │       │   ├── router/
│   │       │   ├── stores/
│   │       │   ├── views/
│   │       │   ├── components/
│   │       │   ├── services/
│   │       │   ├── styles/
│   │       │   └── types/
│   │       └── package.json
│   └── tests/
└── packages/shared/
    └── src/
        ├── types/
        └── schemas/
```

## 4. Phases d'implementation

### Phase A — Fondation
- Root + monorepo
- Electron main + preload + renderer Vue
- Wizard premier lancement + detection Ollama
- Settings globaux

### Phase B — UI
- Design system (tokens CSS)
- Sidebar + routes
- Accueil / Projet / Chapitres / Parametres

### Phase C — Projets + SQLite
- Creation/ouverture/suppression projet
- Arborescence chapitres/source/traductions
- Schema SQLite + repositories
- Import TXT/Markdown/DOCX/EPUB basique

### Phase D — Ollama + providers
- Configuration providers
- Liste modeles
- Test connexion
- Pull modele

### Phase E — Multi-agent
- WorkflowEngine
- AgentFactory
- 10 agents (split, pre_translate, translate, consistency, lexicon, grammar, style, polish, qa, export)
- Prompts versionnes
- Retry / fallback / pause

### Phase F — Lexique + TM + Quality
- LexiconEngine
- TranslationMemoryEngine
- ConsistencyChecker
- QualityChecker
- UI lexique

### Phase G — Export
- MD, TXT, HTML, DOCX, EPUB
- Mode bilingue
- Validation EPUB

### Phase H — Historique + Auto-update
- Versions de chapitres
- Diff / rollback
- electron-updater + latest.json

### Phase I — Tests + CI/CD
- Vitest + Playwright
- GitHub Actions ci.yml / release.yml
- Build Windows

## 5. Prochaines etapes

1. Creer le root package.json + .gitignore
2. Creer packages/shared
3. Creer apps/desktop
4. Installer deps
5. Lancer `npm run dev`
6. Iterer
