# Releasing NovelTrad v4

This document describes how to cut a new release of NovelTrad. The
pipeline is fully automated through GitHub Actions once you push a
tag of the form `vX.Y.Z`.

## 1. Version bump

Two files carry the version, and they must stay in sync:

- `src/__init__.py` → `__version__ = "X.Y.Z"`
- `pyproject.toml` → `[project] version = "X.Y.Z"`

The build script reads `src.__version__` and injects it into the
Inno Setup installer (`AppVersion`, output filename), the wheel, and
the `VERSION` file inside the PyInstaller bundle. The auto-updater
parses the same string with `packaging.version`, so a non-numeric
or pre-release tag will simply not be reported as an update.

## 2. Smoke-test the build locally (optional but recommended)

```powershell
python -m compileall src
python -m unittest discover -s tests -p "test_*.py"
python build.py --wheel
python build.py --exe
python build.py --installer
```

The installer lands at `dist/Setup_NovelTrad-vX.Y.Z.exe` and can be
smoke-tested on the dev machine: install, launch, confirm the
`Settings > Check for updates` button does not propose any update
(because we are already at the latest stable).

## 3. Commit and tag

```powershell
git add pyproject.toml src/__init__.py
git commit -m "chore(release): vX.Y.Z"
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

The `release.yml` workflow is filtered on `v[0-9]+.[0-9]+.[0-9]+`
tags, so pre-release tags like `v4.0.0-rc1` will not trigger a
release build (they are ignored on purpose; use branches for that).

## 4. What the CI does

1. Compiles `src/` and runs the unit test suite.
2. Installs Inno Setup 6 into `C:\Inno Setup 6`.
3. Runs `python build.py --all` to produce sdist + wheel + PyInstaller
   bundle + installer.
4. Computes the SHA256 of `Setup_NovelTrad-vX.Y.Z.exe`.
5. Writes a `latest.json` next to the installer:
   ```json
   {
     "version": "4.1.0",
     "release_date": "2026-06-10T00:00:00Z",
     "download_url": "https://github.com/Balrog57/noveltrad/releases/download/v4.1.0/Setup_NovelTrad-v4.1.0.exe",
     "sha256": "<hex>"
   }
   ```
6. Uploads the installer and `latest.json` as workflow artifacts
   (kept even if the release step fails, for debugging).
7. Creates a **draft** GitHub release tagged `vX.Y.Z` with the
   installer and `latest.json` attached, plus auto-generated release
   notes. Review the notes, edit if needed, then publish.

The draft flag is intentional: the release stays private until a
human double-checks the artefact and notes.

## 5. After publishing

When the release goes live, the auto-updater in any vX.Y.Z build that
runs on a Windows user's machine will:

1. Hit `https://api.github.com/repos/Balrog57/noveltrad/releases/latest`
   three seconds after startup.
2. Compare `tag_name` to its own version.
3. Pop the `UpdateDialog` with the release notes and a "Update now"
   button.
4. Stream the installer from `latest.json` `download_url`.
5. Verify the SHA256 against `latest.json` `sha256`.
6. Launch the installer via `ShellExecuteW` (Windows `os.startfile`).

To verify the end-to-end flow on a dev machine without publishing a
real release, you can run an older local build, then hand-edit the
`NOVELTRAD_VERSION` of a freshly-built installer and confirm the
network call returns the expected JSON from
`api.github.com/repos/Balrog57/noveltrad/releases/latest`.

## 6. Hotfix / patch release

For a hotfix:

1. Branch off `main`.
2. Fix the bug, add a regression test, run the local test suite.
3. Bump the patch version (`X.Y.Z → X.Y.Z+1`).
4. Open a PR, merge, then `git tag vX.Y.Z+1 && git push --tags`.

## 7. Yanking a release

GitHub releases can be marked as "draft" or "pre-release" but cannot
be truly deleted. If a release is broken:

1. Re-upload the corrected installer to the same tag.
2. Or push a new patch version (`vX.Y.Z+1`) that supersedes it.

The auto-updater will simply point users to the new tag.

## 8. UI translations (i18n)

The desktop client is translatable via Qt Linguist. Source strings
live in code wrapped in `self.tr(...)` (English is the source
language). Translated catalogues live under `src/gui/i18n/` as
`.ts` files; the runtime loads compiled `.qm` files placed next to
them. If the `.qm` is missing, the app gracefully falls back to
English.

### Compiling the catalogues

`PyQt6` does not bundle the `lrelease` binary on Windows. Two
options:

1. **Qt Tools (recommended)**: install Qt 6 via the official online
   installer and add `lrelease.exe` to the PATH, then:
   ```powershell
   lrelease src/gui/i18n/noveltrad_fr.ts -qm src/gui/i18n/noveltrad_fr.qm
   ```
2. **PyQt6 dev tools (Linux/macOS)**: `pip install pyqt6-tools` and
   invoke `pylrelease`:
   ```bash
   pylrelease src/gui/i18n/*.ts
   ```

Add a new language:

1. Copy `src/gui/i18n/noveltrad_fr.ts` to `noveltrad_<code>.ts`.
2. Translate the `<translation>` blocks.
3. Compile to `.qm` and ship next to the `.ts`.
4. Register the new code in `src/gui/i18n/__init__.py`
   (`AVAILABLE_LANGUAGES`).

The Settings tab language combobox is auto-populated from
`AVAILABLE_LANGUAGES`; no other code changes are required.
