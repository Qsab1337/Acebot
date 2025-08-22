# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('main_simple.py', '.'), ('overlay_windows.py', '.'), ('advanced_capture.py', '.'), ('simple_gemini_provider.py', '.'), ('simple_ocr.py', '.'), ('ui_automation_capture.py', '.'), ('prompt.txt', '.'), ('settings.json', '.'), ('version.txt', '.')],
    hiddenimports=['pynput', 'PyQt5', 'PIL', 'requests', 'pytesseract', 'mss', 'pyautogui', 'psutil', 'numpy', 'packaging'],
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
    a.binaries,
    a.datas,
    [],
    name='GoStealthAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
