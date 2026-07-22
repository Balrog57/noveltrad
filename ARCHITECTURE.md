# Noveltrad — Architecture Guide (v3)

> Companion to `AGENTS.md` (team workflow) and `WORKFLOW_STATE.md` (session log).
> This document describes the **v3 layered architecture** (pipeline 4 agents),
> the **conventions** to respect when adding code, and the **"where does new
> code go?"** cheat-sheet.
>
> v3 (2026-07-22) est une simplification majeure : pipeline 12→4 stages,
> moteur in-thread (~370 LOC au lieu de 1370), schéma DB greenfield 5
> migrations. Voir `CHANGELOG.md` et `REFACTOR_PLAN_V3.md` pour le détail.

---

## Layer model

```
┌─────────────────────────────────────────────────────────────────┐
│  RENDERER  (Vue 3 + Pinia + Vue Router)                         │
│  apps/desktop/src/renderer/src/                                 │
│                                                                 │
│    views/         → 3 pages : HomeView (Dashboard), ProjectView │
│                     (all-in-one), SettingsView                  │
│    components/    → Sidebar + Nt* UI primitives + ExportDialog  │
│    composables/   → useAsyncAction, useStatusLabels             │
│    stores/        → Pinia stores (project, workflow, settings…) │
│    utils/         → pure helpers (format, download, toPlain)    │
│                                                                 │
│  Rule: NO direct SQL, NO Electron imports.                      │
│  IPC boundary crossed only via `window.novelTradAPI.invoke`.    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │  IPC (preload bridge)
                          │  Contract: packages/shared (types + schemas)
                          │  Error path: handler throws → preload re-throws
                          │               → store `.catch(err => err.message)`
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  MAIN PROCESS  (Electron)                                       │
│  apps/desktop/src/main/                                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ipc/handlers/  → THIN: Zod validation + delegate         │   │
│  │                 No business logic. Channel list:         │   │
│  │                 ipc/channels.ts (52 canaux v3)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ managers/      → ORCHESTRATION                          │   │
│  │   SimpleWorkflowRunner → pipeline 4 stages (in-thread)  │   │
│  │   ProjectManager → ProjectPathResolver                  │   │
│  │   SettingsManager (singleton), OllamaManager,           │   │
│  │   UpdateManager                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ services/      → DOMAIN LOGIC (pure-ish)                │   │
│  │   ai/    AiRouter (facade) → TokenUsageAccumulator,     │   │
│  │          CostEstimator, TextChunker, PromptResolver,    │   │
│  │          jsonRepair, refusalDetector                     │   │
│  │   agents/    Translate, Proofreader, Glossary(=Lexicon),│   │
│  │              Validator (+ Agent base, TextRefineAgent,  │   │
│  │              Summarizer) — created by AgentFactory      │   │
│  │   providers/ (OllamaProvider, OpenAiCompatibleProvider) │   │
│  │   prompts/   (PromptLoader + per-stage system prompts)  │   │
│  │   ExportEngine, LexiconEngine, TranslationMemoryEngine,  │   │
│  │   ConsistencyChecker, QualityChecker, HallucinationDetector│
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ db/            → PERSISTENCE                            │   │
│  │   base/BaseRepository<T>  (generic helpers + abstract   │   │
│  │                            map())                        │   │
│  │   repositories/  5 repos, all extend BaseRepository      │   │
│  │   utils.ts       withTransaction, jsonColumn, boolColumn│   │
│  │   connection.ts  createProjectDatabase, runMigrations    │   │
│  │   migrations/    001-005 .sql files (v3 greenfield)      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  packages/shared  (the contract — depends on nothing in apps/)  │
│    types/       TS interfaces (domain entities, AI providers)   │
│    schemas/     Zod schemas (input validation + agent I/O)      │
│      └─ ipc.ts  IPC payload schemas (single source for handlers)│
│    constants/   language lists                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Dependency rule:** each layer depends only on the layer directly below + `packages/shared`. Reverse dependencies are forbidden (db must not import from managers; renderer must not import from main).

---

## The v3 pipeline (4 stages)

```
SOURCE → [1. translate] → [2. proofread] → [3. glossary] → [4. validate] → FINAL
                                                                      │
                                                          (Summarizer transverse,
                                                           gated by summarizerEnabled)
