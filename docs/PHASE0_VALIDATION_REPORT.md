# Phase 0 Validation Report — Ollama net.fetch() Migration

**Date:** 2026-07-05
**Version:** v2.1.0 (apps/desktop)
**Status:** ✅ PASSED — All targets met

---

## 1. Summary

The Ollama HTTP layer was migrated from `globalThis.fetch()` to `net.fetch()` from the Electron `net` module across 3 files. This validation suite confirms the fix works correctly, covers all error paths, and doesn't regress existing functionality.

---

## 2. Migration Files

| File | Changes |
|---|---|
| `src/main/managers/OllamaManager.ts` | 4 methods migrated to `net.fetch()` with `AbortSignal.timeout()`, `response.body.getReader()` NDJSON streaming, `response.json()`. `node:http` fallback removed. |
| `src/main/services/providers/OllamaProvider.ts` | 5 methods migrated to `net.fetch()` with `AbortSignal.timeout()`, `response.body.getReader()` NDJSON streaming, `response.json()`. `node:http` fallback removed. |
| `src/main/services/RagEngine.ts` | 2 bare `fetch()` calls (L28 `computeEmbedding`, L142 `isAvailable`) migrated to `net.fetch()` with `AbortSignal.timeout()`. |

All 3 files import `{ net } from "electron"` — no `node:http` fallback remains. Zero bare `fetch()` calls remain in `src/main/`.

---

## 3. Test Results

### 3.1 Unit Tests

| Test File | Tests | Status |
|---|---|---|
| `tests/unit/ollama-manager.spec.ts` | 20 | ✅ All passed |
| `tests/unit/providers.spec.ts` (OllamaProvider) | 24 | ✅ All passed |
| `tests/unit/rag-engine.spec.ts` | 16 | ✅ All passed |

**OllamaManager coverage:**
- `isAvailable()` — 7 tests: true, false (connection refused, ECONNREFUSED, AbortError), HTTP 500, invalid JSON
- `listModels()` — 4 tests: success, HTTP 500, undefined models
- `pullModel()` — 3 tests: streaming NDJSON, HTTP 500, null body
- `testModel()` — 6 tests: success, HTTP 500, undefined content, null body, invalid JSON, network error

**OllamaProvider coverage:**
- `isAvailable()` — 3 tests: true, false, network error
- `chat()` — 3 tests: success, timeout, HTTP 500
- `streamChat()` — 5 tests: streaming, multi-chunk, timeout, HTTP 500, null body
- `embeddings()` — 3 tests: success, HTTP 500, empty embeddings
- `listModels()` — 4 tests: success, timeout, HTTP 500, undefined models

**RagEngine coverage:**
- `computeEmbedding()` — 3 tests: success, network error, timeout
- `isAvailable()` — 3 tests: true, false, network error
- Constructor — 2 tests: valid host, invalid host
- `chunkText()` — 3 tests: short text, long text, single paragraph
- `buildPrompt()` — 2 tests: with/without memory
- Fallback embedding — 3 tests

### 3.2 IPC Integration Tests

| Test File | Tests | Status |
|---|---|---|
| `tests/unit/ollama-ipc.spec.ts` | 20 | ✅ All passed |
| `tests/unit/non-regression.spec.ts` | 8 | ✅ All passed |

**IPC coverage:**
- `ollama:is-available` — 6 tests: registered, true, false, HTTP 500, no exception propagation, timing
- `ollama:list-models` — 4 tests: registered, list, error, timing
- `ollama:pull-model` — 5 tests: registered, download, progress events, error, Zod validation
- `ollama:test-model` — 5 tests: registered, success, failure, Zod, timing

**Router smoke test:** All 12 handler modules load, 0 failures. All expected IPC channels registered.

### 3.3 Full Regression Suite

| Metric | Value |
|---|---|
| Test files | 47 passed |
| Tests | 782 passed, 0 failed |
| Duration | ~3s |
| Baseline (pre-Phase 0) | 737 tests |
| New tests added | +45 |

---

## 4. Coverage Results

### 4.1 Per-File Targets (SDD §19.6)

| File | Statements | Branch | Functions | Lines | Target | Status |
|---|---|---|---|---|---|---|
| `OllamaManager.ts` | 100% | 84.44% | 100% | 100% | ≥90% stmts | ✅ |
| `OllamaProvider.ts` | 98.98% | 78.78% | 100% | 98.98% | ≥90% stmts | ✅ |
| `handlers/ollama.ts` | 100% | 100% | 100% | 100% | ≥85% stmts | ✅ |
| `RagEngine.ts` | 100% | 92.3% | 100% | 100% | — | ✅ |

### 4.2 Global Thresholds (vitest.config.ts)

| Metric | Result | Threshold | Status |
|---|---|---|---|
| Statements | 49.88% | 40% | ✅ |
| Branches | 78.64% | 50% | ✅ |
| Functions | 83.09% | 75% | ✅ |
| Lines | 49.88% | 40% | ✅ |

### 4.3 Uncovered Zones

| File | Uncovered Lines | Risk |
|---|---|---|
| `OllamaManager.ts` | 11-14, 21, 38, 84, 90 | Low — logging/metadata lines, no logic |
| `OllamaProvider.ts` | 82 | Low — empty models fallback (dead path in practice) |
| `handlers/ollama.ts` | None | — |

---

## 5. E2E Tests

`tests/e2e/ollama.spec.ts` — 5 scenarios:
1. Badge shows "Ollama disponible" when available
2. Badge shows "Ollama non disponible" when unavailable
3. Wizard detects Ollama and shows status
4. Pull model shows progress events
5. Test model shows success/failure status

**Note:** E2E tests require a running Ollama server and will be skipped in CI unless Ollama is available (auto-detected via `fetch("http://localhost:11434/api/tags")`).

---

## 6. Residual Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `net.fetch()` behaves differently from `globalThis.fetch()` on edge cases | Low | All tests pass; Electron docs confirm `net.fetch()` is Chrome's network stack |
| `response.body.getReader()` used instead of `response.text()` for NDJSON | Low | Already working in production; `response.body` is a `ReadableStream` in Electron 31 |
| E2E tests skipped in CI without Ollama | Low | Unit tests cover all HTTP paths; E2E is validation only |
| `AbortSignal.timeout()` not available in older Node.js | None | Electron 31 ships Node 20+ which supports `AbortSignal.timeout()` |

---

## 7. Recommendations

1. ✅ **Proceed to Phase 0.1** — Ollama fix validated with automated tests
2. Consider adding integration test with real Ollama in staging environment
3. Monitor `debug.log` in production for any new `[Ollama]` errors
4. Phase 0.1 should freeze features and begin stabilization audit

---

## 8. Commands

```bash
# Run unit tests
npx vitest run tests/unit/ollama-manager.spec.ts tests/unit/providers.spec.ts tests/unit/rag-engine.spec.ts

# Run IPC tests
npx vitest run tests/unit/ollama-ipc.spec.ts tests/unit/non-regression.spec.ts

# Run full suite
npx vitest run

# Run coverage
npx vitest run --coverage

# Full verification (lint → typecheck → test → build → e2e)
npm run verify
```
