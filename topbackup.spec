# -*- mode: python ; coding: utf-8 -*-
# TopBackup - PyInstaller Spec File
# Gera executável único (onefile) auto-instalável

import os
import sys

block_cipher = None

# Diretório base
BASE_DIR = os.path.dirname(os.path.abspath(SPEC))

# Dados adicionais - serão embutidos no executável
datas = [
    (os.path.join(BASE_DIR, 'assets'), 'assets'),
    (os.path.join(BASE_DIR, 'config', 'config.json.example'), 'config'),
]

# Binários ocultos necessários
hiddenimports = [
    'win32timezone',
    'win32serviceutil',
    'win32service',
    'win32event',
    'servicemanager',
    'win32pipe',
    'win32file',
    'pywintypes',
    'fdb',
    'mysql.connector',
    'customtkinter',
    'pystray',
    'PIL',
    'PIL.Image',
    'apscheduler',
    'apscheduler.schedulers.background',
    'apscheduler.triggers.cron',
    'apscheduler.triggers.interval',
    'packaging',
    'packaging.version',
]

a = Analysis(
    [os.path.join(BASE_DIR, 'src', 'main.py')],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Executável único (onefile) - tudo embutido
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TopBackup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(BASE_DIR, 'assets', 'icon.ico'),
    uac_admin=False,
)
