# Changelog

## v2.1.1 — Security + Performance + Accessibility (2026-07-05)

### Security
- **IPC channel validation in preload**: Added `IPC_CHANNELS` allowlist with `validateChannel()` — blocks unauthorized channels from renderer process, hardening `contextIsolation`
- **Preload event cleanup**: Changed `removeAllListeners` → `removeListener` for targeted, safe event removal

### Performance
- **SQLite transactions**: Wrapped `ParagraphRepository.createMany/updateMany` and `LexiconRepository.syncAliases` in explicit `BEGIN/COMMIT` transactions — eliminates N+1 auto-commit bottleneck on bulk DB writes

### Accessibility
- **NtTable**: Added `tabindex`, `keydown.enter/space` on sortable headers and rows with `:focus-visible` outlines
- **HomeView**: Added `role="button"`, `tabindex`, `keydown.enter/space` on project list items
- **LexiconForm**: Added `aria-label` + `disabled` state on remove (✕) buttons with not-allowed cursor when minimum items reached

### Tooling
- **ESLint**: 0 errors, 0 warnings (config created with TypeScript parser + Vue 3 support)
- **14 duplicate auto-PRs closed**, stale branches deleted
- **HomeView version**: 2.0.4 → 2.1.1

## v2.1.0 — Stabilization Release (2026-07-05)

### Bug Fixes

- **Ollama connection fix**: Migrated all HTTP calls from `globalThis.fetch()` to Electron's `net.fetch()` — resolves silent connection failures on desktop builds
- **RagEngine**: Migrated 2 remaining bare `fetch()` calls to `net.fetch()` with `AbortSignal.timeout()`
- **Production chunk loading**: Added `node_modules/**/*` to `electron-builder.yml` files list — fixes all 12 dynamic chunks failing silently
- **Menu system**: Added `project:open-dialog` IPC handler, all menu clicks use `getMainWindow()` with `isDestroyed()` checks
- **Log forwarding**: Uses `getMainWindow()` instead of closure for surviving window recreation
- **Settings fallback**: Added `DEFAULT_SETTINGS` in stores/settings.ts
- **Wizard**: Suivant button `:disabled="!canProceed"`, `finish()` wrapped in try/catch
- **App.vue**: `project:open-dialog` navigates to opened project

### Security

- **Path traversal**: Added `assertWithinProject()` to `project:open` handler
- **Logging**: Replaced raw `console.warn` with structured `logger.warn` in ProjectManager (NDJSON, redaction, correlation IDs)
- **Debug log dedup**: Removed 3 duplicate `debugLog()` functions, replaced with `logger.debug()` — eliminates `fs.appendFileSync` race conditions

### Testing

- **782 tests, 0 failures** (up from 737 baseline in v2.0.7)
- **+45 new tests** across 6 new/modified test files:
  - `ollama-manager.spec.ts`: expanded to 20 tests (timeout, HTTP 500, invalid JSON)
  - `providers.spec.ts`: expanded to 24 OllamaProvider tests
  - `rag-engine.spec.ts`: rewritten with `vi.mock("electron")` pattern
  - `ollama-ipc.spec.ts`: new 20 IPC integration tests
  - `non-regression.spec.ts`: new 8 router smoke tests
  - `ollama.spec.ts`: new 5 E2E scenarios
- **Per-file coverage targets met**:
  - OllamaManager.ts: 100% (target ≥90%)
  - OllamaProvider.ts: 98.98% (target ≥90%)
  - handlers/ollama.ts: 100% (target ≥85%)

### Architecture

- **`net.fetch()`**: All main-process HTTP uses Electron's `net.fetch()` (Chrome network stack) — no `node:http` fallback
- **Zod validation**: All IPC handlers validated with Zod schemas
- **Plugin system**: Complete (Volume 15 SDD) — PluginHost, PluginContext, PluginsView, hot-reload, example plugin
- **Structured logging**: NDJSON format, sensitive data redaction, correlation IDs

### Documentation

- `docs/PHASE0_VALIDATION_REPORT.md`: Ollama fix validation results
- `docs/STABILIZATION_AUDIT.md`: Phase 1 code audit findings

---

## v2.0.7 (2026-07-05)

- Repair broken index.ts (regex mangled try/catch)
- Isolated IPC loader

## v2.0.6 (2026-07-05)

- Native menu Help + Ollama default host
- Try/catch IPC router
- HelpView

## v2.0.5 (2026-07-05)

- Update check 5s + banner MAJ visible on Accueil
- Lazy gpt-tokenizer + HelpView

## v2.0.4 (2026-07-05)

- gpt-tokenizer lazy import (fix crash prod)
- HelpView + sidebar Aide

## v2.0.3 (2026-07-05)

- gpt-tokenizer version fix + build fix
- Consistency: replace custom countSentences with sbd
- RAG: replace custom cosineSimilarity with compute-cosine-similarity
