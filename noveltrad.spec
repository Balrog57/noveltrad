# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for AgentTranslate (NovelTrad).

Build a Windows .exe with:
    uv run --extra dev pyinstaller noveltrad.spec --clean --noconfirm

Produces dist/AgentTranslate/ (onedir) — recommended for a Qt app because
PySide6 binaries are large and onefile startup is slow.

CDC §5: 'Packaging Windows via PyInstaller ou Briefcase'.
"""

import sys
from pathlib import Path

block_cipher = None

# Collect all data/binaries PySide6 needs at runtime.
from PySide6 import QtWidgets  # noqa: E402

pyside6_dir = Path(QtWidgets.__file__).resolve().parent.parent

datas = [
    # Bundled icon.
    ("assets/icon.png", "assets"),
]
# PySide6 plugins (platforms, styles, imageformats, etc.) — use collect_all.
from PyInstaller.utils.hooks import collect_all  # noqa: E402

pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")
datas += pyside6_datas
hiddenimports = list(pyside6_hiddenimports)

# langchain/langgraph dynamic imports.
for pkg in ("langchain_ollama", "langchain_openai", "langchain_core", "langgraph"):
    d, b, h = collect_all(pkg)
    datas += d
    hiddenimports += h

# Auto-update: bundle the package metadata so importlib.metadata.version()
# works inside the frozen app, and ensure the updater deps are collected.
from PyInstaller.utils.hooks import copy_metadata  # noqa: E402

datas += copy_metadata("noveltrad")
datas += copy_metadata("packaging")
hiddenimports += ["importlib.metadata", "packaging", "requests"]

a = Analysis(
    ["src/app.py"],
    pathex=["."],
    binaries=pyside6_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "tests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AgentTranslate",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI app, no console window.
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico" if (Path("assets") / "icon.ico").exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AgentTranslate",
)
