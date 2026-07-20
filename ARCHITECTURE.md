# Noveltrad — Architecture Guide

> Companion to `AGENTS.md` (team workflow) and `WORKFLOW_STATE.md` (session log).
> This document describes the **layered architecture**, the **conventions** to
> respect when adding code, and the **"where does new code go?"** cheat-sheet.

---

## Layer model

```
┌─────────────────────────────────────────────────────────────────┐
│  RENDERER  (Vue 3 + Pinia + Vue Router)                         │
│  apps/desktop/src/renderer/src/                                 │
│                                                                 │
│    views/         → pages (routes)                              │
│    components/    → reusable + feature components               │
│    composables/   → useXxx() reusable logic (Vue composition)   │
│    stores/        → Pinia stores (one per domain)               │
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
│  │ ipc/handlers/  → THIN: safeHandle + Zod + delegate      │   │
│  │                 No business logic. Owns no state.       │   │
│  │                 Channel list: ipc/channels.ts            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ managers/      → ORCHESTRATION                          │   │
│  │   WorkflowEngine → WorkflowRunner → PauseController     │   │
│  │   ProjectManager → ProjectPathResolver                  │   │
│  │   SettingsManager (singleton), OllamaManager, etc.      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ services/      → DOMAIN LOGIC (pure-ish)                │   │
│  │   ai/    AiRouter (facade) → TokenUsageAccumulator,     │   │
│  │          CostEstimator, TextChunker, PromptResolver,    │   │
│  │          jsonRepair, refusalDetector                     │   │
│  │   agents/    (all extend Agent base; created by factory)│   │
│  │   providers/ (OllamaProvider, OpenAiCompatibleProvider) │   │
│  │   prompts/   (PromptLoader + per-stage system prompts)  │   │
│  │   ExportEngine, LexiconEngine, TranslationMemoryEngine,  │   │
│  │   RagEngine, ConsistencyChecker, QualityChecker,         │   │
│  │   HallucinationDetector, CalibrationService, AuditService│   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ db/            → PERSISTENCE                            │   │
│  │   base/BaseRepository<T>  (generic helpers + abstract   │   │
│  │                            map())                        │   │
│  │   repositories/  7 repos, all extend BaseRepository      │   │
│  │   utils.ts       withTransaction, jsonColumn, boolColumn│   │
│  │   connection.ts  createProjectDatabase, runMigrations    │   │
│  │   migrations/    001-018 .sql files                      │   │
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

## Conventions

### DB layer — repositories

All 7 repositories extend `BaseRepository<T>` (`db/base/BaseRepository.ts`), which provides opt-in `protected` helpers:

- `queryOne(sql, params)` / `queryMany(sql, params)` — read + map rows
- `execute(sql, params)` — INSERT/UPDATE/DELETE
- `findById(id)` / `deleteById(id)` — default PK operations
- abstract `map(row)` — each repo shapes its own entity

**When adding a repo:** extend `BaseRepository<YourEntity>`, pass the table name to `super(db, "table_name")`, implement `map()`. Use `withTransaction` for multi-statement atomicity, `jsonColumn.read/write` for JSON columns. Do NOT inline `db.prepare(...)` outside of batch methods that need prepared-statement reuse (cf. `ParagraphRepository.createMany`).

### IPC layer — handlers

- **Channel list:** `ipc/channels.ts` is the single source of truth (81 channels). The preload (`preload/index.ts`) maintains a parallel copy that **MUST stay in sync** (preload runs in an isolated context and can't import from main). When you add a channel, update BOTH.
- **Schemas:** payload Zod schemas live in `packages/shared/src/schemas/ipc.ts`. Handlers import from `@shared/schemas/ipc.js`. Do NOT re-declare schemas locally in handlers or tests.
- **`safeHandle`** (`ipc/safeHandle.ts`): opt-in helper for uniform Zod parse + try/catch + error logging. The handler's natural return value passes through (NO `{ok,data}` envelope — that would break the renderer stores which consume the value directly). Errors throw → preload re-throws → store's `.catch(err => err.message)`.
- **Error shapes are intentionally heterogeneous** on the success path: some handlers return discriminated unions (`source:import-files` → per-file `{success}[]`, `dialog:open-file` → `{success, paths}`). This is correct — these represent legitimate non-error outcomes, not errors to standardize.

### Services layer

- **`AiRouter`** is a facade. Its 6 collaborators live in `services/ai/`:
  - `TokenUsageAccumulator`, `CostEstimator`, `TextChunker`, `PromptResolver` (stateful)
  - `jsonRepair.ts`, `refusalDetector.ts` (pure functions)
  - Do not add new concerns to `AiRouter` itself — add a collaborator.
- **Agents** all extend `services/agents/Agent.ts` (abstract `execute(input): Promise<AgentOutput>` + optional `outputSchema`). They're created exclusively by `AgentFactory.create(stage, config)`.
- **Providers** implement `AiProvider` (`chat`, `streamChat`, `embeddings`, optional `chatWithUsage`).

### Managers layer

- **`ProjectPathResolver.resolve(projectId)`** is the ONLY way to turn a projectId into a project path. Do NOT re-implement the `recentProjects` scan — it was duplicated 8× before WS-4 and the resolver fixed latent DB leaks as a side effect.
- **`WorkflowRunner`** delegates pause/resume/cancel to `PauseController`. The other planned collaborators (QaBranchPolicy, JobRecorder, AgentIoAssembler, RunnerServices) were descoped — see `WORKFLOW_STATE.md` WS-5 for the rationale.

### Renderer layer

- **`composables/`** (created in WS-6): `useAsyncAction` (loading/error wrapper), `useStatusLabels` (workflow status/stage maps). Adopt progressively; do not mass-migrate stores (no renderer unit tests).
- **`utils/format.ts`** (formatDate/formatDuration/formatTime/formatSize) and **`utils/download.ts`** (downloadBlob) are the shared helpers — do not re-inline these in views.
- **`toPlain()`** (`utils/toPlain.ts`) MUST be called before any IPC `invoke` that passes a Vue reactive object (Proxy), or Electron's structured clone will throw `DataCloneError`.

---

## "Where does new code go?" cheat-sheet

| You're adding... | Put it in... |
|---|---|
| A new DB table + entity | `db/repositories/` (new repo extending `BaseRepository<T>`) + migration in `db/migrations/NNN_name.sql` + type in `packages/shared/src/types/index.ts` |
| A new IPC channel | `ipc/channels.ts` AND `preload/index.ts` (keep in sync) + handler in `ipc/handlers/` + payload schema in `packages/shared/src/schemas/ipc.ts` |
| A new workflow stage | `STAGES` in `managers/WorkflowEngine.ts` + `WorkflowStage` type in shared + `workflowStageSchema` in `ipc.ts` + agent in `services/agents/` + `AgentFactory.create` switch |
| A new AI provider | `services/providers/` (implements `AiProvider`) + register in `WorkflowRunner` constructor |
| A new LLM concern on AiRouter | NEW collaborator in `services/ai/` (do NOT grow AiRouter) |
| A new renderer page | `views/` (lazy-loaded in `router/index.ts`) + store in `stores/` |
| Reusable renderer logic | `composables/` (if reactive) or `utils/` (if pure) |
| A new domain type/schema | `packages/shared/src/{types,schemas}/` (the contract layer) |

---

## Testing

- **Runner:** Vitest (`apps/desktop/vitest.config.ts`)
- **Scope:** `src/main/{services,managers,db/repositories,ipc/handlers}/**` — the **main process**. The renderer has **no unit tests** (verify by `npm run dev` smoke).
- **Baseline:** 1022 tests across 73 files. Every commit in this codebase MUST keep this green.
- **Verify command:** `npm run type-check && npm run test && npm run lint` (the holy trinity — 0 errors on all three).

---

## Architectural decisions log (refactor `refactor/clean-architecture`)

This section records the non-obvious decisions from the 2026-07 clean-architecture refactor (see `WORKFLOW_STATE.md` for per-commit detail).

1. **BaseRepository is opt-in, not opinionated.** HistoryRepository keeps its custom SQL (hybrid snapshots, zlib, JOINs) and only uses the base for the constructor + handle. Paragraph/Lexicon keep their `withTransaction` batch methods (intentional N-fsync → 1 optimization). The base provides helpers, not forced CRUD.

2. **IPC error envelope was NOT imposed.** Original plan: uniform `{ok,data,error}`. Audit proved this would break behavior (stores consume return values directly; errors flow via throw). `safeHandle` standardizes the error path only. Documented in the WS-2 commit.

3. **AiRouter became a facade, not a relocation.** It stays at `services/AiRouter.ts` (not moved to `services/ai/`) to avoid churning 16 import paths. The 6 collaborators are extracted; the facade forwards.

4. **ProjectPathResolver dropped the `fs.existsSync(project.db)` guard.** The guard existed in 3 of the 8 duplicated sites. Removing it fixed a test failure (tests mock `createProjectDatabase` without writing `project.db`). `createProjectDatabase` already handles missing DB files. Documented in the resolver.

5. **WorkflowRunner decomposition stopped at PauseController.** The other 4 planned collaborators would each need to share heavy mutable state back with the runner; extraction would move coupling rather than reduce it. Honest descoping documented in WS-5 commit.

6. **Renderer view decomposition is deferred.** No renderer unit tests → blind template-factoring of 1000-LOC views is high-risk. Pattern established (composables + utils exist); adopt case-by-case during feature work.
