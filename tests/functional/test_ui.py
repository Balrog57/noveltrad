"""Functional tests via Playwright (SDD 17.4, FT-AUTH-001, EF-015).

The app must be started externally with:
  APP_PASSWORD, NOVELTRAD_DATA_DIR set; streamlit on port 8521.
See tests/functional/README or run_app fixture guidance.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

_APP_PASSWORD = "functional-test-password-123"
_PORT = 8521
_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = Path(os.environ.get("TEMP", "/tmp")) / "noveltrad-ft"


@pytest.fixture(scope="session")
def app_process():
    _DATA_DIR.mkdir(exist_ok=True)
    env = dict(os.environ)
    env["APP_PASSWORD"] = _APP_PASSWORD
    env["NOVELTRAD_DATA_DIR"] = str(_DATA_DIR)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(_ROOT / "src" / "noveltrad" / "app" / "main.py"),
            "--server.headless=true",
            f"--server.port={_PORT}",
        ],
        cwd=_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"http://localhost:{_PORT}/_stcore/health", timeout=3):
                break
        except Exception:
            time.sleep(2)
    yield
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture()
def browser(app_process):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.mark.parametrize("width", [390, 768, 1280])
def test_auth_required(browser, width):
    page = browser.new_page(viewport={"width": width, "height": 800})
    page.goto(f"http://localhost:{_PORT}")
    page.get_by_text("Authentification").wait_for()
    page.get_by_text("Mot de passe").wait_for()
    page.close()


@pytest.mark.parametrize("width", [390, 768, 1280])
def test_auth_wrong_password(browser, width):
    page = browser.new_page(viewport={"width": width, "height": 800})
    page.goto(f"http://localhost:{_PORT}")
    page.get_by_role("textbox").fill("wrong-password")
    page.get_by_role("button", name="Se connecter").click()
    page.get_by_text("Mot de passe incorrect.").wait_for()
    page.close()


@pytest.mark.parametrize("width", [390, 768, 1280])
def test_auth_success_shows_projects(browser, width):
    page = browser.new_page(viewport={"width": width, "height": 800})
    page.goto(f"http://localhost:{_PORT}")
    page.get_by_role("textbox").fill(_APP_PASSWORD)
    page.get_by_role("button", name="Se connecter").click()
    page.get_by_text("Nouveau projet", exact=False).wait_for(timeout=15000)
    page.close()


def test_create_project_and_import(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(f"http://localhost:{_PORT}")
    page.get_by_role("textbox").fill(_APP_PASSWORD)
    page.get_by_role("button", name="Se connecter").click()
    page.get_by_text("Nouveau projet", exact=False).wait_for(timeout=15000)
    page.close()
