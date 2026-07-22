# NovelTrad v3 — Simplification Plan

> Approved 2026-07-22. A deliberate product simplification (ship less, keep it solid),
> NOT a dead-code cleanup — every service removed is live and tested.
>
> Built on **verified** codebase facts, not the original pasted plan (which had wrong counts).

## Baseline (captured 2026-07-22 on `main` @ `e835160`)
- `npm run type-check` → **0 errors**
- `npm run test` → **1054/1054 pass** (75 files)
- `npm run lint` → **0 errors**

## Decisions locked (from user clarification)
- **Genuine v3 rewrite** — deliberately ship less; what remains must be solid.
- **Keep chapters/paragraphs data model** (preserves the EPUB multi-file splitting shipped in v2.3.0).
- **Greenfield** — no users, no data-migration path. Migrations may be rewritten freely.
- Driven by **real crashes + UI too complex**.

## Corrected scope vs. the original pasted plan
| Pasted plan claim | Reality → v3 decision |
|---|---|
| "10 agents" | 14 concrete → collapse to **4** (translate, proofread, glossary, validate) |
| "81 channels" | 79 → trim to **~30-40** |
| "5+ views" | 12 → **3** (Dashboard, Project, Settings) |
| "145 tests" | ~1054/75 files → delete tests for removed features, keep/add tests for the 4-agent core |
| "delete dead code" | Nothing is dead → this is a **feature deletion**, not cleanup |
| "WorkflowEngine + WorkflowRunner = 2 files" | 1 file (`WorkflowEngine.ts`, 1370 lines, both classes) → replaced by `SimpleWorkflowRunner.ts` |
| (not mentioned) **SummarizerAgent** | **Keep** — transverse cross-chapter coherence feature, retarget its trigger to `validate` |

## Branch strategy
Long-lived **`v3`** integration branch from `main`. All phases land as commits into `v3`.
Intermediate states on `v3` need not be independently shippable. Final merge `v3 → main` ships 3.0.0.

---

## Phase 0 — Setup & baseline ✅
- [x] Branch `v3` from `main`.
- [x] Green baseline captured (type-check/test/lint all 0 errors, 1054 tests).
- [x] `REFACTOR_PLAN_V3.md` committed.
- [x] Migrations audited.

### Schema audit (for Phase 2)
**Keep tables:** `projects`, `chapters` (+metadata), `paragraphs`, `lexicon` (+aliases, metadata),
`translation_memory`, `chapter_summaries`, `novel_summaries`, `settings`.

**Drop tables:** `agents`, `jobs`, `job_steps`, `history_snapshots`, `audit_log`, `embeddings` (RAG),
`exports`, `prompts` (DB override), `statistics`, `model_calibrations`, `review_reports`, `models`.

## Phase 1 — New 4-stage pipeline (additive; old path untouched)
Goal: build the new runner **alongside** the old engine so the tree compiles and existing tests stay green.
- **New** `managers/SimpleWorkflowRunner.ts`: sequential, **in-thread (no worker_threads)**, iterates 4 stages,
  emits `workflow:progress` per stage, persists translated paragraphs via `ParagraphRepository.upsertMany`.
- **Agents:**
  - Keep `TranslateAgent`, `LexiconAgent` as-is.
  - **New `ProofreaderAgent`** = `TextRefineAgent` with merged `PROOFREAD_SPEC` (GRAMMAR+STYLE+POLISH → 1).
  - **New `ValidatorAgent`** = merge `QaAgent` + `ConsistencyAgent`; internalize the ConsistencyReport hand-off.
- **Prompts:** new `proofread.system.ts`, new `validate.system.ts`.
- **Types:** add 4 new stage ids to `WorkflowStage`; extend `AgentFactory.create`. Leave old stages in the union.
- **Summarizer:** keep; trigger after `validate` (gated by `summarizerEnabled`).
- New unit tests for `SimpleWorkflowRunner`, `ProofreaderAgent`, `ValidatorAgent`.

## Phase 2 — Simplify DB & repositories
- **New migrations `001-006`** (replace 001-018): projects, chapters, paragraphs, lexicon (+aliases), summaries, TM, settings.
- **Keep repos:** Project, Chapter, Paragraph, Lexicon, Summary.
- **Delete repos:** `JobRepository`, `HistoryRepository`.
- Update `ProjectManager.importSource` raw SQL to new schema.

## Phase 3 — Cut old code (big deletion phase)
- `ipc/handlers/workflow.ts` → forward to `SimpleWorkflowRunner`. Drop retry/quality-failed channels.
- **Delete managers/workers:** `WorkflowEngine.ts`, `QaBranchPolicy.ts`, `workers/agent-worker.ts`.
- **Delete services:** Calibration, RagEngine, QualityChecker, HallucinationDetector, AuditService,
  plugins/*, Review/Revise/Split/PreTranslate/Polish/Grammar/Style/Consistency agents + their prompts.
- **Delete handlers:** `history.ts`, `plugins.ts`.
- **Edit** `main/index.ts`, `AiRouter.ts`, `ExportEngine.ts`: remove PluginHost wiring/hooks.
- **Prune channels** `channels.ts` + `preload/index.ts` (keep in sync).

## Phase 4 — Renderer: 3 views
- **Rewrite `DashboardView.vue`:** project cards (create/open/delete + status).
- **Rewrite `ProjectView.vue` (all-in-one):** header, import/export, chapter selector, source/target panes,
  Translate button, 4-agent inspector (real-time via `workflow:progress` + `useStatusLabels`), lexicon tab.
- **Keep `SettingsView.vue`.**
- **Delete views:** Chapters, ChapterEditor, Workflow, History, Console, Plugins, Help (fold Lexicon into ProjectView).
- **Router** → 3 routes. **Stores:** delete plugins/history, merge/trim editor+workflow.
- Reuse `Nt*` components, composables, utils. Call `toPlain()` before IPC invokes.

## Phase 5 — Tests & release 3.0.0
- Trinity green at every phase boundary.
- Tests for SimpleWorkflowRunner, 4 agents, ProjectRepository, import (txt/docx/epub), export (epub).
- Playwright e2e: create → import epub → translate → export.
- Bump **3.0.0** (root + desktop package.json, CHANGELOG, README, verify electron-builder.yml).
- Merge `v3 → main`, tag `v3.0.0`.

## Risks & mitigations
- **EPUB export regression** → keep `ExportEngine` core untouched; only remove its PluginHost hook. Keep epub tests gating.
- **Renderer refactor is blind** (no renderer unit tests) → keep logic in composables; gate by Playwright e2e + smoke.
- **Freezes may NOT be fixed by dropping workers** (workers are async I/O). Recommend profiling the actual freeze separately.

## Open questions (defaults in parentheses)
1. **Translation Memory (TM)** — keep `TranslationMemoryEngine` + `tm:*` channels? **Default: keep.**
2. **Lexicon view** — fold into ProjectView as a tab. **Default: fold in.**
3. **`ai:stream-*` chat channels** — delete (only `lexicon:suggest` uses AiRouter, builds its own). **Default: delete.**
4. **QA auto-retry branching** — drop; report score only. **Default: drop.**

## Verify commands (every phase)
`npm run type-check && npm run test && npm run lint` — must be green at each boundary.
