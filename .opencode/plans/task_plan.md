# Task Plan — NovelTrad 2.0 SDD Compliance

## Goal
Complete all remaining SDD compliance gaps to bring the application to full SDD alignment. Focus on the most impactful missing features.

## Current State
- **12 commits on main** (Items 1-8 + SDD fixes A-E)
- **95/95 tests pass**
- **type-check passes**
- Editor, Lexicon, Export, History, RAG, Prompts, CI/CD all implemented

## Remaining SDD Gaps (Priority Order)

### Phase 1 — Workflow Visualization (SDD §4.9, §7.6)
**Priority: HIGH** — Core feature for monitoring translations

| Task | Files |
|------|-------|
| Create `WorkflowView.vue` | `views/WorkflowView.vue` |
| Add route `/project/:projectId/workflow` | `router/index.ts` |
| Add sidebar link "⚙ Workflow" | `components/Sidebar.vue` |
| Enhance workflow store | `stores/workflow.ts` |

**SDD Specs:**
- Pipeline graph with step status icons (⏳ 🔄 ✅ ⚠️ ❌ ⏭️)
- Step detail panel (name, model, tokens, duration, message)
- Real-time logs console
- Actions: pause, resume, cancel, retry step, retry from

### Phase 2 — Console/Log Viewer (SDD §4.12)
**Priority: MEDIUM** — Important for debugging

| Task | Files |
|------|-------|
| Create `ConsoleView.vue` | `views/ConsoleView.vue` |
| Create `NtLogViewer.vue` | `components/ui/NtLogViewer.vue` |
| Add route `/console` | `router/index.ts` |
| Add sidebar link "🖥 Console" | `components/Sidebar.vue` |
| Create log store | `stores/logs.ts` |
| Add IPC `log` listener | `main/index.ts` |

### Phase 3 — Import System (SDD §5.4, §5.9)
**Priority: HIGH** — Users need to import files

| Task | Files |
|------|-------|
| Add DOCX parsing (mammoth.js) | `managers/ProjectManager.ts` |
| Add EPUB parsing (adm-zip) | `managers/ProjectManager.ts` |
| Add drag-and-drop import UI | `views/ChaptersView.vue` |
| Add language detection (franc) | `managers/ProjectManager.ts` |
| Add `source:import-files` IPC handler | `handlers/project.ts` |
| Add chapter splitting by patterns | `managers/ProjectManager.ts` |

### Phase 4 — Project Dashboard Stats (SDD §4.6)
**Priority: MEDIUM** — Improves UX

| Task | Files |
|------|-------|
| Create `NtStatCard.vue` | `components/ui/NtStatCard.vue` |
| Enhance `ProjectView.vue` with stats | `views/ProjectView.vue` |
| Add stats IPC handlers | `handlers/project.ts` |

### Phase 5 — Batch Processing (SDD §7.9)
**Priority: LOW** — Nice to have for v1.0

### Phase 6 — Translation Memory (SDD §9)
**Priority: LOW** — Already partially exists via RAG

## Verification
- `npm run type-check` must pass
- `npm run test` must pass (95+ tests)
- Each phase produces at least one test
