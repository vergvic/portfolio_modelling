# PyInstaller spec file for Portfolio Modeller
# Usage (from project root):
#   pyinstaller build/build.spec
#
# Produces dist/Portfolio Modeller/ with the .exe and all dependencies.
# For a single-file build, uncomment the EXE(onefile=True) option below.

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent   # project root

block_cipher = None

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'assets' / 'icon.ico'), 'assets'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'matplotlib.backends.backend_qtagg',
        'yfinance',
        'scipy.stats',
        'pandas',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='Portfolio Modeller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed app — no console
    icon=str(ROOT / 'assets' / 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Portfolio Modeller',
)
