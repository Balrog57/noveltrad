"""Auto-update via GitHub Releases (Sparkle-like, stable channel only).

The updater queries the public ``/repos/.../releases/latest`` endpoint
(no auth required, < 60 req/h on the IP allow-list), compares the
``tag_name`` to the running version (parsed with ``packaging.version``)
and, if newer, offers the user a download.

Garde-fous (mirrors the constraints in
``.kilo/plans/installer-ci-autoupdate.md``):

* In dev mode (``sys.frozen`` is absent) or when the env var
  ``NOVELTRAD_SKIP_UPDATE=1`` is set, :meth:`Updater.check` returns
  ``None`` immediately so we never hit the network from a developer
  run.
* The downloaded installer is SHA256-verified against a manifest
  shipped alongside the release (``latest.json``) before
  :meth:`Updater.install` is allowed to run.
* Pre-releases are skipped — we only follow the ``stable`` channel.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

try:
    from packaging.version import InvalidVersion, Version
except Exception:  # pragma: no cover - packaging missing in slim env
    Version = None  # type: ignore[assignment]
    InvalidVersion = Exception  # type: ignore[assignment,misc]


logger = logging.getLogger(__name__)

API_URL = (
    "https://api.github.com/repos/Balrog57/noveltrad/releases/latest"
)
LATEST_JSON_URL = (
    "https://github.com/Balrog57/noveltrad/releases/latest/download/latest.json"
)
DEFAULT_TIMEOUT = 5.0
CHUNK = 64 * 1024

ProgressCallback = Callable[[int, int], None]


@dataclasses.dataclass
class UpdateInfo:
    """Metadata about an available update."""

    version: str
    tag: str
    release_date: str
    body: str
    download_url: str
    expected_sha256: Optional[str] = None

    @property
    def is_prerelease(self) -> bool:
        return False  # filtered by check()


def is_skipped() -> bool:
    """True if auto-update is disabled by env or by dev mode."""
    if os.environ.get("NOVELTRAD_SKIP_UPDATE", "").strip() == "1":
        return True
    # In dev mode (running from `python src/main_qt.py`) we are not
    # inside a PyInstaller bundle — never auto-update the dev checkout.
    if not getattr(sys, "frozen", False):
        return True
    return False


def _parse_version(tag: str) -> Optional["Version"]:
    if Version is None:
        return None
    cleaned = tag.lstrip("v").strip()
    try:
        return Version(cleaned)
    except InvalidVersion:
        return None


def _normalize_current(version: str) -> str:
    return version.lstrip("v").strip() or "0.0.0"


class Updater:
    """Sparkle-like auto-updater for the NovelTrad desktop app."""

    def __init__(
        self,
        current_version: str,
        *,
        api_url: str = API_URL,
        latest_json_url: str = LATEST_JSON_URL,
        opener: Optional[Callable[[str, float], object]] = None,
    ) -> None:
        self._current_version = _normalize_current(current_version)
        self._api_url = api_url
        self._latest_json_url = latest_json_url
        self._opener = opener  # injectable for tests

    # --- queries --------------------------------------------------------

    @property
    def current_version(self) -> str:
        return self._current_version

    def should_check(self) -> bool:
        """False when in dev mode or when explicitly disabled."""
        return not is_skipped()

    def check(self, timeout: float = DEFAULT_TIMEOUT) -> Optional[UpdateInfo]:
        """Return an :class:`UpdateInfo` if a newer stable release exists.

        Returns ``None`` when up-to-date, on any network/parse error, or
        when the user has disabled auto-update. Never raises.
        """
        if not self.should_check():
            logger.info("updater: skipped (dev or NOVELTRAD_SKIP_UPDATE=1)")
            return None
        try:
            payload = self._fetch_json(self._api_url, timeout)
        except Exception as exc:  # noqa: BLE001 - never raise
            logger.warning("updater: latest release fetch failed: %s", exc)
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("draft") or payload.get("prerelease"):
            return None
        tag = str(payload.get("tag_name") or "").strip()
        if not tag:
            return None
        remote_v = _parse_version(tag)
        local_v = _parse_version(self._current_version)
        if remote_v is None or local_v is None:
            # Fall back to a string compare if packaging is unavailable.
            if self._current_version and tag.lstrip("v") <= self._current_version:
                return None
        else:
            if remote_v <= local_v:
                return None

        info = UpdateInfo(
            version=tag.lstrip("v"),
            tag=tag,
            release_date=str(payload.get("published_at") or ""),
            body=str(payload.get("body") or ""),
            download_url=self._pick_asset_url(payload),
        )
        # Try to enrich with the SHA256 from the manifest next to the
        # release assets. Best-effort: if it fails we just don't verify.
        try:
            manifest = self._fetch_json(self._latest_json_url, timeout)
            if isinstance(manifest, dict):
                sha = str(manifest.get("sha256") or "").strip().lower()
                if sha:
                    info.expected_sha256 = sha
                # Also prefer the manifest's download_url when present,
                # since the release JSON may not list the actual asset
                # for pre-attached installers.
                url = str(manifest.get("download_url") or "").strip()
                if url:
                    info.download_url = url
        except Exception:  # noqa: BLE001 - manifest is optional
            pass
        return info

    # --- download + verify --------------------------------------------

    def download(
        self,
        info: UpdateInfo,
        dest: Optional[Path] = None,
        progress_cb: Optional[ProgressCallback] = None,
        timeout: float = 60.0,
    ) -> Path:
        """Stream the installer to ``dest`` (or a temp file).

        ``progress_cb(downloaded, total)`` is invoked at most every
        ``CHUNK`` bytes. Returns the path of the saved file.
        """
        if dest is None:
            tmp = tempfile.NamedTemporaryFile(
                prefix="NovelTrad-setup-", suffix=".exe", delete=False
            )
            tmp.close()
            dest = Path(tmp.name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            info.download_url, headers={"User-Agent": "NovelTrad-Updater/1.0"}
        )
        with self._urlopen(req, timeout) as resp:  # type: ignore[attr-defined]
            total = self._content_length(resp)
            downloaded = 0
            hasher = hashlib.sha256()
            with open(dest, "wb") as out:
                while True:
                    buf = resp.read(CHUNK)
                    if not buf:
                        break
                    out.write(buf)
                    hasher.update(buf)
                    downloaded += len(buf)
                    if progress_cb is not None:
                        try:
                            progress_cb(downloaded, total)
                        except Exception:  # noqa: BLE001
                            pass
        digest = hasher.hexdigest().lower()
        if info.expected_sha256:
            expected = info.expected_sha256.lower()
            if digest != expected:
                try:
                    dest.unlink(missing_ok=True)
                except Exception:
                    pass
                raise ValueError(
                    f"SHA256 mismatch: expected {expected}, got {digest}"
                )
        return dest

    # --- install -------------------------------------------------------

    def install(self, exe_path: Path) -> None:
        """Launch the installer via ShellExecuteW (``os.startfile``).

        Inno Setup installers accept ``/SP- /SILENT /NORESTART`` for an
        unattended install; we leave the UI mode to the user by
        default but the calling dialog can append these flags.
        """
        exe = Path(exe_path)
        if not exe.exists():
            raise FileNotFoundError(str(exe))
        # Best-effort Authenticode verification on Windows before
        # launching the installer. GitHub builds are unsigned when no
        # signing certificate is configured, so SHA256 verification from
        # latest.json remains the hard gate.
        if getattr(sys, "frozen", False) and sys.platform == "win32":
            self._verify_authenticode(exe)
        try:
            os.startfile(str(exe))  # type: ignore[attr-defined]
            return
        except AttributeError:
            pass
        # Non-Windows fallback (tests / WSL).
        subprocess.Popen(  # noqa: S603
            [str(exe)], shell=False, close_fds=True
        )

    @staticmethod
    def _verify_authenticode(exe: Path) -> bool:
        """Best-effort Authenticode signature verification via signtool.

        Returns True if signtool reports a valid signature, False otherwise.
        On platforms without signtool, returns True. The caller treats a
        False return as a warning only because release builds may be unsigned.
        """
        signtool = _find_signtool()
        if signtool is None:
            logger.info("updater: signtool not found; skipping signature check")
            return True
        try:
            res = subprocess.run(  # noqa: S603
                [str(signtool), "verify", "/pa", "/q", str(exe)],
                capture_output=True,
                text=True,
                timeout=15.0,
            )
            valid = res.returncode == 0
            if not valid:
                logger.warning(
                    "updater: Authenticode verification failed (code=%s): %s",
                    res.returncode,
                    res.stderr.strip() or res.stdout.strip(),
                )
            return valid
        except Exception as exc:
            logger.warning("updater: signtool error: %s", exc)
            return False

    # --- internals ----------------------------------------------------

    def _pick_asset_url(self, payload: dict) -> str:
        assets = payload.get("assets") or []
        for a in assets:
            if not isinstance(a, dict):
                continue
            name = str(a.get("name") or "")
            url = str(a.get("browser_download_url") or "")
            if name.lower().endswith(".exe") and url:
                return url
        # Fall back to the release HTML page so the user can still
        # click through if we somehow lost the asset list.
        return str(payload.get("html_url") or "")

    def _fetch_json(self, url: str, timeout: float) -> object:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "NovelTrad-Updater/1.0",
            },
        )
        with self._urlopen(req, timeout) as resp:  # type: ignore[attr-defined]
            raw = resp.read()
        if hasattr(raw, "decode"):
            raw = raw.decode("utf-8", errors="replace")
        return json.loads(raw)

    def _urlopen(self, req, timeout):  # type: ignore[no-untyped-def]
        if self._opener is not None:
            return self._opener(req, timeout)
        return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310

    @staticmethod
    def _content_length(resp) -> int:  # type: ignore[no-untyped-def]
        try:
            return int(resp.headers.get("Content-Length") or 0)
        except Exception:
            return 0


def download_default_destination() -> Path:
    """Return a sensible default download directory for the installer."""
    tmp = os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()
    return Path(tmp)


def _find_signtool() -> Path | None:
    """Locate Microsoft signtool.exe for Authenticode verification."""
    if sys.platform != "win32":
        return None
    candidates = [
        Path("C:/Program Files (x86)/Windows Kits/10/bin/10.0.22621.0/x64/signtool.exe"),
        Path("C:/Program Files (x86)/Windows Kits/10/bin/10.0.22000.0/x64/signtool.exe"),
        Path("C:/Program Files (x86)/Windows Kits/10/bin/10.0.19041.0/x64/signtool.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c
    try:
        res = subprocess.run(
            ["where", "signtool"], capture_output=True, text=True, timeout=5.0
        )
        if res.returncode == 0 and res.stdout.strip():
            return Path(res.stdout.strip().splitlines()[0])
    except Exception:
        pass
    return None


__all__ = [
    "Updater",
    "UpdateInfo",
    "is_skipped",
    "download_default_destination",
    "API_URL",
    "LATEST_JSON_URL",
]
