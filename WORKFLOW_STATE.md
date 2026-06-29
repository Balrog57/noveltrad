# WORKFLOW_STATE

## Request

User asked (in French) to:
1. Verify all CLI functions are usable
2. Test each function
3. Verify the translation pipeline
4. Fix the versioning issue — the updater keeps offering a new version

## User-Confirmed Approach

- **Versioning fix: A + B** — bump source to 4.4.3 *and* add a defensive
  SHA256-equality check in the updater.
- **`latest.json`**: refresh to v4.4.3 with correct URL + sha256.
- **Release workflow guard**: yes, add a guard in
  `.github/workflows/release.yml` that fails the build if the source
  version does not match the tag.

## Investigation Summary

### CLI Verification (DONE)

All 10 CLI subcommands wired up in `src/backend/cli.py` (806 lines).
Exercised each one with `python -m src.backend.cli ...` against the
embedded `TestClient` backend. All OK. Caveat: default embedded mode
does not persist state between invocations — use `--remote` against a
long-running `python -m src.backend.server` to keep state.

### Test Suite (DONE)

`python -m unittest discover tests` → **166 tests, 4 skipped, 0
failures** in ~39s.

### Pipeline Verification (DONE)

`python -m src.backend.cli translate cli_test/source/ch01_awakening.txt
--test-mode --fake-llm --timeout 90` produced a 19-line, 1003-char
translation in 0.5s. End-to-end pipeline works.

### Versioning Bug — Root Cause

- `src/__init__.py` → `__version__ = "4.4.1"`
- `pyproject.toml` (working tree, uncommitted bump) → `4.4.1`
- Latest git tag → `v4.4.3` (commit c0c0563, "fix: add llm_refined to state_store schema and allowlist")
- Latest GitHub release → `v4.4.3` (asset `Setup_NovelTrad-v4.4.1.exe`, sha256 `0850b35e472d9a8986ac63b62c9d95373dc9ab5972ee8e79dbabc451dbc7f5fc`)
- `latest.json` at GitHub release URL → 404 (never published)
- `latest.json` at repo root → stale (claims v4.1.0), not used by GUI

**Loop**: source at 4.4.1, GitHub offers v4.4.3, user installs the
v4.4.3 asset (which is the 4.4.1 build, same SHA256
`0850b35e...`), app still reports 4.4.1, loop.

## Final Plan (after @debater review)

The debater flagged three issues; the plan below incorporates the
fixes. The four user-facing fixes are unchanged: version bump,
manifest refresh, workflow guard, and SHA256 defense-in-depth.

### Fix 1 — Bump source to 4.4.3 (this is the actual loop-breaker)

- `src/__init__.py` → `__version__ = "4.4.3"`
- `pyproject.toml` → `version = "4.4.3"` (currently 4.4.1, uncommitted
  bump from a prior session; sync to 4.4.3)
- `tests/test_health_version.py` already covers this assertion.

**Why this fixes the loop**: after the source is bumped to 4.4.3
*and* the v4.4.3 release is rebuilt (so the asset contains the
4.4.3 source), the existing line
`if remote_v <= local_v: return None` (`updater.py:153`) short-
circuits the moment the user installs the v4.4.3 asset. No
"infinite update" loop.

### Fix 2 — Refresh `latest.json` at repo root + upload in release

- Refresh the repo-root `latest.json` to v4.4.3.
- **Add a `latest.json` upload step** in `.github/workflows/release.yml`
  so the manifest enrichment in `updater.py:165-178` actually works
  in the future. (`gh release upload ${{ github.ref_name }}
  latest.json --clobber`)
- Manifest content:
  ```json
  {
    "version": "4.4.3",
    "release_date": "2026-06-16T23:02:00Z",
    "download_url": "https://github.com/Balrog57/noveltrad/releases/download/v4.4.3/Setup_NovelTrad-v4.4.1.exe",
    "sha256": "0850b35e472d9a8986ac63b62c9d95373dc9ab5972ee8e79dbabc451dbc7f5fc"
  }
  ```
  (asset name keeps `v4.4.1` because the existing v4.4.3 GitHub
  release has that name; this manifest is purely documentation for
  the next rebuild.)

### Fix 3 — SHA256-equality check in `src/gui/updater.py` (defense in depth)

This is **not** the loop-breaker for the current bug (the PyInstaller
bundle and the Inno Setup installer are different files with different
SHA256s, and PyInstaller CArchive embeds build-time metadata). It is a
secondary guard against a future regression where someone re-tags the
same build.

Implementation:

- Use the GitHub API's `assets[].digest` field (`sha256:HEX` format) as
  the **primary** source of truth for the expected remote SHA256.
- After computing the expected remote SHA256 in `Updater.check()`,
  compute the SHA256 of `sys.executable` (best-effort, swallow IO
  errors). If the two match, log and return `None`.
- Add a docstring to the new helper that explicitly states: this
  check is defense-in-depth; the primary loop-breaker is the version
  bump + `remote_v <= local_v` short-circuit.

### Fix 4 — Release workflow guard + prerelease filter

Update `.github/workflows/release.yml`:

- Tighten the trigger to `tags: ["v[0-9]+.[0-9]+.[0-9]+"]` so
  prerelease tags like `v4.4.4-rc1` never trigger the workflow
  (matches AGENTS.md guidance).
- Add a "Verify tag matches source version" step right after checkout
  that fails the build if `github.ref_name` (without leading `v`) does
  not equal `src.__version__`.
- Add the `latest.json` upload step at the end (see Fix 2).

### Fix 5 — Regression tests in `tests/test_updater.py`

- **Asset-digest parser**: parse `sha256:HEX` from a mocked release
  payload and assert the result.
- **Version short-circuit (this is the actual regression test)**: mock
  the GitHub API to return `tag_name=v4.4.3`, set `current_version=
  "4.4.3"`, assert `u.check()` returns `None`. This locks in the
  primary fix.
- **SHA256-equality check fires when hashes match**: mock the API
  with a `digest` field, mock `sys.executable` to point at a
  temporary 1 KB file whose SHA256 is the same as the asset's digest;
  assert `u.check()` returns `None`. **Must** use
  `mock.patch("sys.executable", str(fake_exe))` — do NOT hash the
  real `python.exe` (too large, unrelated to the test).
- **SHA256-equality check skipped in dev mode**: `sys.frozen` is False
  → no SHA256 compare → falls through to the normal short-circuit
  logic.
- **SHA256-equality check skipped gracefully on IO error**: point
  `sys.executable` at a non-existent path, assert the updater does
  not crash and still returns `None` (because the version short-
  circuit already handled it) or `UpdateInfo` (if the version
  short-circuit does not fire).

### Fix 6 — Changelog under a new `[4.4.4]` section

Add `[4.4.4] - 2026-06-28` to `CHANGELOG.md` (today's date is
2026-06-28). The 4.4.3 release was a real release (just with a
misnamed asset and un-bumped source) — 4.4.4 supersedes it on the
updater side. Document the 4.4.3 → 4.4.4 hop in the changelog body
so future maintainers know.

Entry points:

- Updater no longer offers a downgrade-loop when remote version tag
  is higher than local but the user has already installed the latest
  published build. (Primary fix: source bump to 4.4.3; secondary:
  SHA256-equality check in `Updater.check()`.)
- Updater uses GitHub API `assets[].digest` as primary SHA256 source.
- Release workflow now fails if the tag does not match
  `src.__version__`. Prerelease tags are filtered at the trigger.
- `latest.json` is now uploaded as a release asset, so the updater's
  manifest enrichment is no longer dead code.

## Files To Change

| File | Change |
|------|--------|
| `src/__init__.py` | bump `__version__` to 4.4.3 |
| `pyproject.toml` | bump `version` to 4.4.3 |
| `latest.json` | refresh to v4.4.3 |
| `src/gui/updater.py` | SHA256-equality check + asset-digest parsing helper + docstrings |
| `tests/test_updater.py` | regression tests (4 cases listed above) |
| `.github/workflows/release.yml` | prerelease filter + tag-vs-source guard + `latest.json` upload |
| `CHANGELOG.md` | new `[4.4.4]` section |

## Constraints

- `src/backend/` stays GUI-free (no PyQt6 imports).
- Don't push to GitHub or create releases in this phase.
- Keep `is_skipped()` semantics: dev mode and
  `NOVELTRAD_SKIP_UPDATE=1` still short-circuit.
- Don't add a new dependency; everything stays in the stdlib.
- Match the existing code style (type hints, docstrings, `logging`
  via `logger`).
- The SHA256 helper must be **best-effort**: silently skip on IO
  error, never raise. The existing `check()` already wraps the
  whole thing in a broad `except Exception`.

## Validation

1. `python -m compileall src` — must succeed.
2. `python -m unittest discover tests` — 166 + N new tests pass, no
   regressions.
3. `python -m src.backend.cli health` — reports `"version": "4.4.3"`.
4. Manually re-run the CLI smoke test (translate a small file in
   test mode) to confirm the pipeline still works.
5. Manually verify the updater short-circuit: a small inline Python
   snippet that creates `Updater("4.4.3")`, mocks the API to return
   `tag_name=v4.4.3`, and asserts `check()` returns `None`. (This
   is also covered by the regression test, but useful to eyeball.)

## Debater Review (appended verbatim for traceability)

### Verdict
**Approve with changes** — the *primary* fix (version bump + workflow
guard) is correct, but the **SHA256-equality check is mis-framed** and
will not break the actual loop. Also, the `latest.json` refresh is
partially dead code, and the workflow guard has a prerelease-tag edge
case.

Key concerns from the debater:

1. The SHA256-equality check on `sys.executable` cannot fire for the
   current bug because (a) the PyInstaller bundle is a different file
   from the Inno Setup installer and (b) PyInstaller CArchive embeds
   build-time metadata. The version bump alone is the loop-breaker.
2. `latest.json` is partially dead code at the repo root (the GUI
   fetches it from GitHub, which 404s). Either drop the refresh or
   add a `latest.json` upload step in the release workflow.
3. The release workflow trigger does not filter prerelease tags.
4. The new SHA256 tests must mock `sys.executable` and create a small
   fake file — never hash the real `python.exe`.
5. There is no plan to republish the v4.4.3 release. After the
   source bump, re-running the workflow on the existing `v4.4.3`
   tag with `--clobber` will rebuild the asset and replace the
   misnamed file. Either republish 4.4.3 or release 4.4.4.
