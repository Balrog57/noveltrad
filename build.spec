# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for NovelTrad Desktop (v4).

Build: pyinstaller build.spec --noconfirm
Output: dist/NovelTrad/NovelTrad.exe

The GUI (src/gui/main_window.py) spawns the backend (src/backend/server.py)
as a subprocess at runtime, so we only need to bundle the GUI entrypoint.
The backend modules are still included (hiddenimports) so the spawn
`-m src.backend.server` works inside the frozen exe too.
"""
from PyInstaller.utils.hooks import collect_all

datas = [('resources', 'resources')]
binaries = []
hiddenimports = [
    # Legacy v3 engines
    'src.engines.google_engine',
    'src.engines.nllb_engine',
    'src.engines.llm_engine',
    'src.engines.argos_engine',
    # v4 backend (the GUI spawns these as a subprocess)
    'src.backend.server',
    'src.backend.orchestrator.orchestrator',
    'src.backend.orchestrator.state_store',
    'src.backend.orchestrator.worker_manager',
    'src.backend.orchestrator.pipeline',
    'src.backend.agents.parser',
    'src.backend.agents.fast_translator',
    'src.backend.agents.lexicon_builder',
    'src.backend.agents.glossary_applier',
    'src.backend.agents.consistency_checker',
    'src.backend.agents.qa_validator',
    'src.backend.agents.grammar_proofer',
    'src.backend.agents.llm_polisher',
    'src.backend.agents.assembler',
    'src.backend.llm_router.router',
    'src.backend.engines.nllb_engine',
    'src.backend.formats',
    'deep_translator',
    'peewee',
    'sqlite3',
]

# Collect deep_translator dependencies
try:
    tmp_ret = collect_all('deep_translator')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception:
    pass

block_cipher = None

a = Analysis(
    ['src/main_qt.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'pandas', 'notebook', 'ipython'],
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
    name='NovelTrad',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NovelTrad',
)
