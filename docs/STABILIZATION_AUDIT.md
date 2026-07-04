# Stabilization Audit — Phase 1

**Date:** 2026-07-05
**Branch:** `stabilization-v2`
**Status:** Audit complete, issues listed below

---

## 1. Executive Summary

782 tests pass, type-check clean, 0 bare `fetch()` in main process. The codebase is solid for a v2.1 release. This audit found **3 important** and **5 minor** issues. No critical issues.

---

## 2. Issues Found

### IMPORTANT (3)

#### I1. `debugLog()` function duplicated 3 times
- **Files:** `OllamaManager.ts:7`, `router.ts:7`, `handlers/ollama.ts` (inline)
- **Problem:** Identical `debugLog()` function copy-pasted in 3 files. Each writes to `%APPDATA%/NovelTrad/debug.log` with `fs.appendFileSync`. If two fire simultaneously on the same file, writes may interleave.
- **Fix:** Extract to `src/main/utils/debug-log.ts` as a shared utility.
- **Risk:** Low (cosmetic/maintenance)

#### I2. `console.log/warn/error` used instead of `logger` in production code
- **Files:** `ProjectManager.ts` (4 occurrences), `OllamaManager.ts` (1), `handlers/ollama.ts` (2)
- **Problem:** SDD §18 mandates structured logging via `StructuredLogger`. Raw `console.log` bypasses redaction, correlation IDs, and NDJSON formatting.
- **Fix:** Replace `console.warn(...)` in ProjectManager with `logger.warn(...)`. Replace `debugLog()` in OllamaManager/handlers with `logger.debug(...)`.
- **Risk:** Medium (logging inconsistency, debug.log still works via interception)

#### I3. `project:open` handler lacks Zod validation and path traversal check
- **File:** `handlers/project.ts:40`
- **Problem:** `ipcMain.handle("project:open", async (_event, projectPath: string) => ...)` — raw string parameter, no Zod validation, no `assertWithinProject()`. Other handlers (lexicon, export, PluginHost) use `assertWithinProject()` consistently.
- **Fix:** Add `z.string().min(1).parse(projectPath)` and `assertWithinProject()` check.
- **Risk:** Medium (security, though sandbox:true limits exploitation from renderer)

### MINOR (5)

#### M1. `SettingsManager` instantiated in multiple files independently
- **Files:** `handlers/settings.ts:12`, `handlers/project.ts:11`, `handlers/lexicon.ts:25`, `index.ts:15`
- **Problem:** Each handler creates its own `SettingsManager` instance. They share the same file on disk (`config.json`) so data is consistent, but 4 separate instances is wasteful.
- **Fix:** Pass `SettingsManager` instance via `registerXxxHandlers(settings)` pattern, or use a singleton.
- **Risk:** Low (functionality correct, minor memory waste)

#### M2. `LexiconRepository` / `ProjectRepository` opened and closed repeatedly in handlers
- **Files:** `handlers/lexicon.ts:32-50`, `handlers/project.ts:47-52`
- **Problem:** `resolveProjectPath()` creates a new DB connection, creates a repository, queries, then closes — every time an IPC call arrives. For `lexicon:list`, this means 2 DB opens per call.
- **Fix:** Cache the DB connection per project path, or use a connection pool.
- **Risk:** Low (correctness OK, performance degradation on rapid calls)

#### M3. `OllamaManager.debugLog()` uses `process.env.APPDATA || ""` — empty string on Linux/Mac
- **File:** `OllamaManager.ts:11`
- **Problem:** On Linux/Mac, `APPDATA` is undefined, so `path.join("", "NovelTrad")` → `"NovelTrad"` (relative path). `fs.appendFileSync` will try to write to CWD, not `~/.config/NovelTrad`.
- **Fix:** Use `app.getPath('userData')` consistently (like SettingsManager does).
- **Risk:** Low (debug.log only,不影响 functionality)

#### M4. `router.ts` debugLog also uses `process.env.APPDATA || ""`
- **File:** `router.ts:11`
- **Problem:** Same as M3 — non-portable path.
- **Fix:** Same as M3.
- **Risk:** Low (debug.log only)

#### M5. No `"app:get-version"` channel validation
- **File:** `handlers/settings.ts:32`
- **Problem:** Handler registered but channel listed in `channels.ts` without issue. Minor — just noting it exists.
- **Risk:** None (informational)

---

## 3. Security Assessment

### ✅ Passed
- **Sandbox:** `sandbox: true` in webPreferences — Electron security baseline met
- **CSP:** Content Security Policy active in dev mode
- **IPC validation:** Zod schemas on all critical handlers (project, workflow, plugins, ollama, ai)
- **Path traversal:** `assertWithinProject()` used in PluginHost, ExportEngine, lexicon handler
- **Plugin permissions:** Sensitive permissions gated behind user confirmation
- **No `eval()` / `innerHTML` / `dangerouslySetInnerHTML`:** Clean
- **No bare `fetch()` in main process:** All migrated to `net.fetch()`
- **Plugin manifest validation:** Zod schema with entry .ts rejection

### ⚠️ Concerns
- **I3:** `project:open` lacks path validation (see above)
- **M1:** Multiple SettingsManager instances (data consistency OK but fragile)

---

## 4. Test Coverage Assessment

| Area | Status | Notes |
|---|---|---|
| OllamaManager | ✅ 100% | Target ≥90% |
| OllamaProvider | ✅ 98.98% | Target ≥90% |
| handlers/ollama.ts | ✅ 100% | Target ≥85% |
| RagEngine | ✅ 100% | — |
| IPC Router smoke | ✅ 12/12 | All modules load |
| Non-regression | ✅ | 782 tests, 0 failures |
| E2E (Ollama) | ⏳ | Requires live Ollama |

### Coverage Gaps (pre-existing, not from this session)
- `db/repositories/` — 3.5% (needs SQLite mocking)
- `handlers/history.ts` — 0%
- `handlers/project.ts` — 0%
- `managers/ProjectManager.ts` — 46%
- `managers/UpdateManager.ts` — 0%
- `managers/WorkflowEngine.ts` — 0%

---

## 5. Recommended Fix Priority

1. **I3** (project:open path validation) — Security, fix first
2. **I2** (console.log → logger) — Logging consistency, easy fix
3. **I1** (deduplicate debugLog) — Maintenance, moderate effort
4. **M3/M4** (APPDATA path portability) — Cross-platform, easy fix
5. **M1** (SettingsManager singleton) — Architecture, moderate effort
6. **M2** (DB connection caching) — Performance, defer to Phase 8

---

## 6. Conclusion

The codebase is **stable and ready for v2.1 release** after fixing I3 (security) and I2 (logging). The 3 important issues are all low-effort fixes. The 5 minor issues can be deferred or bundled into Phase 8/9.

**Recommendation:** Fix I3 + I2 now, commit, then proceed to Phase 10 (release v2.1).