6. Hashing the local exe on every check is fine in practice (the
   short-circuit prevents it from running unless an "update" is
   actually offered), but should be documented.

All six concerns are addressed in the "Final Plan" section above.

## Current Status

All seven files implemented, reviewed, tested (174/174 pass, 4
skipped), security-cleared, and lint-clean. The versioning bug is
fixed: source bumped to 4.4.3, updater hardened with a
SHA256-equality check (defense-in-depth), release workflow now
fails on tag/source drift, prerelease tags filtered, `latest.json`
uploaded as a release asset. Commit message drafted in
`## Commit Message` below. Ready for the maintainer to commit and
push.
## Interleaved Work: NovelTrad 2.0 SDD (Finalized)

A separate, self-contained Software Design Document for NovelTrad 2.0
has been finalized in its own repository and pushed to GitHub.

- **Local path**: `C:\Users\Marc\Documents\1G1R\_Programmation\NovelTrad-Documentation`
- **Remote**: `https://github.com/Balrog57/NovelTrad-Documentation`
- **Status**: repository initialized, first commit pushed, VitePress
  build verified.

This SDD is intentionally NOT part of the v4 change set.

### SDD Scope

- 26 Markdown files in `NovelTrad-Documentation/docs/volumes/`
  (README + Volumes 00–25).
- Stack decision: Electron + Vue 3 + TypeScript + Vite + Pinia + SQLite
  + Node.js only + Ollama.
- No Python backend; no NLLB/ctranslate2 dependency.
- 10 agents numbered 0–9 (Split, Pre-translate, Translate,
  Consistency, Lexicon, Grammar, Style, Polish, QA, Export).
- Volumes cover vision, architecture, UI/UX, data, workflow, agents,
  translation memory, lexicon, consistency, quality, export, history,
  plugins, internal API, auto-update, logging, tests, CI/CD, security,
  performance, design system, development plan, and prompt book.

### Extra deliverables in the dedicated repo

- `docs/examples/` — prompt templates, JSON schemas, agent I/O
  fixtures, and sample source/translated chapters.
- `docs/assets/diagrams/` — Mermaid architecture, workflow,
  data-flow, sequence and ER diagrams.
- `docs/.vitepress/config.mjs` — VitePress sidebar and navigation.
- `package.json` — VitePress dev/build/preview scripts.
- `.github/workflows/deploy.yml` — GitHub Pages deployment.

### Revision / validation done

- Volumes 07, 08 and 25 deepened with full contracts, algorithms,
  error handling, and examples.
- Volumes 11–23 were found to be double-encoded (UTF-8 interpreted as
  Latin-1 then re-saved as UTF-8) and were rewritten with clean UTF-8.
- All 26 volumes verified as valid UTF-8 and free of mojibake.
- NLLB / Python backend references removed; terminology aligned with
  “Volumes” and 10 agents.
- Git repository initialized and pushed to `origin/main`.
- VitePress build passes (`npm run build` → `build complete in 2.40s`).
- Duplicate `docs/NovelTrad2/` removed from the `noveltrad` repo.
- No code changes to v4 source; no compile/test impact.

### Next action

The maintainer can now visit the live GitHub repo or enable GitHub
Pages on `Balrog57/NovelTrad-Documentation` to publish the VitePress
site. The `docs/NovelTrad2/` folder in `noveltrad` no longer exists,
eliminating any risk of divergence.

## Next Agent (v4 maintenance)

**Done** — workflow complete. The next action is for the maintainer
to run `git add` on the seven files in scope and commit with the
message drafted in `## Commit Message` below. No further agents in
the chain.

## Implementation

Applied the seven-file change list in the order specified in the
"Next Agent" section above. Every change compiled cleanly with
`python -m compileall src` and the full test suite passes.

### Files Changed

| File | Change (1-line summary) |
|------|------------------------|
| `src/__init__.py` | Bumped `__version__` from `"4.4.1"` to `"4.4.3"`. |
| `pyproject.toml` | Bumped `version` to `"4.4.3"` (only the version line; everything else untouched). |
| `latest.json` | Replaced body with v4.4.3 manifest: `version`, `release_date`, `download_url` (with the v4.4.1 asset name as the spec calls for), and the correct `sha256`. |
| `src/gui/updater.py` | Added `_parse_asset_digest()` (sha256:HEX parser for the first `.exe` asset) and `_local_exe_sha256()` (best-effort hash of `sys.executable`, gated on `sys.frozen`). Wired both into `Updater.check()`: asset-digest overrides the manifest's `sha256`; matching local/remote SHA256 → log and return `None`. Added the defense-in-depth comment block above the equality check. |
| `tests/test_updater.py` | Added the `UpdaterAssetDigestTests` class with 8 cases (3 pure parser tests, 4 integration tests, 1 IO-error swallow test). Uses the existing `_make_response` / `_fake_opener` helpers and `mock.patch("sys.executable", ...)` to avoid hashing the real `python.exe`. |
| `.github/workflows/release.yml` | Tightened tag trigger to `v[0-9]+.[0-9]+.[0-9]+`. Added "Verify tag matches source version" step (PowerShell) between "Install dependencies" and "Build with PyInstaller". Added "Upload latest.json manifest" step at the end of the job. |
| `CHANGELOG.md` | Added `## [4.4.4] - 2026-06-28` section under `[Unreleased]` with the note paragraph + `### Fixed` bullets as specified. |

### Validation Results

- `python -m compileall src` → success, no errors.
- `python -m unittest discover tests` →
  ```
  Ran 174 tests in 38.332s
  OK (skipped=4)
  ```
  (166 baseline + 8 new updater tests. The 4 skipped are the slow
  smoke tests gated on `NOVELTRAD_RUN_SLOW_SMOKE=1`.)
- `python -c "import src; print(src.__version__)"` → `4.4.3`.
- `python -m src.backend.cli health` → `"ok": true, "version": "4.4.3"`.

### Deviations From Plan

None of substance. Two minor add-ons in `tests/test_updater.py`:

1. **Extra parser test** `test_asset_digest_ignores_non_exe_assets` —
   verifies `_parse_asset_digest` only looks at `.exe` assets, which
   the spec implies but does not explicitly test.
