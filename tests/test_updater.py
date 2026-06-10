"""Unit tests for the GitHub Releases auto-updater.

The updater never imports PyQt6 â€” it lives in ``src.gui`` for project
layout reasons but is pure-Python â€” so we can exercise it under
``unittest`` without spinning up Qt. We mock ``urllib.request.urlopen``
through the ``opener`` injection point on :class:`Updater` so the
network is never touched.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Ensure dev mode is "off" for the network-touching tests; we still
# want the guard logic to be observable, so we do not change sys.frozen.
from src.gui import updater as updater_mod
from src.gui.updater import Updater, UpdateInfo, is_skipped


def _make_response(payload: dict, raw: bytes | None = None):
    """Build a minimal urllib-like response object for the mocked opener."""

    class _Resp:
        def __init__(self, data: bytes):
            self._buf = io.BytesIO(data)
            self.headers = {"Content-Length": str(len(data))}

        def read(self, n: int = -1) -> bytes:
            return self._buf.read(n)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self._buf.close()
            return False

    body = raw if raw is not None else json.dumps(payload).encode("utf-8")
    return _Resp(body)


def _fake_opener(responses: dict[str, "_Resp"]):
    """Return an opener that dispatches by URL."""

    def _open(req, timeout=None):  # type: ignore[no-untyped-def]
        url = req if isinstance(req, str) else req.full_url
        if url not in responses:
            raise AssertionError(f"unexpected URL: {url}")
        return responses[url]

    return _open


class IsSkippedTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = os.environ.get("NOVELTRAD_SKIP_UPDATE")
        self._frozen_was = getattr(sys, "frozen", None)
        os.environ.pop("NOVELTRAD_SKIP_UPDATE", None)

    def tearDown(self) -> None:
        if self._env is not None:
            os.environ["NOVELTRAD_SKIP_UPDATE"] = self._env
        if self._frozen_was is not None:
            sys.frozen = self._frozen_was

    def test_skipped_in_dev_mode(self) -> None:
        # Default Python interpreter has no `sys.frozen` -> dev mode.
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")
        self.assertTrue(is_skipped())

    def test_skipped_when_env_var_set(self) -> None:
        sys.frozen = True  # pretend we're bundled
        os.environ["NOVELTRAD_SKIP_UPDATE"] = "1"
        self.assertTrue(is_skipped())

    def test_not_skipped_in_frozen_build(self) -> None:
        sys.frozen = True
        os.environ.pop("NOVELTRAD_SKIP_UPDATE", None)
        self.assertFalse(is_skipped())


class UpdaterCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        sys.frozen = True
        os.environ["NOVELTRAD_SKIP_UPDATE"] = "0"
        # Make sure dev-mode is off for the check tests.
        self._patch = mock.patch.object(updater_mod, "is_skipped", return_value=False)
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        if hasattr(sys, "frozen") and sys.frozen is True and not isinstance(
            getattr(sys, "frozen_test_keep", False), bool
        ):
            pass

    def test_newer_version_returns_update_info(self) -> None:
        payload = {
            "tag_name": "v4.1.0",
            "published_at": "2026-06-10T00:00:00Z",
            "body": "Bug fixes and shiny things.",
            "html_url": "https://github.com/Balrog57/noveltrad/releases/tag/v4.1.0",
            "prerelease": False,
            "draft": False,
            "assets": [
                {
                    "name": "Setup_NovelTrad-v4.1.0.exe",
                    "browser_download_url": "https://example.com/setup.exe",
                }
            ],
        }
        opener = _fake_opener({updater_mod.API_URL: _make_response(payload)})
        u = Updater(current_version="4.0.0", opener=opener)
        info = u.check()
        self.assertIsInstance(info, UpdateInfo)
        self.assertEqual(info.version, "4.1.0")
        self.assertEqual(info.tag, "v4.1.0")
        self.assertEqual(info.download_url, "https://example.com/setup.exe")
        self.assertIn("Bug fixes", info.body)

    def test_same_version_returns_none(self) -> None:
        payload = {
            "tag_name": "v4.0.0",
            "published_at": "2026-01-01T00:00:00Z",
            "body": "",
            "html_url": "",
            "prerelease": False,
            "draft": False,
            "assets": [],
        }
        opener = _fake_opener({updater_mod.API_URL: _make_response(payload)})
        u = Updater(current_version="4.0.0", opener=opener)
        self.assertIsNone(u.check())

    def test_older_version_returns_none(self) -> None:
        payload = {
            "tag_name": "v3.9.0",
            "published_at": "2025-12-01T00:00:00Z",
            "body": "",
            "html_url": "",
            "prerelease": False,
            "draft": False,
            "assets": [],
        }
        opener = _fake_opener({updater_mod.API_URL: _make_response(payload)})
        u = Updater(current_version="4.0.0", opener=opener)
        self.assertIsNone(u.check())

    def test_prerelease_is_ignored(self) -> None:
        payload = {
            "tag_name": "v4.1.0-rc1",
            "published_at": "2026-06-01T00:00:00Z",
            "body": "",
            "html_url": "",
            "prerelease": True,
            "draft": False,
            "assets": [],
        }
        opener = _fake_opener({updater_mod.API_URL: _make_response(payload)})
        u = Updater(current_version="4.0.0", opener=opener)
        self.assertIsNone(u.check())

    def test_malformed_json_returns_none(self) -> None:
        resp = _Resp = type(
            "_R",
            (),
            {
                "headers": {"Content-Length": "5"},
                "_buf": io.BytesIO(b"not js"),
            },
        )

        class _BadResp:
            headers = {"Content-Length": "5"}

            def read(self, n: int = -1) -> bytes:
                return b"not json"

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        opener = _fake_opener({updater_mod.API_URL: _BadResp()})
        u = Updater(current_version="4.0.0", opener=opener)
        self.assertIsNone(u.check())

    def test_network_error_returns_none(self) -> None:
        def _boom(req, timeout=None):
            raise ConnectionError("no internet")

        u = Updater(current_version="4.0.0", opener=_boom)
        self.assertIsNone(u.check())

    def test_manifest_enriches_sha256(self) -> None:
        release = {
            "tag_name": "v4.1.0",
            "published_at": "2026-06-10T00:00:00Z",
            "body": "",
            "html_url": "",
            "prerelease": False,
            "draft": False,
            "assets": [
                {
                    "name": "Setup_NovelTrad-v4.1.0.exe",
                    "browser_download_url": "https://example.com/wrong.exe",
                }
            ],
        }
        manifest = {
            "version": "4.1.0",
            "release_date": "2026-06-10T00:00:00Z",
            "download_url": "https://example.com/correct.exe",
            "sha256": "deadbeef" * 8,
        }
        opener = _fake_opener(
            {
                updater_mod.API_URL: _make_response(release),
                updater_mod.LATEST_JSON_URL: _make_response(manifest),
            }
        )
        u = Updater(current_version="4.0.0", opener=opener)
        info = u.check()
        self.assertIsNotNone(info)
        assert info is not None
        # The manifest overrides the asset URL and provides a SHA256.
        self.assertEqual(info.download_url, "https://example.com/correct.exe")
        self.assertEqual(info.expected_sha256, "deadbeef" * 8)


class UpdaterDownloadTests(unittest.TestCase):
    def setUp(self) -> None:
        sys.frozen = True
        os.environ["NOVELTRAD_SKIP_UPDATE"] = "0"

    def test_sha256_mismatch_raises(self) -> None:
        body = b"installer-bytes"

        class _Resp:
            def __init__(self):
                self._buf = io.BytesIO(body)
                self.headers = {"Content-Length": str(len(body))}

            def read(self, n: int = -1) -> bytes:
                if n < 0:
                    return self._buf.read()
                return self._buf.read(n)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def _open(req, timeout=None):
            return _Resp()

        u = Updater(current_version="4.0.0", opener=_open)
        info = UpdateInfo(
            version="4.1.0",
            tag="v4.1.0",
            release_date="",
            body="",
            download_url="https://example.com/setup.exe",
            expected_sha256="0" * 64,  # wrong
        )
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "setup.exe"
            with self.assertRaises(ValueError):
                u.download(info, dest=dest)
            # The file must be cleaned up on mismatch.
            self.assertFalse(dest.exists())

    def test_download_writes_file_and_progress(self) -> None:
        body = b"x" * (256 * 1024 + 17)
        digest = hashlib.sha256(body).hexdigest().lower()

        class _Resp:
            def __init__(self):
                self._buf = io.BytesIO(body)
                self.headers = {"Content-Length": str(len(body))}

            def read(self, n: int = -1) -> bytes:
                if n < 0:
                    return self._buf.read()
                return self._buf.read(n)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        u = Updater(current_version="4.0.0", opener=lambda r, t=None: _Resp())
        info = UpdateInfo(
            version="4.1.0",
            tag="v4.1.0",
            release_date="",
            body="",
            download_url="https://example.com/setup.exe",
            expected_sha256=digest,
        )
        calls: list[tuple[int, int]] = []

        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "setup.exe"
            out = u.download(info, dest=dest, progress_cb=lambda a, b: calls.append((a, b)))
            self.assertTrue(out.exists())
            self.assertEqual(out.read_bytes(), body)
            self.assertGreaterEqual(len(calls), 1)
            last = calls[-1]
            self.assertEqual(last[0], len(body))
            self.assertEqual(last[1], len(body))


if __name__ == "__main__":
    unittest.main()




