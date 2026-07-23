"""Auto-update logic (pure, no Qt) — checks GitHub Releases and swaps the exe.

Design (Windows best-practice for a locked running exe):
  1. fetch_latest_release() queries api.github.com .../releases/latest.
  2. download_asset() streams the Windows zip to a staging dir.
  3. extract_zip() unpacks it.
  4. perform_replace_and_relaunch() writes an updater.bat that waits for this
     process to exit, xcopy the new files over the install dir, relaunch the
     exe, and self-delete.

The Qt layer (update_dialog.py / tray.py) drives these helpers; everything
here is independently testable by mocking requests.

Channel: single 'latest' (compares runtime version to the latest release tag).
Dev mode (non-frozen): is_packaged() is False -> caller should skip the check.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests
from packaging.version import InvalidVersion, Version

from src import __version__

# GitHub repo identity (single source of truth).
OWNER = "Balrog57"
REPO = "noveltrad"
API_LATEST = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
REQUEST_TIMEOUT = 10  # seconds


class UpdateError(RuntimeError):
    """Network / parsing / asset error during an update check."""


@dataclass
class LatestRelease:
    """Parsed view of the GitHub 'latest' release."""

    tag: str  # e.g. "v1.1.0"
    version: str  # e.g. "1.1.0" (stripped)
    asset_url: str  # browser_download_url of the Windows asset
    asset_name: str
    notes: str  # release body (markdown)


def is_packaged() -> bool:
    """True when running from a PyInstaller bundle (sys.frozen set)."""
    return getattr(sys, "frozen", False)


def get_current_version() -> str:
    """The version of the running app (importlib.metadata)."""
    return __version__


def _strip_v(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def is_newer(remote_version: str, current_version: str) -> bool:
    """True if remote_version is strictly greater than current_version.

    Tolerates a leading 'v'. Falls back to lexicographic compare if a value is
    not PEP 440-compliant (never raises for a malformed tag).
    """
    rv = _strip_v(remote_version)
    cv = _strip_v(current_version)
    try:
        return Version(rv) > Version(cv)
    except InvalidVersion:
        return rv > cv


def select_windows_asset(assets: list[dict]) -> dict | None:
    """Pick the Windows x64 .zip asset from a release's asset list.

    Heuristic: name contains 'windows' (case-insensitive), ends with '.zip',
    preferring one that also mentions 'x64'. Returns None if no match.
    """
    candidates = [
        a for a in assets
        if str(a.get("name", "")).lower().endswith(".zip")
        and "windows" in str(a.get("name", "")).lower()
    ]
    if not candidates:
        return None
    # Prefer x64-among-the-windows ones.
    for a in candidates:
        if "x64" in str(a.get("name", "")).lower():
            return a
    return candidates[0]


def fetch_latest_release() -> LatestRelease:
    """Query GitHub for the latest release; raise UpdateError on failure."""
    headers = {"Accept": "application/vnd.github+json"}
    try:
        resp = requests.get(API_LATEST, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise UpdateError(f"Réseau inaccessible : {exc}") from exc
    if resp.status_code == 404:
        raise UpdateError("Aucune release publiée pour l'instant.")
    if resp.status_code != 200:
        raise UpdateError(f"GitHub API HTTP {resp.status_code}")

    data = resp.json()
    tag = str(data.get("tag_name", "")).strip()
    if not tag:
        raise UpdateError("Réponse GitHub sans tag_name.")

    asset = select_windows_asset(data.get("assets") or [])
    if asset is None:
        raise UpdateError("Aucun asset Windows .zip trouvé dans la release latest.")

    return LatestRelease(
        tag=tag,
        version=_strip_v(tag),
        asset_url=asset["browser_download_url"],
        asset_name=asset["name"],
        notes=str(data.get("body") or ""),
    )


def download_asset(url: str, dest: Path, progress_cb=None) -> Path:
    """Stream-download a release asset to dest; call progress_cb(done, total)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
                        if progress_cb is not None:
                            progress_cb(done, total)
    except requests.RequestException as exc:
        raise UpdateError(f"Échec du téléchargement : {exc}") from exc
    return dest


def extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Extract a zip; dest_dir will contain the new AgentTranslate/ tree.

    Returns the path to the extracted top-level directory (the new install).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    # The zip was made with base dir 'AgentTranslate'; locate it.
    for child in dest_dir.iterdir():
        if child.is_dir() and "agenttranslate" in child.name.lower():
            return child
    # Fallback: if the zip had no top folder, the content is directly in dest_dir.
    return dest_dir


def _build_updater_bat(install_dir: Path, new_dir: Path, exe_name: str) -> str:
    """Generate the Windows batch updater script content."""
    install = str(install_dir)
    new = str(new_dir)
    return f"""\
@echo off
setlocal
set "INSTALL={install}"
set "NEW={new}"
set "EXE={exe_name}"
:wait
tasklist /FI "IMAGENAME eq %EXE%" 2>NUL | find /I "%EXE%" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >NUL
    goto wait
)
xcopy "%NEW%\\*" "%INSTALL%\\" /E /Y /I >NUL
start "" "%INSTALL%\\%EXE%"
(del "%~f0" 2>NUL) & exit
"""


def perform_replace_and_relaunch(new_dir: Path, install_dir: Path | None = None) -> Path:
    """Write the updater.bat to TEMP and launch it detached (Windows only).

    The caller should then quit the app (QApplication.quit()). Returns the bat path.
    install_dir defaults to the directory of the running exe (sys.executable).
    """
    if os.name != "nt":
        raise UpdateError("Le remplacement automatique est supporté sous Windows uniquement.")
    exe_path = Path(sys.executable)
    install_dir = install_dir or exe_path.parent
    exe_name = exe_path.name  # e.g. AgentTranslate.exe
    bat_path = Path(tempfile.gettempdir()) / "noveltrad_updater.bat"
    bat_path.write_text(_build_updater_bat(install_dir, new_dir, exe_name), encoding="utf-8")
    # Detached launch via cmd; DETACHED_PROCESS = 0x00000008.
    subprocess.Popen(
        ["cmd", "/c", str(bat_path)],
        creationflags=0x00000008,
        close_fds=True,
    )
    return bat_path
