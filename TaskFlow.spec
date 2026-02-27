# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['TaskFlow\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('c:\\Users\\Lennard Finn Penzler\\Documents\\VSC_Projects\\todo_app\\TaskFlow\\TaskFlow\\assets', 'assets'), ('c:\\Users\\Lennard Finn Penzler\\Documents\\VSC_Projects\\todo_app\\TaskFlow\\TaskFlow\\sounds', 'sounds'), ('c:\\Users\\Lennard Finn Penzler\\Documents\\VSC_Projects\\todo_app\\TaskFlow\\TaskFlow\\release_notes.txt', '.'), ('c:\\Users\\Lennard Finn Penzler\\Documents\\VSC_Projects\\todo_app\\TaskFlow\\TaskFlow\\icon.ico', '.')],
    hiddenimports=['torch', 'dateparser', 'pyaudio', 'faster_whisper', 'core.analytics', 'ai.engine'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pygame'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TaskFlow',
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
    icon=['c:\\Users\\Lennard Finn Penzler\\Documents\\VSC_Projects\\todo_app\\TaskFlow\\TaskFlow\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TaskFlow',
)