```

| Stage | Agent | Role |
|---|---|---|
| `translate` | `TranslateAgent` | Traduction initiale per-paragraphe (TM exact-match short-circuit) |
| `proofread` | `ProofreaderAgent` | Fusion grammar+style+polish (TextRefineAgent + PROOFREAD_SPEC) |
| `glossary` | `LexiconAgent` | Application du lexique (locked/forbidden terms) |
| `validate` | `ValidatorAgent` | Fusion consistency+qa ; évaluation qualité 8-dims + ConsistencyReport |

`SimpleWorkflowRunner` (`managers/SimpleWorkflowRunner.ts`) itère les 4 stages
**séquentiellement, in-thread** (pas de worker_threads), émet `workflow:progress`
par stage, persiste les paragraphes via `ParagraphRepository.upsertMany`, et
déclenche le `SummarizerAgent` (cohérence cross-chapitre) après `validate`.

**Pas de jobs table** : la progression est en mémoire + events IPC. Cancel
only (pas de pause/resume persistant). Pas de QA auto-retry branching.

---

## Conventions

### DB layer — repositories

All 5 repositories extend `BaseRepository<T>` (`db/base/BaseRepository.ts`), which provides opt-in `protected` helpers:

- `queryOne(sql, params)` / `queryMany(sql, params)` — read + map rows
- `execute(sql, params)` — INSERT/UPDATE/DELETE
- `findById(id)` / `deleteById(id)` — default PK operations
- abstract `map(row)` — each repo shapes its own entity

**Repos v3 :** Project, Chapter, Paragraph, Lexicon, Summary.

**When adding a repo:** extend `BaseRepository<YourEntity>`, pass the table name to `super(db, "table_name")`, implement `map()`. Use `withTransaction` for multi-statement atomicity, `jsonColumn.read/write` for JSON columns.

### IPC layer — handlers

- **Channel list:** `ipc/channels.ts` is the single source of truth (52 channels v3). The preload (`preload/index.ts`) maintains a parallel copy that **MUST stay in sync** (preload runs in an isolated context and can't import from main). When you add a channel, update BOTH.
- **Schemas:** payload Zod schemas live in `packages/shared/src/schemas/ipc.ts`. Handlers import from `@shared/schemas/ipc.js`. Do NOT re-declare schemas locally in handlers or tests.

### Services layer

- **`AiRouter`** is a facade. Its collaborators live in `services/ai/`: `TokenUsageAccumulator`, `CostEstimator`, `TextChunker`, `PromptResolver` (stateful), `jsonRepair.ts`, `refusalDetector.ts` (pure). Do not add new concerns to `AiRouter` itself — add a collaborator.
- **Agents** all extend `services/agents/Agent.ts` (abstract `execute(input): Promise<AgentOutput>` + optional `outputSchema`). They're created exclusively by `AgentFactory.create(stage, config)` — the factory switch covers **only the 4 v3 stages**.
- **Providers** implement `AiProvider` (`chat`, `streamChat`, `embeddings`, optional `chatWithUsage`).

### Managers layer

- **`ProjectPathResolver.resolve(projectId)`** is the ONLY way to turn a projectId into a project path.
- **`SimpleWorkflowRunner`** is the sole workflow engine. It owns its DB connection (disposed on completion). Cancel via `runner.cancel()`.

### Renderer layer

- **3 views only:** HomeView (Dashboard), ProjectView (all-in-one), SettingsView.
- **`composables/`:** `useAsyncAction` (loading/error wrapper), `useStatusLabels` (workflow status/stage maps).
- **`utils/format.ts`** (formatDate/formatDuration/formatTime/formatSize) and **`utils/download.ts`** (downloadBlob) are the shared helpers.
- **`toPlain()`** (`utils/toPlain.ts`) MUST be called before any IPC `invoke` that passes a Vue reactive object (Proxy), or Electron's structured clone will throw `DataCloneError`.

---

## "Where does new code go?" cheat-sheet

| You're adding... | Put it in... |
|---|---|
| A new DB table + entity | `db/repositories/` (new repo extending `BaseRepository<T>`) + migration in `db/migrations/NNN_name.sql` + type in `packages/shared/src/types/index.ts` |
| A new IPC channel | `ipc/channels.ts` AND `preload/index.ts` (keep in sync) + handler in `ipc/handlers/` + payload schema in `packages/shared/src/schemas/ipc.ts` |
| A new pipeline stage | `SIMPLE_STAGES` in `managers/SimpleWorkflowRunner.ts` + `WorkflowStage` type in shared + `workflowStageSchema` in `ipc.ts` + agent in `services/agents/` + `AgentFactory.create` switch + `buildAgentInput`/`applyAgentOutput` cases |
| A new AI provider | `services/providers/` (implements `AiProvider`) + register in `SimpleWorkflowRunner` constructor |
| A new LLM concern on AiRouter | NEW collaborator in `services/ai/` (do NOT grow AiRouter) |
| A new renderer page | `views/` (lazy-loaded in `router/index.ts`) + store in `stores/` |
| Reusable renderer logic | `composables/` (if reactive) or `utils/` (if pure) |
| A new domain type/schema | `packages/shared/src/{types,schemas}/` (the contract layer) |

---

## Testing

- **Runner:** Vitest (`apps/desktop/vitest.config.ts`) for unit + Playwright (`playwright.config.ts`) for e2e.
- **Scope:** `src/main/{services,managers,db/repositories,ipc/handlers}/**` — the **main process**. The renderer has **no unit tests** (verify by `npm run dev` smoke).
- **Baseline:** 570 tests across 49 files. Every commit in this codebase MUST keep this green.
- **Verify command:** `npm run type-check --workspace=apps/desktop && npm test && npm run lint` (the holy trinity — 0 errors on all three).

---

## v3 architectural decisions

1. **SimpleWorkflowRunner is in-thread, no workers.** v2 ran agents in worker threads (`workers/agent-worker.ts`), which added complexity and freeze risk for async I/O. v3 runs sequentially in-thread — simpler, and the LLM calls are network-bound (await) so there's no CPU-spin benefit from workers.

2. **No jobs table.** v2 persisted jobs/job_steps for progress tracking and resume. v3 uses in-memory progress + `workflow:progress` events. Resume = re-run (skip already-translated paragraphs). Cancel only — no pause/resume.

3. **4 stages via factory switch.** `AgentFactory.create` covers only translate/proofread/glossary/validate. The old stages (split, pre_translate, consistency, grammar, style, polish, review, revise, qa, export) are deleted — their work is absorbed: Proofreader fuses grammar+style+polish, Validator fuses consistency+qa.

4. **QualityChecker + HallucinationDetector kept.** Despite being "v2 features," they're heuristic fallbacks the ValidatorAgent depends on (LLM eval → heuristic fallback on parse failure). Deleting them would have broken the Validator.

5. **Summarizer stays transverse.** Not a pipeline stage — invoked after `validate` (gated by `summarizerEnabled`), maintains a cross-chapter novel summary injected into translate/proofread/validate for naming/tone coherence.

6. **Greenfield migrations (18→5).** No users to migrate. Tables dropped: jobs, job_steps, agents, history_snapshots, audit_log, embeddings, exports, statistics, model_calibrations, review_reports, models.