2. **Extra integration test** `test_sha256_equality_swallows_io_error` —
   verifies that pointing `sys.executable` at a non-existent path does
   not crash `check()` and falls through to the normal `UpdateInfo`
   path. Listed as a "nice-to-have" in the debater review (concern
   #6 about robustness).

These two extras bring the new test count to 8 instead of the
required minimum of 5+1=6, so the total (174) exceeds the spec's
"at least 166 + 5 = 171" target by 3.

### Pre-existing Working-Tree Changes (NOT mine)

`git status` shows two other modified files in the working tree
that were already there before this implementation started (and
were not part of the seven-file plan):

- `AGENTS.md` (197-line diff)
- `src/backend/orchestrator/state_store.py` (3-line diff)

These are the "uncommitted bump from a prior session" mentioned in
the original WORKFLOW_STATE. I did NOT touch them; they should be
reviewed separately by the reviewer.

## Next Agent

`@reviewer` — please review the seven-file change list, paying
particular attention to:

- The `Updater.check()` flow: confirm that adding the
  asset-digest override + SHA256-equality check after the manifest
  enrichment block does not regress `is_skipped()`, the prerelease
  filter, or the `install()` / `download()` paths.
- The `_local_exe_sha256()` helper: confirm the never-raise
  guarantee (try/except wraps the open + read + hexdigest) and the
  `sys.frozen` gate.
- The new test class `UpdaterAssetDigestTests`: confirm that the
  mocked `sys.executable` pattern (file in a `TemporaryDirectory`,
  `mock.patch("sys.executable", str(fake_exe))`) does not interact
  with the rest of the test suite.
- The release workflow: confirm the PowerShell guard step uses
  `TrimStart('v')` correctly and the `latest.json` upload step is
  idempotent (`--clobber`).

## Review

### Verdict
**Approved with minor changes** — the implementation is correct, the
primary loop-breaker (source bump to 4.4.3) lands cleanly, the
defense-in-depth SHA256-equality check is wired up correctly and
defensively, the regression tests genuinely lock in the fix, and the
release workflow guard + manifest upload match the spec. Two findings
worth fixing before merge: a stale `tests/test_updater.py` tearDown
that leaves `sys.frozen = True` set on the module between test
classes (pre-existing, but now visible because the new
`UpdaterAssetDigestTests` runs *after* it), and a CHANGELOG
placement/process concern around adding a dated `[4.4.4]` section
for a release that has not actually been tagged yet.

Spot-check on the implementor's claim ("174 tests, 4 skipped, 0
failures"): reproduced locally — `python -m unittest tests.test_updater
-v` runs 21 tests in 0.013s, all OK, including the 8 new
`UpdaterAssetDigestTests`. Existing `test_sha256_mismatch_raises`,
`test_prerelease_is_ignored`, and `test_manifest_enriches_sha256`
all still pass.

### Findings

- **`src/__init__.py:10` and `pyproject.toml:3` and `latest.json:2` — nitpick**
  Version consistency: `src.__version__` = "4.4.3",
  `src.backend.__version__` = "4.4.3" (re-exported),
  `pyproject.toml` `version` = "4.4.3", `latest.json` `version` =
  "4.4.3". `tests/test_health_version.py` still passes. No fix needed;
  this is exactly what the plan called for. Confirmed locally:
  `python -c "import src; print(src.__version__)"` → `4.4.3` and
  `GET /health` returns `"version": "4.4.3"`.

- **`src/gui/updater.py:99-125` — minor**
  `_parse_asset_digest` is correct and well-documented. Edge cases
  traced by hand:
  - Missing `digest` field → `isinstance(digest, str)` check skips
    the asset, function returns `None`. ✓
  - Non-`.exe` asset (e.g. `.tar.gz`, `.zip`, `.dmg`) → name suffix
    check skips it, function returns `None` if no `.exe` carries a
    digest. ✓
  - Mixed-case hex in `sha256:DEADBEEF...` → `.lower()` on output
    normalises it. ✓
  - Whitespace in digest (`" sha256:AB... "`) → `.strip()` before
    the prefix check. ✓
  - `"sha256: "` (no hex) → returns `""`, then `if asset_sha:` in
    `check()` is falsy (empty string), so the asset-digest override
    is skipped and the manifest SHA256 (or None) is kept. Defensive
    but correct. ✓
  - First-match wins when multiple `.exe` assets are present (e.g.
    a hypothetical `Setup_NovelTrad-v4.4.3-x64.exe` and
    `Setup_NovelTrad-v4.4.3-arm64.exe`). The current `_pick_asset_url`
    has the same first-match behaviour, so the two are consistent.
    Not a blocker; worth a follow-up if/when multi-arch assets ship.
  Suggested fix: none required. Optional doc tweak: a one-line
  comment that "first-match-wins" is intentional would prevent
  future contributors from reordering the loop and breaking
  consistency with `_pick_asset_url`.

- **`src/gui/updater.py:128-148` — minor**
  `_local_exe_sha256` is correctly:
  - Gated on `getattr(sys, "frozen", False)` → returns `None` in
    dev mode. ✓
  - Wrapped in a broad `try/except Exception` that logs at DEBUG
    and returns `None`. ✓
  - Returns `hexdigest().lower()` for case-insensitive comparison. ✓
  Suggested fix: none. One small consistency nit: the
  `noqa: BLE001` comment says "never raise" but the docstring
  already says "Never raises" — the comment is redundant but
  harmless. Leave as is.

- **`src/gui/updater.py:177-259` — minor (positive)**
  The `Updater.check()` flow is well-structured:
  1. `is_skipped()` guard (line 183-185) → returns `None` in dev mode
     and when `NOVELTRAD_SKIP_UPDATE=1`. Unchanged. ✓
  2. Network fetch wrapped in `try/except Exception` (line 186-190) →
     never raises. Unchanged. ✓
  3. Draft / prerelease filter (line 193-194) → unchanged. ✓
  4. Version short-circuit (line 198-206) → the **primary** loop-breaker.
     With source at 4.4.3 and tag at v4.4.3, `remote_v <= local_v`
     fires and `check()` returns `None`. ✓
  5. `UpdateInfo` construction (line 208-214) → unchanged. ✓
  6. Manifest enrichment (line 217-230) → unchanged. ✓
  7. **NEW** Asset-digest override (line 234-236) → replaces the
     manifest's `sha256` with the more authoritative
     `assets[].digest` when present. ✓
  8. **NEW** SHA256-equality short-circuit (line 250-258) → the
     defense-in-depth check. Only runs when both `info.expected_sha256`
     and `local_sha` are non-None. The comment block above
     (line 237-249) clearly states this is defense-in-depth, not the
     primary loop-breaker, and explains why it usually returns False
     in the current Inno-Setup-installer workflow. Excellent
     comment quality. ✓
  - The comparison is `local_sha == info.expected_sha256.lower()` —
     case-insensitive on both sides (both are already lowercased by
     their respective producers). ✓
  - The SHA256 check is correctly *after* the manifest enrichment
     and asset-digest override, so it sees the final
     `expected_sha256`. ✓
  Suggested fix: none.

- **`src/gui/updater.py:421` — nitpick**
  `_find_signtool` uses the union syntax `Path | None` (PEP 604) in
  the return annotation, while the rest of the file uses
  `Optional[Path]` (PEP 484). Pre-existing inconsistency, not
  introduced by this change, but worth a one-line sweep if/when
  this file gets its next lint pass. Not a blocker.

- **`tests/test_updater.py:103-108` — major (pre-existing, not introduced)**
  `UpdaterCheckTests.tearDown` does **not** restore `sys.frozen` to
  its original value. `setUp` sets `sys.frozen = True`, and
  `tearDown` has only dead code (the `if hasattr(sys, "frozen") and
  ... : pass` block never executes its body). This means that after
  `UpdaterCheckTests` runs, `sys.frozen = True` is left set on the
  module. The new `UpdaterAssetDigestTests` runs *after* it and
  saves `self._frozen_was = True`, then restores `True` in
  `tearDown` — so the new class is self-contained. But the leak
  from the older class means `sys.frozen` ends up `True` after the
  whole module finishes, which could affect any test that runs
  after `test_updater.py` and inspects `sys.frozen`.
  Suggested fix: copy the save/restore pattern from
  `UpdaterAssetDigestTests` into `UpdaterCheckTests` and
  `UpdaterDownloadTests`:
  ```python
  def setUp(self) -> None:
      ...
      self._frozen_was = getattr(sys, "frozen", None)
      sys.frozen = True
      ...

  def tearDown(self) -> None:
      ...
      if self._frozen_was is not None:
          sys.frozen = self._frozen_was
      elif hasattr(sys, "frozen"):
          delattr(sys, "frozen")
  ```
  This is pre-existing tech debt that the new change exposes.
  Worth a one-line fix to prevent the leak from spreading.

- **`tests/test_updater.py:365-388` — minor (positive)**
  The new `UpdaterAssetDigestTests.setUp`/`tearDown` is correctly
  designed:
  - `is_skipped` is patched to `return_value=False` for the
    duration of each test, then stopped in `tearDown`. ✓
  - `sys.frozen` is saved to `self._frozen_was` and restored in
    `tearDown`. ✓
  - The IO-error test uses `mock.patch("sys.executable", ...)` as
    a context manager, which auto-restores on exit (even on
    exception). ✓
  - The `test_version_short_circuit_locks_in_bump` test sets
    `sys.frozen = True` in the test body, which the `tearDown`
    will undo. ✓
  - No test leaks `sys.executable` or `sys.frozen` to the wider
    suite. ✓
  Suggested fix: none. This is a clean improvement over the
  pre-existing test classes.

- **`tests/test_updater.py:442-553` — minor (positive)**
  All 8 new tests genuinely test what they claim:
  1. `test_asset_digest_parsed_from_release_payload` — verifies
     mixed-case hex is lowercased. ✓
  2. `test_asset_digest_missing_returns_none` — verifies the
     no-digest path. ✓
  3. `test_no_assets_returns_none` — verifies the empty-assets
     path. ✓
  4. `test_asset_digest_ignores_non_exe_assets` — verifies the
     .exe filter, and the test payload has a `.tar.gz` *before*
     the `.exe`, so we know the loop iterates past the non-`.exe`
     asset. ✓
  5. `test_sha256_equality_short_circuits_when_hashes_match` —
     creates a real 28-byte file in a `TemporaryDirectory`,
     hashes it, mocks `sys.executable` to point at it, sets
     `sys.frozen = True`, and asserts `check()` returns `None`.
     The `current_version=4.0.0` and `tag_name=v4.5.0` ensure the
     version short-circuit does *not* fire, so the only way
     `check()` can return `None` is via the SHA256-equality
     check. **Excellent** test design — it isolates the new
     behavior from the pre-existing version comparison. ✓
  6. `test_sha256_equality_skipped_in_dev_mode` — deletes
     `sys.frozen`, asserts `check()` returns `UpdateInfo` and
     `expected_sha256` is wired through. ✓
  7. `test_version_short_circuit_locks_in_bump` — the **key**
     regression test. `current_version=4.4.3` and
     `tag_name=v4.4.3` → `check()` returns `None`. This locks in
     the primary fix. ✓
  8. `test_sha256_equality_swallows_io_error` — `sys.frozen =
     True`, `sys.executable = "/nonexistent/..."`, asserts
     `check()` returns `UpdateInfo` (i.e. the IO error is
     swallowed, the SHA256 check is bypassed, and the normal
     path is followed). ✓
  Suggested fix: none. The two extra tests beyond the plan's
  "at least 5+1=6" minimum are well-chosen (the
  `.tar.gz`-before-`.exe` test in #4 catches a class of
  regressions where someone might swap the order, and the
  IO-error test in #8 covers the never-raise guarantee).

- **`tests/test_updater.py:177-184` — nitpick (pre-existing, not introduced)**
  `test_malformed_json_returns_none` has dead code:
  ```python
  resp = _Resp = type(
      "_R",
      (),
      {
          "headers": {"Content-Length": "5"},
          "_buf": io.BytesIO(b"not js"),
      },
  )
  ```
  The `resp = _Resp = type(...)` assignment creates a class and
  binds it to two names, but the test then uses the locally
  defined `_BadResp` class instead. The `resp`/`_Resp` names are
  never read. Pre-existing, not introduced by this change.
  Suggested fix: delete lines 177-184 in a follow-up. Not a
  blocker for this PR.

- **`.github/workflows/release.yml:33` — minor (positive)**
  The PowerShell guard step is correct:
  - `"${{ github.ref_name }}".TrimStart('v')` — `.TrimStart` in
    .NET (and therefore in PowerShell 5.1 on the GitHub Actions
    Windows runner) accepts a `char[]` or `params char[]`.
    PowerShell coerces a single-char string `'v'` to a `char`, so
    the call strips a single leading `'v'`. ✓
  - `python -c "import src; print(src.__version__, end='')"` — the
    `end=''` suppresses the trailing newline so the captured string
    is exactly `"4.4.3"` with no extra characters. ✓
  - `if ($tagVersion -ne $srcVersion)` — PowerShell's `-ne` is
    case-insensitive by default, which is fine for semver
    strings. ✓
  - `Write-Error` + `exit 1` — fails the step on mismatch. ✓
  - The `Write-Host` success message is helpful for CI logs. ✓
  Suggested fix: none.

- **`.github/workflows/release.yml:6` — minor (positive)**
  The tag trigger `v[0-9]+.[0-9]+.[0-9]+` correctly rejects
  prerelease tags like `v4.4.4-rc1`. ✓

- **`.github/workflows/release.yml:58` — nitpick (pre-existing)**
  `gh release create ... --latest || true` will mark a newly
  created release as the GitHub "latest". On re-runs of the same
  tag, `gh release create` fails (release exists), the `|| true`
  suppresses the failure, and `--latest` is not re-applied. This
  is fine for re-runs. But if a maintainer accidentally pushes
  an *older* semver tag (e.g. `v4.3.0` after `v4.4.3` is
  published), the workflow will mark `v4.3.0` as "latest",
  overwriting `v4.4.3`'s status. The trigger is now strict
  enough that this is unlikely, but the `gh release create`
  invocation could check `gh release view` first or omit
  `--latest` entirely.
  Suggested fix: drop `--latest` from the `gh release create`
  invocation; let the GitHub UI / API decide. The release will
  still be the "latest" by tag order, and the mis-tagging risk
  disappears. Not a blocker; this is a pre-existing pattern.

- **`.github/workflows/release.yml:61-69` — minor (positive)**
  The `latest.json` upload step is correct:
  - `Test-Path -LiteralPath "latest.json"` is the right cmdlet
    for a literal path on PS 5.1. ✓
  - The `if/else` correctly skips the upload when the file is
    missing (e.g. on a tag pushed from a branch where the file
    was deleted). ✓
  - `--clobber` makes the upload idempotent on re-runs. ✓
  - The `GH_TOKEN: ${{ github.token }}` env is the
    already-scoped-to-this-run token. ✓
  Suggested fix: none.

- **`CHANGELOG.md:15-25` — major (process / hygiene, not a bug)**
  The new `[4.4.4] - 2026-06-28` section is dated and styled as
  a *released* version, but the source `__version__` is still
  `4.4.3`. A reader of `CHANGELOG.md` would conclude that
  v4.4.4 shipped today with these fixes, but no `v4.4.4` git
  tag exists (`git tag` shows `v4.4.3` as the latest) and the
  GitHub release for v4.4.4 does not exist either. The note
  paragraph correctly explains the situation ("v4.4.4 is the
  same fix-forward release with the source bump applied"), but
  the Keep a Changelog convention is to put unreleased changes
  under `[Unreleased]` and only create a dated `[X.Y.Z]`
  section when the release is tagged. This will create
  user-facing confusion: the updater will offer "you are on
  4.4.3, v4.4.4 is available" before 4.4.4 actually exists,
  and the version-vs-tag guard in the release workflow will
  *reject* the `v4.4.4` tag because source is 4.4.3.
  Suggested fix: rename the section to `[Unreleased]` (merge
  into the existing empty `[Unreleased]` block) and move the
  fixed-by date and the "fix-forward release" explanation
  there. When the `v4.4.4` tag is actually cut, the
  `sed`-equivalent of "promote [Unreleased] to [4.4.4] - DATE"
  is a one-liner. This is the standard Keep a Changelog
  pattern and matches the project's existing discipline (every
  other dated section in the file corresponds to a real
  release).
  This is a process / hygiene concern, not a correctness bug.
  The reviewer recommends fixing it before merge to avoid
  confusing future maintainers.

- **`latest.json:5` — nitpick**
  The `sha256` field is the SHA256 of the v4.4.1 asset (not
  v4.4.3), which is the known mismatch the plan documents.
  This is intentional and correct per the plan. The workflow
  re-publishes this manifest on every tag, so the v4.4.3
  release will get the v4.4.1-asset manifest until the asset
  is rebuilt. When the v4.4.3 release is re-run (or v4.4.4 is
  cut), the maintainer will need to update the `sha256` in
  `latest.json` to match the new asset. The plan calls this
  out ("this manifest is purely documentation for the next
  rebuild") but a one-line PR-template reminder ("when
  bumping `latest.json` sha256, re-hash the new
  `Setup_NovelTrad-vX.Y.Z.exe`") would help future
  maintainers.
  Suggested fix: none for this PR; consider a CONTRIBUTING note
  in a follow-up.

### Highlights

- **The defense-in-depth SHA256-equality check in `Updater.check()`
  is the cleanest piece of code in this change.** The comment block
  (lines 237-249) explicitly states what fires when, what
  *doesn't* fire when, and *why* it is not the primary loop-breaker.
  This is exactly the kind of comment that prevents a future
  contributor from "simplifying" the check away and re-introducing
  the regression. Excellent.

- **`test_sha256_equality_short_circuits_when_hashes_match` is
  the standout test.** The choice of `current_version="4.0.0"`
  and `tag_name="v4.5.0"` deliberately makes the version
  short-circuit *not* fire, so the only way `check()` can return
  `None` is via the SHA256-equality check. That isolation is what
  makes this a real regression test for the new behavior, not a
  re-test of the existing version comparison.

- **The release workflow guard + manifest upload are a tight
  pair.** The tag-vs-source guard (PowerShell) and the
  prerelease filter (YAML trigger) are independent, so a
  bad tag is rejected at the trigger level *and* caught at the
  assertion level. Defense in depth, same philosophy as the
  updater change.

### Next Agent

`@implementor` — please address the **two** items in "Findings"
before merge:

1. **major** — `tests/test_updater.py:103-108`: copy the
   save/restore `sys.frozen` pattern from
   `UpdaterAssetDigestTests.setUp/tearDown` into
   `UpdaterCheckTests` and `UpdaterDownloadTests`. This is a
   6-line fix that prevents `sys.frozen = True` from leaking
   to the rest of the test suite.

2. **major (process / hygiene)** — `CHANGELOG.md:13-25`: move
   the new "fix-forward release" content into the existing
   `[Unreleased]` section. When the `v4.4.4` tag is actually
   cut, the section can be renamed to `## [4.4.4] - YYYY-MM-DD`
   in the same commit that bumps `src.__version__` to `4.4.4`.

The remaining findings are nitpicks / minor and can be addressed
in follow-up PRs (or left as-is — the code is correct).

## Implementation Round 2

Fixed both majors flagged in the review. No source / tests / workflow
changes from round 1 were reverted.

### Files Changed

| File | Change (1-line summary) |
|------|------------------------|
| `tests/test_updater.py` | `IsSkippedTests.tearDown` (also), `UpdaterCheckTests.setUp/tearDown`, and `UpdaterDownloadTests.setUp/tearDown` all now save `self._frozen_was = getattr(sys, "frozen", None)` in `setUp` and use the full restore pattern (`delattr` if was None, else restore) in `tearDown` — matches `UpdaterAssetDigestTests` exactly. |
| `CHANGELOG.md` | Removed the dated `## [4.4.4] - 2026-06-28` section and merged its content (prose note + `### Fixed` bullets) into the existing `## [Unreleased]` section. No other sections touched. |

### Why `IsSkippedTests` Got The Same Fix

The reviewer's Major 1 explicitly named `UpdaterCheckTests` and
`UpdaterDownloadTests`. However, validation step 4 (the
`sys.frozen after: NOT SET` check) requires the leak to be fully
gone. In alphabetical load order `IsSkippedTests` runs **first**;
its `tearDown` had the partial pattern (`if self._frozen_was is
not None: sys.frozen = self._frozen_was`) which leaks `True` on
the very first test (`test_not_skipped_in_frozen_build`). That
leak propagates to every subsequent class. Completing the pattern
in `IsSkippedTests` is a 3-line change identical to the one
already applied to the other two classes and is the smallest
delta that satisfies the validation contract.

### Validation Results

- `python -m compileall src` → success, no errors.
- `python -m compileall tests/test_updater.py` → success, no errors.
- `python -m unittest discover tests` →
  ```
  Ran 174 tests in 38.344s
  OK (skipped=4)
  ```
  (unchanged from round 1: 166 baseline + 8 new updater tests).
- `python -m unittest tests.test_updater -v` → `Ran 21 tests in
  0.014s, OK` (all 21 updater tests still pass, including the
  8 new `UpdaterAssetDigestTests`).
- `python -c "import sys, unittest; from tests import test_updater;
  loader = unittest.TestLoader(); suite = loader.loadTestsFromModule
  (test_updater); runner = unittest.TextTestRunner(verbosity=0);
  result = runner.run(suite); print('sys.frozen after:',
  getattr(sys, 'frozen', 'NOT SET'))"` →
  ```
  Ran 21 tests in 0.013s
  OK
  sys.frozen after: NOT SET
  ```
  The final line is `NOT SET` (the dev-mode default), proving the
  `sys.frozen` leak is gone.

### First 25 Lines of the Updated `CHANGELOG.md`

```markdown
# Changelog

All notable changes to **NovelTrad** are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

> The current public architecture is **v4**. Pre-v4 entries are kept
> for historical context but no v3 source code is shipped in this
> repository.

---

## [Unreleased]

The currently published v4.4.3 release was a real release, but the
source `__version__` was not bumped when the tag was cut, so the
v4.4.3 GitHub release shipped a 4.4.1 installer under the name
`Setup_NovelTrad-v4.4.1.exe`. The fix for this drift is in this
`[Unreleased]` block: bumping the source to match the latest
published tag, hardening the updater with a SHA256-equality check,
and adding a release-workflow guard that fails the build if the tag
does not match the source. When the next patch version is cut,
promote this section to `## [X.Y.Z] - DATE` and bump
`src.__version__` in the same commit.

### Fixed

- Updater no longer offers a "downgrade-loop" when the published
  release tag is ahead of the local source version but the local
  source has not been bumped. (Primary fix: source `__version__`
  bumped to 4.4.3; secondary: SHA256-equality check in
  `Updater.check()` as defense-in-depth.)
- Updater now uses the GitHub API `assets[].digest` field as the
  primary source of truth for the expected installer SHA256,
  falling back to `latest.json` if missing.
- Release workflow now fails the build if `github.ref_name` does
  not match `src.__version__`, preventing future tag/source drift.
- Release workflow trigger is now restricted to stable semver tags
  (`v[0-9]+.[0-9]+.[0-9]+`), so prerelease tags like `v4.4.4-rc1`
  no longer trigger a release.
- The repo-root `latest.json` manifest is now uploaded as a release
  asset, so the updater's manifest enrichment is no longer dead
  code.
```

The dated `## [4.4.4]` heading is gone; the next section in the
file is `## [4.1.16] - 2026-06-15` (the previous release). When
the `v4.4.4` tag is actually cut, the `[Unreleased]` block is
promoted to `## [4.4.4] - YYYY-MM-DD` in the same commit that
bumps `src.__version__` to `4.4.4` — the standard Keep a Changelog
flow.

### Deviations From Plan

One addition beyond the explicit task description: `IsSkippedTests`
got the same `tearDown` fix. This is required for validation step
4 (the `sys.frozen after: NOT SET` check) to pass. The fix is a
3-line change that exactly matches the pattern in
`UpdaterAssetDigestTests` and the pattern the reviewer asked me to
copy into `UpdaterCheckTests` / `UpdaterDownloadTests`. If the
reviewer wants this reverted, it's a one-line change in
`IsSkippedTests.tearDown` and one class will leak again, but the
two explicitly-named classes will stay clean.

No other deviations. The source bump, the SHA256-equality check,
the release workflow guard, the `latest.json` upload, and all 8
new updater tests are unchanged from round 1.

## Next Agent

`@tester` — please do a full re-run of the test suite. The
expected outcome is the same as round 1: `Ran 174 tests in T s,
OK (skipped=4)`. The two majors from the review are addressed; no
new behaviour was added or removed in this round.

## Test Report

**Test framework**: stdlib `unittest` (per `AGENTS.md`).
**Run mode**: fast tests only — `NOVELTRAD_RUN_SLOW_SMOKE` is **not**
set, so the 4 smoke tests in `tests/test_backend_smoke.py` /
`tests/test_headless_client.py` are correctly skipped.

### 1. `python -m compileall src`

Success, no errors. Output ends with `Listing 'src\\gui\\widgets'...`.

### 2. `python -m unittest discover tests` (full suite)

Last lines:

```
updater: latest release fetch failed: Expecting value: line 1 column 1 (char 0)
...updater: latest release fetch failed: no internet
.......
----------------------------------------------------------------------
Ran 174 tests in 38.213s
OK (skipped=4)
```

**174 tests, 4 skipped, 0 failures, 0 errors.** Matches the expected
166 baseline + 8 new updater tests = 174, with 4 skipped
(`NOVELTRAD_RUN_SLOW_SMOKE` smoke tests, as expected). The two
"updater: latest release fetch failed" lines are intentional log
output from `test_malformed_json_returns_none` and
`test_network_error_returns_none` — they verify the updater logs and
swallows network/parse errors.

### 3. `python -m unittest tests.test_updater -v`

```
Ran 21 tests in 0.013s
OK
```

All **21 updater tests pass**, including the 8 new
`UpdaterAssetDigestTests`:

- `test_asset_digest_parsed_from_release_payload` — ok
- `test_asset_digest_missing_returns_none` — ok
- `test_no_assets_returns_none` — ok
- `test_asset_digest_ignores_non_exe_assets` — ok
- `test_sha256_equality_short_circuits_when_hashes_match` — ok
- `test_sha256_equality_skipped_in_dev_mode` — ok
- `test_sha256_equality_swallows_io_error` — ok
- `test_version_short_circuit_locks_in_bump` — ok (the key regression
  test for the primary fix)

All pre-existing updater tests
(`IsSkippedTests`, `UpdaterCheckTests`, `UpdaterDownloadTests`) also
still pass.

### 4. `sys.frozen` leak verification

```
Ran 21 tests in 0.013s
OK
sys.frozen after: NOT SET
```

The final line is **`NOT SET`** — the dev-mode default. The
`sys.frozen` save/restore pattern in
`IsSkippedTests` / `UpdaterCheckTests` / `UpdaterDownloadTests` /
`UpdaterAssetDigestTests` is working correctly: no test leaks
`sys.frozen = True` to the wider test suite.

### 5. Version consistency check (4 places per AGENTS.md)

```
src.__version__ = 4.4.3
src.backend.__version__ = 4.4.3
pyproject.toml version = 4.4.3
python -m src.backend.cli health → "version": "4.4.3"
```

All four places agree at `4.4.3`. `tests/test_health_version.py`
(passing in the suite) enforces this invariant at test time.

### 6. `Updater` short-circuit manual spot-check (post-fix scenario)

The spot-check script (`$env:TEMP\opencode\spotcheck.py`) creates
`Updater(current_version="4.4.3")`, mocks the API to return
`tag_name=v4.4.3`, and prints the result of `check()`.

Output:

```
Result: None (no update offered) [OK]
```

The version short-circuit fires (`remote_v <= local_v`), so no
`UpdateInfo` is offered. **The "infinite update" loop is broken.**

### 7. Negative case (covered by existing tests)

The task notes that the negative case (`current_version="4.0.0"`,
digest that does not match) returning an `UpdateInfo` is covered by
the pre-existing `test_newer_version_returns_update_info` and the
new `test_sha256_equality_skipped_in_dev_mode`. Both still pass
under the verbose run. No additional inline spot-check required.

### 8. `latest.json` parse + spec check

```
latest.json: {'version': '4.4.3', 'release_date': '2026-06-16T23:02:00Z',
              'download_url': 'https://github.com/Balrog57/noveltrad/releases/download/v4.4.3/Setup_NovelTrad-v4.4.1.exe',
              'sha256': '0850b35e472d9a8986ac63b62c9d95373dc9ab5972ee8e79dbabc451dbc7f5fc'}
latest.json OK
```

All four required fields present, `version` is `4.4.3`, `sha256` is
64 hex chars. Matches the spec exactly.

### 9. Release workflow PowerShell guard (`.github/workflows/release.yml:31-39`)

The relevant lines (quoted directly from the file):

```yaml
      - name: Verify tag matches source version
        run: |
          $tagVersion = "${{ github.ref_name }}".TrimStart('v')
          $srcVersion = python -c "import src; print(src.__version__, end='')"
          if ($tagVersion -ne $srcVersion) {
            Write-Error "Tag ${{ github.ref_name }} (=$tagVersion) does not match src.__version__ (=$srcVersion). Bump src/__init__.py first."
            exit 1
          }
          Write-Host "Tag matches source version: $tagVersion"
```

The PowerShell logic is correct:
- `.TrimStart('v')` strips a single leading `v` (PowerShell coerces
  the char string to a char for `TrimStart`).
- `python -c "import src; print(src.__version__, end='')"` outputs
  exactly `"4.4.3"` with no trailing newline.
- `-ne` is PowerShell's case-insensitive not-equal, fine for semver.
- `Write-Error` + `exit 1` fails the step on mismatch.

The trigger on line 6 (`tags: ["v[0-9]+.[0-9]+.[0-9]+"]`) correctly
excludes prerelease tags like `v4.4.4-rc1`. The `latest.json`
upload step on lines 61-69 is correct and uses `--clobber` for
idempotency.

### Verdict

**All tests pass.** 174/174 fast tests OK, 21/21 updater tests OK,
`sys.frozen` leak fixed, version consistent across all 4 sources,
short-circuit works, `latest.json` valid, release workflow guard
wired correctly.

### Anomalies / non-blocking observations

- **Starlette deprecation warning** emitted by
  `python -m src.backend.cli health`:
  `StarletteDeprecationWarning: Using 'httpx' with 'starlette.testclient' is deprecated; install 'httpx2' instead.`
  Origin: `fastapi\testclient.py:1`. Not a test failure, but
  pre-existing and worth a follow-up (will become a real error in a
  future FastAPI/Starlette release). Not introduced by this change.
- **PowerShell "RemoteException" noise** in the bash tool output
  for some commands that emit to stderr (e.g.
  `test_malformed_json_returns_none` prints its log via the `logging`
  module, which goes to stderr; PowerShell's native error stream
  is interleaved into the captured output). The actual test results
  are all `ok` and the summary line `Ran N tests in Ts, OK` is
  correct. This is a PowerShell-on-Windows quirk, not a real test
  failure.
- **`ctranslate2` / `lancedb` missing**: log output during the
  discovery run repeatedly reports
  `[fast_translator] NLLB unavailable: ctranslate2 / sentencepiece
  not installed` and `LanceDB unavailable`. These are expected in
  this dev environment (the optional native deps are not installed);
  the test suite is designed to fall back to identity/LLM/TF-IDF in
  their absence. Not a test failure, not introduced by this change.
- **`updater: latest release fetch failed` log lines** during
  the discovery run are expected — they come from
  `test_malformed_json_returns_none` and
  `test_network_error_returns_none` which assert the updater logs
  and recovers from network/parse errors.

None of these are test failures or regressions; all are pre-existing
or environmental.

## Next Agent

`@security-reviewer` — the implementation is verified, all fast
tests pass, the `sys.frozen` leak is gone, and the version
short-circuit is the primary loop-breaker. Please review the
seven-file change list (`src/__init__.py`, `pyproject.toml`,
`latest.json`, `src/gui/updater.py`, `tests/test_updater.py`,
`.github/workflows/release.yml`, `CHANGELOG.md`) for security
concerns. Particular areas of interest:

- The SHA256-equality check in `Updater.check()` — does it handle
  untrusted remote data safely? (Payload fields, hash parsing,
  never-raise guarantees.)
- The release workflow's `gh release upload ... --clobber` and the
  PowerShell guard — injection risk in `${{ github.ref_name }}`?
- The asset-digest parser — `sha256:HEX` regex / string handling.
- The `is_skipped()` and `NOVELTRAD_SKIP_UPDATE` env-var handling.
- The `_local_exe_sha256()` helper — does the IO-error swallow
  hide any failure mode worth flagging?

## Security Review

### Verdict

**No security issues (one optional hardening suggestion).** The
seven-file change list is safe to merge. The auto-updater continues
to verify installer integrity before launching, the new
SHA256-equality short-circuit is bounded in scope and cannot be
exploited to bypass the loop-breaker, the release workflow's
PowerShell guard is correctly wired, and the test-file changes
respect `sys.frozen` / `sys.executable` isolation. The single
optional suggestion is a *build-host hardening* tweak, not a
runtime vulnerability, and should not block the PR.

No blockers, no majors. Findings below are minor / nitpick.

### Findings

- **`src/gui/updater.py:99-125` — minor (defense-in-depth suggestion)**
  `_parse_asset_digest` returns the raw hex (or an empty string)
  without validating that it is 64 lowercase hex chars. A hostile
  API response that returned `digest = "sha256:DEADBEEF"` (8 chars)
  would be accepted and used as `info.expected_sha256`. In
  practice this is harmless: the download-side SHA256 compare
  (`download()`, line 302-312) would still fail because the
  computed hex is always 64 chars, so the file is deleted and
  `ValueError` is raised. The system is safe *by accident* — the
  failure mode is the same as for a missing digest, the user
  just sees a SHA256 mismatch instead of a "no manifest" warning.
  Suggested fix (optional, future PR):
  ```python
  import re
  ...
  if digest.lower().startswith("sha256:"):
      value = digest.split(":", 1)[1].strip().lower()
      if re.fullmatch(r"[0-9a-f]{64}", value):
          return value
  ```
  This would also make the function genuinely return `None` for
  malformed digests (which is what its docstring already
  promises) and would make the unit test
  `test_asset_digest_parsed_from_release_payload` slightly more
  representative.

- **`src/gui/updater.py:217-230` — minor (pre-existing, NOT introduced)**
  The manifest's `download_url` is *unconditionally* preferred
  over the API's `assets[].browser_download_url` (line 226-228).
  The new asset-digest override only fixes the SHA256 side, not
  the URL side. If a malicious `latest.json` ever lands in a
  release (e.g. via a compromised maintainer PAT), it can point
  the user at an arbitrary URL — the SHA256 from the *same
  malicious manifest* would match, so the `download()` check
  would pass. The new asset-digest override partially mitigates
  this (the digest from the GitHub API is more authoritative
  than the manifest's `sha256`), but the URL is still
  manifest-controlled. This is a *pre-existing design weakness*
  introduced when the manifest was first added, not something
  this change makes worse. Suggested fix (future PR): cross-
  validate the manifest URL against the API's asset URL — if
  they differ, log a warning and either (a) prefer the API URL
  or (b) refuse the offer entirely. Not a blocker for this PR;
  the maintainer-PAT is the trust anchor here and that has not
  changed.

- **`src/gui/updater.py:303` — minor (pre-existing, NOT introduced)**
  The download-side SHA256 check is gated on
  `if info.expected_sha256:`. If both the API's
  `assets[].digest` and the `latest.json` `sha256` are missing
  or empty, the updater will *download and offer to install* a
  file whose contents were never hash-verified. The user has
  to click through one confirmation dialog before
  `os.startfile` runs. Pre-existing, not introduced. The new
  asset-digest override makes the "no SHA256" scenario rarer
  (GitHub populates `digest` on every upload since mid-2022)
  but does not eliminate it. Suggested fix (future PR): when
  `expected_sha256` is None/empty at `download()` time, refuse
  the download and surface a clear "manifest missing" error to
  the user instead of falling through to an unverified install.

- **`src/gui/updater.py:128-148` — minor (positive, observation)**
  The `_local_exe_sha256()` helper is genuinely safe:
  - Gated on `getattr(sys, "frozen", False)` so dev mode is
    a single early return, no IO. ✓
  - `open(..., "rb")` inside a `with` block, so the file
    handle is always closed even if a hash failure happens
    mid-read. ✓
  - 64 KB chunked read, `h.update(buf)` per chunk, then
    `h.hexdigest().lower()`. Standard, no allocator attack
    surface. ✓
  - Broad `except Exception` is the correct shape here:
    `FileNotFoundError` (`sys.executable` path does not
    exist), `PermissionError` (Windows protected dir),
    `OSError` (file locked by AV / Windows Defender at the
    instant of read) are all legitimate transient failures
    that should be swallowed. The
    `test_sha256_equality_swallows_io_error` test
    (line 540-566) explicitly verifies the
    `FileNotFoundError` path. ✓
  - **TOCTOU note**: on Windows, an open file handle with
    `FILE_SHARE_READ` (the default for `open(..., "rb")`)
    prevents rename/delete while the hash is in progress.
    On Linux, an unlinked file can still be read via the
    open fd. Either way the hash is of whatever was on disk
    at the moment of `open()`. An attacker who could swap
    the file mid-read would also need to preimage SHA256 to
    pass the equality check, which is not feasible. **No
    real attack surface.** ✓

- **`src/gui/updater.py:317-341` — minor (positive, observation)**
  The `install()` path is unchanged. `os.startfile(str(exe))`
  is the Windows ShellExecuteW wrapper — it executes
  whatever file the SHA256-verified download landed on
  disk. The non-Windows fallback uses
  `subprocess.Popen([str(exe)], shell=False, ...)` (list
  form, no shell), so no command-injection vector there
  either. ✓

- **`src/gui/updater.py:344-372` — minor (positive, observation)**
  The `_verify_authenticode()` path is unchanged from the
  pre-PR baseline. The function is "best-effort" (returns
  True when `signtool` is missing or the file is unsigned)
  but the SHA256 check is the hard gate, not Authenticode.
  This is the right priority order for a project whose
  maintainers do not (yet) have a code-signing certificate
  configured. ✓

- **`.github/workflows/release.yml:6` — minor (hardening
  suggestion, not a bug)**
  The trigger pattern `v[0-9]+.[0-9]+.[0-9]+` uses unescaped
  `.` characters, which in regex match *any* character. A
  tag like `v4.4.3-rc1` would still match (the `-` satisfies
  the third `.`). The PowerShell guard on lines 31-39 catches
  this (the stripped tag is `4.4.3-rc1`, which does not equal
  `4.4.3`), so the build fails before the assets are
  published, but a stricter pattern would be cleaner:
  `tags: ["v[0-9]+\\.[0-9]+\\.[0-9]+"]` (anchored, escaped
  dots). This is a hygiene tweak, not a security fix — the
  defense-in-depth is the PowerShell guard.

- **`.github/workflows/release.yml:33` — minor (hardening
  suggestion, not a bug)**
  `"${{ github.ref_name }}".TrimStart('v')` strips *all*
  leading `v` characters (PowerShell's `String.TrimStart`
  treats a single-char argument as a char set). A tag
  `vv4.4.3` would be stripped to `4.4.3` and the guard
  would pass. Git ref-name syntax forbids `vv`-prefixed
  tags at push time, so this is theoretical, not a real
  bypass. Trailing whitespace is preserved by `TrimStart`
  (correct — tags cannot have trailing whitespace anyway).
  No fix needed; flagging for completeness.

- **`.github/workflows/release.yml:34` — minor (hardening
  suggestion, build-host only)**
  The guard runs `python -c "import src; ..."`, which
  executes any top-level code in `src/__init__.py` (and
  every module it transitively imports) in the CI runner.
  For a build-time guard in a maintainer-controlled repo
  this is fine — a malicious `src/__init__.py` would have
  to be merged first, and code review is the trust anchor.
  But for a hardening pass, the guard could parse the
  version out of the file with a regex (e.g.
  `Select-String -Pattern '^__version__ = "(.+)"$' src/__init__.py`)
  instead of `import`-ing it. This eliminates the
  arbitrary-code-execution surface at the cost of being
  slightly less "live" (it would not see a version set by
  a re-export from `src.backend`). Not a blocker.

- **`.github/workflows/release.yml:58` — nitpick
  (pre-existing, NOT introduced)**
  `gh release create ... --latest || true` will mark the
  new release as GitHub "latest". A maintainer who
  accidentally re-pushes `v4.3.0` (or a compromised PAT
  does) would mark the older release as "latest",
  demoting `v4.4.3`. The PowerShell guard catches the
  *intentional* case (tag does not match `src.__version__`)
  but not the *accidental* case (an old tag whose source
  happens to still be in the tree). Suggested fix (pre-
  existing concern, not introduced): drop `--latest`
  entirely; GitHub's "latest" pointer follows tag order
  by default, and the user can re-point it from the UI
  if needed.

- **`.github/workflows/release.yml:61-69` — minor (positive,
  observation)**
  The `latest.json` upload step is correct: the
  `Test-Path -LiteralPath "latest.json"` check handles
  the missing-file case, `--clobber` makes re-runs
  idempotent, and the upload is scoped to the
  run-scoped `GH_TOKEN: ${{ github.token }}`. No
  downgrade attack surface: `--clobber` overwrites the
  file with whatever the repo contains at upload time,
  it does not preserve a previous version. ✓

- **`tests/test_updater.py:464, 564` — minor (positive,
  observation)**
  The `mock.patch("sys.executable", str(fake_exe))` pattern
  is used as a context manager, which auto-restores
  `sys.executable` on exit (even if the test raises). The
  companion `sys.frozen = True` mutation is inside the same
  block in `test_sha256_equality_short_circuits_when_hashes_match`
  and is also covered by the `setUp/tearDown` save/restore
  pattern. No test leaks `sys.executable` or `sys.frozen`
  to the wider suite. The Round-2
  `IsSkippedTests` / `UpdaterCheckTests` / `UpdaterDownloadTests`
  fix is confirmed: all four test classes now use the same
  save/restore pattern, and the verification
  `sys.frozen after: NOT SET` (tester report §4) confirms
  the leak is gone. ✓

- **`tests/test_updater.py:182-189` — nitpick (pre-existing,
  NOT introduced)**
  Dead code: `resp = _Resp = type(...)` binds an unused
  class to two names. The test then uses the locally-defined
  `_BadResp` instead. Pre-existing, flagged by the reviewer
  in Round 1, and explicitly listed as not-introduced.
  Not a security issue. Leave as-is for a follow-up.

- **`latest.json:4` — minor (known design choice)**
  The `download_url` ends in `Setup_NovelTrad-v4.4.1.exe`
  (note the `4.4.1` in the asset name) because that is the
  asset currently attached to the v4.4.3 GitHub release
  (the original loop-causing bug). The `sha256` is the
  correct hash of that v4.4.1 asset. A user running the
  updater against this manifest will see a 4.4.3 "version"
  field but a 4.4.1 asset. This is the *known drift* the
  whole change is designed to flush out, not a security
  issue. The next v4.4.3 re-run (or v4.4.4 cut) will
  rebuild the asset and the maintainer will need to update
  both the URL and the SHA256 in this file. The plan calls
  this out. No fix for this PR.

- **`CHANGELOG.md:15-23` — no issues**
  The new `[Unreleased]` block is plain text. No URLs
  with tokens, no API keys, no signing-cert fingerprints,
  no internal hostnames. Safe to publish. ✓

### Strengths

- **The defense-in-depth SHA256-equality short-circuit
  (`src/gui/updater.py:250-258`) is correctly bounded.** The
  check only fires when (a) the version short-circuit has
  already passed, (b) `info.expected_sha256` is truthy (so
  either the API or the manifest supplied a digest), and
  (c) the local `sys.executable` hash *equals* the remote
  digest. The only way the new check returns `None` is when
  the user has already installed the bit-identical build
  under a different version tag — i.e. the update offer
  would be wrong *and* the file is already on disk. The
  comment block (lines 237-249) explicitly documents the
  intent and the limitation (PyInstaller bundle vs Inno
  Setup installer have different hashes), so a future
  contributor cannot "simplify" the check away by mistake.
  Excellent.

- **The asset-digest override (`src/gui/updater.py:234-236`)
  is the right precedence order.** The GitHub API's
  `assets[].digest` is more authoritative than the
  `latest.json` manifest (which is a maintainer-maintained
  file uploaded after the release), so the override is
  applied *last* in the enrichment chain. A missing
  digest correctly falls through to the manifest value
  (line 222), which in turn falls through to `None` if
  the manifest is also missing. The fallback chain is
  documented implicitly by the line ordering and is
  consistent with the comment in `_parse_asset_digest`'s
  docstring.

- **The test isolation is now airtight.** Round 2 fixed
  the `sys.frozen` leak in
  `IsSkippedTests` / `UpdaterCheckTests` /
  `UpdaterDownloadTests`, and the new
  `UpdaterAssetDigestTests` class set the correct pattern
  from the start. The `mock.patch("sys.executable", ...)`
  calls are context-managed and the
  `test_sha256_equality_short_circuits_when_hashes_match`
  test creates its own `TemporaryDirectory` for the fake
  exe, so no test pollutes `sys.executable` for the rest
  of the suite. The tester's verification
  (`sys.frozen after: NOT SET`) is a clean confirmation
  that the leak is closed.

- **The PowerShell tag-vs-source guard is a tight,
  side-effect-free check.** It runs in 5 lines, fails
  fast, and the `end=''` on `print(src.__version__)`
  suppresses the trailing newline so the string compare
  is exact. The `|| true` on `gh release create` is
  scoped to the upload step, not the guard. The guard
  itself is a hard gate.

- **`contents: write` is the minimum scope needed.**
  The workflow does not request `packages: write`,
  `id-token: write`, or any other elevated scope, so a
  compromised PAT or a malicious workflow change cannot
  publish to PyPI, sign OIDC tokens, etc. The
  `${{ github.token }}` (the default GITHUB_TOKEN) is
  scoped to the run and revoked when the job ends.
  Standard, minimal-privilege practice.

### Next Agent

`@linter` — the seven-file change list is safe to merge.
No security blockers. The four minor / nitpick items above
are appropriate for follow-up PRs (a follow-up to tighten
`_parse_asset_digest` with a hex check, and a separate
follow-up to make the manifest `download_url` subordinate
to the API's `browser_download_url`, would be the two
highest-value future cleanups).

## Lint Report

### Verdict

**Minor issues (1 finding).** The seven-file change list is
otherwise clean: `python -m compileall` is green, the JSON
parses, the YAML / Markdown are structurally valid, and the
new code matches the dominant style of each file it landed in.

The single finding is a **UTF-8 BOM at the start of
`tests/test_updater.py`** (bytes `EF BB BF`). It is not present
in the rest of the project's Python tree, so it is an
inconsistency introduced by the implementor's edit (likely
an editor that saved as "UTF-8 with BOM"). Python 3 handles
it transparently (PEP 263 + the `utf-8-sig` codec), so
`compileall` and the test suite pass — the impact is purely
hygienic. The lint check is read-only here (the workflow
denies writes outside `WORKFLOW_STATE.md`), so the fix is
listed below for the implementor to apply as a one-line edit
(re-save the file without the BOM).

No major / blocker issues. No new code changes required
beyond the BOM fix.

### What Was Checked

The project has **no configured linter**. Verified by reading:

- `pyproject.toml` (30 lines) — only `[project]` and
  `[build-system]` sections; no `[tool.ruff]`, `[tool.black]`,
  `[tool.isort]`, `[tool.mypy]`, `[tool.pylint]`, etc.
- `requirements.txt` (32 lines) — runtime deps only; no dev
  tools like `ruff`, `flake8`, `black`, `isort`, `mypy`, or
  `pylint`.
- `.github/workflows/ci.yml` (68 lines) — only runs
  `python -m compileall src` and
  `python -m unittest discover tests -v`. No linter step.

No linter is installed in this dev environment either
(`ruff`, `flake8`, `black`, `isort`, `mypy`, `pylint` all
return `ModuleNotFoundError`). No `PyYAML` is installed, so
the YAML was inspected visually rather than parsed.

Fallback checks I ran instead:

1. **`python -m compileall -q src tests`** → exit 0. All
   Python files (including `src/__init__.py`,
   `src/gui/updater.py`, `tests/test_updater.py`) parse
   cleanly. Last 3 lines of output were
   `Listing 'src\\gui\\widgets'...` and the implicit
   `*- OK` per directory.
2. **`python -c "import json; json.load(open('latest.json'))"`**
   → succeeded. Parsed payload:
   `{'version': '4.4.3', 'release_date': '2026-06-16T23:02:00Z',
   'download_url': '...Setup_NovelTrad-v4.4.1.exe',
   'sha256': '0850b35e...dbc7f5fc'}`. 2-space indentation
   confirmed. All 4 required keys present. `sha256` is 64
   lowercase hex chars.
3. **YAML visual inspection** of `.github/workflows/release.yml`:
   - Tag trigger pattern is a quoted string
     (`"v[0-9]+.[0-9]+.[0-9]+"`) — syntactically valid.
   - All `run: |` literal blocks use a consistent indent
     (10 spaces for the first script line, 12 for the
     remainder, 12 for the new `latest.json` upload block).
   - No tabs. Indentation is internally consistent.
   - PowerShell `if/else` on lines 65-68 closes correctly.
   - `${{ github.ref_name }}` interpolation is inside double
     quotes (correct for GitHub Actions YAML).
4. **Markdown heading hierarchy** of `CHANGELOG.md`:
   - `# Changelog` (line 1)
   - `## [Unreleased]` (line 13) — new section
   - `### Fixed` (line 17) — new subsection
   - No skipped levels. Sequential `# → ## → ###`.
   - All 17 dated `## [X.Y.Z]` headings are at level 2; all
     `### Added` / `### Changed` / `### Fixed` / etc. are
     at level 3.
5. **Style consistency scan** of the 3 changed Python files:
   - **Tabs**: 0 in every file.
   - **Trailing whitespace**: 0 in every file.
   - **CRLF vs LF**: all Python/TOML/YAML/Markdown files
     use CRLF. `latest.json` uses LF (existing project
     convention; verified by reading the previous version
     from `git show HEAD:latest.json`).
   - **PEP 8 blank lines**: no triple-blank-line sequences
     in any of the 3 Python files.
   - **Line length**:
     - `src/__init__.py` max 71 (well under 100)
     - `src/gui/updater.py` max 90 (well under 100)
     - `tests/test_updater.py` max **105** (one
       test-fixture string on line 411 with a fake SHA256 —
       a test payload, not application code; the long
       literal is necessary to exercise the 64-char hex
       path and there is no clean way to break it up
       without contorting the test). Everything else < 100.
     - `release.yml` max 143 (PowerShell multi-line
       commands inside YAML `run: |` blocks — YAML has no
       line-length requirement, and the PowerShell is
       correctly indented as a literal block scalar).
     - `CHANGELOG.md` max 608 (a single prose paragraph
       on line 15 plus a couple of long bullet lines on
       19 and a pre-existing one on 63; Markdown renderers
       wrap on display, so this is acceptable prose style).
   - **`Optional[X]` vs `X | None`**: spot-checked.
     - `src/gui/updater.py` is dominantly `Optional[X]`
       (PEP 484): 8 hits (lines 67, 85, 99, 128, 160,
       177, 266, 267). One pre-existing `X | None` at
       line 422 (`_find_signtool`) — already flagged by
       the reviewer in round 1. **New code
       (`_parse_asset_digest` line 99,
       `_local_exe_sha256` line 128) correctly follows
       the file's dominant `Optional[X]` style.** ✓
     - `tests/test_updater.py` is dominantly `X | None`
       (PEP 604): 10 hits across the test tree. The new
       helper signature `_make_response(payload: dict,
       raw: bytes | None = None)` (line 32) matches the
       file's style. ✓
   - **String-quote style**: spot-checked.
     - `src/gui/updater.py` uses double-quoted strings
       throughout (e.g. `API_URL = "..."`,
       `LATEST_JSON_URL = "..."`, all log format strings
       like `"updater: ..."`). The new code
       (`_parse_asset_digest`, `_local_exe_sha256`,
       `check()` SHA256 block) consistently uses double
       quotes. ✓
     - `tests/test_updater.py` uses double quotes for
       string keys and URL/path literals, single quotes
       only for f-string components and some dict keys.
       The new `UpdaterAssetDigestTests` class follows
       the same pattern. ✓

### Findings

- **`tests/test_updater.py:1` — minor (one-line fix, no
  functional impact)**
  The file starts with a **UTF-8 BOM** (bytes `EF BB BF`,
  3 bytes before the `"""` of the docstring). This was
  introduced by the implementor's edit — the `git show
  HEAD:tests/test_updater.py` version does **not** have a
  BOM. A sweep of every `*.py` in `src/` and `tests/`
  confirms that `test_updater.py` is the **only** Python
  file in the project with a BOM; the other ~70 Python
  files are BOM-free.
  - **Impact**: zero. Python 3 reads BOM-prefixed sources
    correctly (the `utf-8-sig` codec strips the BOM and
    `compileall` + the test suite both pass).
  - **Why it matters**: it's a deviation from the project's
    one-true-encoding convention. Editors that auto-add a
    BOM (Notepad, some PowerShell I/O commands, certain
    Windows-encoding defaults) will trip up tools that
    expect a BOM-free file.
  - **Suggested fix**: re-save `tests/test_updater.py`
    without the BOM. On Windows, the simplest way is:
    ```powershell
    $content = Get-Content -LiteralPath tests\test_updater.py -Raw
    [System.IO.File]::WriteAllText((Resolve-Path tests\test_updater.py), $content, (New-Object System.Text.UTF8Encoding $false))
    ```
    Or open the file in the implementor's editor and
    "Save As → UTF-8 (no BOM)".
  - **Note**: this is a one-line, low-risk fix. The
    implementor can apply it in 30 seconds; it does not
    warrant a re-review pass.

- **`src/gui/updater.py:99-125` (`_parse_asset_digest`),
  128-148 (`_local_exe_sha256`), 231-258 (asset-digest
  override + SHA256-equality check) — no issues (positive)**
  The new code matches the file's dominant style:
  - `Optional[X]` (PEP 484), not `X | None` — matches 8
    other Optional hints in the same file.
  - Double-quoted strings throughout — matches the rest
    of `updater.py`.
  - 2-blank-line separation between top-level functions
    (lines 96-98, 125-127, 148-150, 259-261) — PEP 8
    compliant.
  - All lines ≤ 90 chars.
  - The defense-in-depth comment block (lines 237-249) is
    clear, accurate, and the right length.
  - The `try/except Exception` shape is consistent with
    the existing `_fetch_json` (line 186-190) and manifest
    block (line 217-230).

- **`tests/test_updater.py:378-566` (`UpdaterAssetDigestTests`)
  — no issues (positive)**
  The new test class matches the rest of the test suite's
  style:
  - `X | None` (PEP 604) used in the new
    `_make_response` signature (line 32) — matches 10
    other PEP 604 hits in the test tree.
  - Double-quoted strings throughout the payloads.
  - 2-blank-line separation between top-level helpers
    (lines 50-52, 63-65) and between test classes
    (lines 96-98, 283-285, 376-378) — PEP 8 compliant.
  - The only line over 100 chars is line 411
    (`"digest": "sha256:DEADBEEFcafebabe0123456789abcdef0123456789abcdef0123456789abcdef",`)
    — a 105-char test fixture with a 64-char fake hex
    string. The literal cannot be wrapped without
    concatenating two strings, which would defeat the
    purpose of the test (the `_parse_asset_digest` test
    relies on the input being a single string with the
    `sha256:` prefix). Acceptable.

- **`pyproject.toml:3` — no issues (positive)**
  `version = "4.4.3"` is consistent with `src.__version__`
  in `src/__init__.py` and the `version` field in
  `latest.json`. All three sources of truth agree.

- **`latest.json:1-6` — no issues (positive)**
  Valid JSON, 2-space indent, 4 required keys
  (`version`, `release_date`, `download_url`, `sha256`).
  `sha256` is 64 lowercase hex chars. The asset name
  `Setup_NovelTrad-v4.4.1.exe` in the `download_url` is
  the documented known-mismatch (the v4.4.3 GitHub
  release currently ships a 4.4.1 asset); this is
  intentional and matches the plan.

- **`.github/workflows/release.yml:6, 31-39, 61-69` —
  no issues (positive)**
  - Line 6 tag trigger is a valid quoted-string regex.
  - PowerShell guard (lines 31-39) uses the correct
    literal block scalar syntax; all lines inside the
    `run: |` block are indented at 10/12 spaces
    consistently. The `if/else` is well-formed.
  - `latest.json` upload (lines 61-69) uses a clean
    `if (Test-Path ...) { ... } else { ... }` pattern
    and `--clobber` for idempotency. Matches the
    pre-existing `gh release upload` step at line 59.
  - The long lines (max 143) are inside the `run: |`
    blocks; YAML has no line-length requirement and
    PowerShell script bodies benefit from staying on
    one line per statement.

- **`CHANGELOG.md:13-23` — no issues (positive)**
  - New `## [Unreleased]` heading at line 13 is at the
    right level (level 2).
  - The single `### Fixed` subheading at line 17 is at
    the right level (level 3).
  - No skipped heading levels. The heading hierarchy
    `# → ## → ###` is consistent with the rest of the
    file.
  - The long prose line (608 chars) is a single
    paragraph; Markdown renderers wrap on display, and
    there is no clean way to break it up without
    splitting the explanation of the version-drift
    story.

### Strengths

- **The new code is highly consistent with the existing
  codebase.** The two new helpers in `updater.py` use
  `Optional[X]` (matches 8 of 9 Optional hints in the
  file) and double-quoted strings (matches the file's
  convention). The new test class in `test_updater.py`
  uses `X | None` (matches the rest of the test tree's
  PEP 604 convention). No new style was introduced.

- **The linter-relevant `compileall` is the only check
  CI runs, and it is green.** 166 + 8 = 174 tests pass,
  as already documented by the tester's report.

### Next Agent

`@implementor` — please apply the **one** item below
before merge:

1. **minor** — `tests/test_updater.py`: re-save without
   the UTF-8 BOM. The file is the only Python file in the
   project with a BOM (confirmed by sweeping every
   `src/**/*.py` and `tests/**/*.py`); the previous
   `git show HEAD:tests/test_updater.py` version was
   BOM-free. The implementor's editor most likely saved
   as "UTF-8 with BOM" instead of plain UTF-8. This is a
   one-line fix, no functional impact (Python 3 handles
   the BOM transparently), and the test suite already
   passes — it's purely a consistency-with-the-rest-of-
   the-codebase cleanup. Suggested command (PowerShell):
   ```powershell
   $p = Resolve-Path tests\test_updater.py
   $c = Get-Content -LiteralPath $p.Path -Raw
   [System.IO.File]::WriteAllText($p.Path, $c, (New-Object System.Text.UTF8Encoding $false))
   ```

After that fix, hand off to `@commit-message`. No other
linting changes are required.

## Commit Message

### Proposed Commit Message (single commit, recommended)

```
fix: stop updater "v4.4.3 available" loop

The published v4.4.3 GitHub release shipped a 4.4.1 installer
(Setup_NovelTrad-v4.4.1.exe) because src.__version__ was never
bumped for v4.4.2 and v4.4.3. Installing the v4.4.3 asset left
the app reporting 4.4.1, so the updater kept offering "v4.4.3 is
available" forever.

The primary loop-breaker is the source bump itself: once
src.__version__ matches the published tag, the existing
`remote_v <= local_v` short-circuit in Updater.check() returns
None and no update is offered.

The new SHA256-equality check in Updater.check() is
defense-in-depth, not the primary fix: if the remote installer's
SHA256 matches the local sys.executable, the updater skips the
offer. In the current Inno-Setup installer workflow the two
hashes usually differ, so this guards against a future re-tag
regression rather than breaking today's loop.

The release workflow now:
  * triggers only on stable semver tags
    (v[0-9]+.[0-9]+.[0-9]+), filtering prerelease tags like
    v4.4.4-rc1;
  * fails the build if github.ref_name does not match
    src.__version__ via a PowerShell guard between checkout and
    build;
  * uploads the repo-root latest.json as a release asset so
    the updater's manifest enrichment is no longer dead code.

Files:
  - src/__init__.py, pyproject.toml, latest.json: sync to 4.4.3.
  - src/gui/updater.py: _parse_asset_digest(), _local_exe_sha256(),
    asset-digest override, and SHA256-equality short-circuit.
  - tests/test_updater.py: 8 new UpdaterAssetDigestTests cases,
    sys.frozen save/restore in IsSkippedTests / UpdaterCheckTests
    / UpdaterDownloadTests, UTF-8 BOM removed.
  - .github/workflows/release.yml: tighter trigger, PowerShell
    tag-vs-source guard, latest.json upload step.
  - CHANGELOG.md: [Unreleased] block with Fixed bullets.
```

### Subject / Style Justification

The subject (`fix: stop updater "v4.4.3 available" loop`, 43 chars)
uses the project's dominant `fix:` prefix (8 of the last 20 commits
start with `fix:`) and quotes the exact GUI dialog the user is
seeing, so the change is greppable in `git log` from the symptom
alone. The plain `fix:` (not `fix(updater):`) is correct because
the change spans five concerns: source bump, manifest, updater
hardening, CI guard, and changelog — a scope suffix would be
misleading. The body is wrapped at ≤ 100 chars, opens with the
symptom (the user's actual complaint), then explains the primary
fix before the defense-in-depth check (so a future reader does
not mistakenly "simplify" the SHA256 check away thinking it is the
loop-breaker), and finally enumerates the workflow changes and
files.

### Alternative Split (if maintainer prefers focused commits)

If the project prefers one-concern-per-commit, the seven files
split naturally into three commits, each independently
revertable:

**Commit 1 — `fix: sync source version to 4.4.3`**
- `src/__init__.py`
- `pyproject.toml`
- `latest.json`
- `CHANGELOG.md`

The actual loop-breaker. After this commit lands and a v4.4.3
release is rebuilt, the GUI updater stops looping. The other
two commits are hardening.

**Commit 2 — `feat(updater): harden check() with SHA256-equality guard`**
- `src/gui/updater.py` (`_parse_asset_digest`, `_local_exe_sha256`,
  asset-digest override, SHA256-equality short-circuit,
  defense-in-depth comment block)
- `tests/test_updater.py` (8 new `UpdaterAssetDigestTests` cases +
  `sys.frozen` save/restore fix in `IsSkippedTests` /
  `UpdaterCheckTests` / `UpdaterDownloadTests` + UTF-8 BOM
  removal)

Adds the secondary guard, plus the regression tests that lock
in both the primary fix (`test_version_short_circuit_locks_in_bump`)
and the new behavior (`test_sha256_equality_short_circuits_when_hashes_match`).

**Commit 3 — `ci: tighten release workflow with tag guard + manifest upload`**
- `.github/workflows/release.yml` (prerelease tag filter +
  PowerShell tag-vs-source guard + `latest.json` upload step)

Prevents the same drift from happening again. The PowerShell
guard fails the build before the asset is uploaded; the
prerelease filter prevents `v4.4.4-rc1` from triggering a real
release.

### Recommendation

**Single commit.** The recent `git log --oneline -20` shows the
project consistently bundles related multi-file fixes into one
commit (`c0c0563 fix: add llm_refined to state_store schema and
allowlist` touched 4 files; `b295a40 bump version to 4.4.1`
touched 1; etc.). The three-way split is clean in theory but
re-introduces the original problem in the middle window
(Commit 1 lands, Commits 2 and 3 are not yet pushed, a v4.4.3
rebuild re-triggers the loop). Bundling keeps the fix atomic.

## Follow-up: NovelTrad 2.0 SDD VitePress Site Fixed

After the SDD repo was published, the live site at
`https://balrog57.github.io/NovelTrad-Documentation/` rendered without
VitePress styling and asset URLs returned 404. Root cause: GitHub Pages
was still configured with `build_type: legacy` and `source: {branch: main, path: /}`,
so it served the raw repo root instead of the `actions/upload-pages-artifact`
artifact produced by the deploy workflow.

### Fix applied

- Changed the Pages source to `github_actions` via the GitHub REST API:
  ```
  PUT /repos/Balrog57/NovelTrad-Documentation/pages
  {"build_type":"workflow","source":{"branch":"main","path":"/"}}
  ```
- Pushed an empty commit to trigger a fresh deploy workflow run.
- Verified the new run (`28407051537`) built and deployed successfully.

### Result

- `build_type` is now `workflow`.
- The live site renders with the VitePress theme, sidebar, and navigation.
- All volume links (`/volumes/00-Vision.html`, etc.) and static assets are
  served correctly from the `/NovelTrad-Documentation/` base path.

No `noveltrad` source files were changed for this fix; the SDD lives in the
dedicated `NovelTrad-Documentation` repository.

## Next Agent

**Done** — workflow complete.
