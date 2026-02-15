# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\main_qt.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src')],
    hiddenimports=['src.gui.mainwindow', 'src.gui.styles', 'src.core.project_manager', 'src.engines.llm_engine', 'src.core.database'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NovelTrad',
)
