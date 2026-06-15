# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for NovelTrad Desktop (v4).

Build: pyinstaller build.spec --noconfirm
Output: dist/NovelTrad/NovelTrad.exe

The GUI (src/main_qt.py) spawns the backend (src/backend/server.py)
as a subprocess at runtime, so we only need to bundle the GUI entrypoint.
The backend modules are still included (hiddenimports) so the spawn
`-m src.backend.server` works inside the frozen exe too.
"""

from pathlib import Path


datas = []
for qm in Path('src/gui/i18n').glob('*.qm'):
    datas.append((str(qm), 'src/gui/i18n'))
binaries = []
hiddenimports = [
    # v4 backend (the GUI spawns these as a subprocess)
    'src.backend.server',
    'src.backend.server.app',
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
    'src.backend.agents.terminology_researcher',
    'src.backend.agents.reviewer',
    'src.backend.agents.prompt_contracts',
    'src.backend.agents.assembler',
    'src.backend.llm_router.router',
    'src.backend.engines.nllb_engine',
    'src.backend.formats',
    'src.backend.routes',
    'src.backend.routes.projects',
    'src.backend.routes.deps',
    # v4 GUI
    'src.gui.app_config',
    'src.gui.backend_client',
    'src.gui.first_run_wizard',
    'src.gui.main_window',
    'src.gui.a11y',
    'src.gui.i18n',
    'src.gui.notifier',
    'src.gui.theme',
    'src.gui.updater',
    'src.gui.tabs.__init__',
    'src.gui.tabs.translate_tab',
    'src.gui.tabs.settings_tab',
    'src.gui.tabs.glossaries_tab',
    'src.gui.tabs.files_tab',
    'src.gui.tabs.projects_tab',
    'src.gui.tabs.review_model',
    'src.gui.widgets.activity_log',
    'src.gui.widgets.event_debouncer',
    'src.gui.dialogs.hitl_popup',
    'src.gui.dialogs.chunk_detail_dialog',
    'src.gui.dialogs.update_dialog',
    # stdlib modules sometimes missed by static analysis
    'sqlite3',
    # NLLB engine dependencies — imported inside try/except ImportError
    # so PyInstaller static analysis does not see them.
    'ctranslate2',
    'sentencepiece',
]

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
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'notebook',
        'ipython',
    ],
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
    icon='assets/noveltrad-icon.ico',
)
# Include assets alongside the exe for runtime use
datas.append(('assets/noveltrad-icon.ico', 'assets'))
datas.append(('assets/noveltrad-logo-256.png', 'assets'))

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
