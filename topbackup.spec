# -*- mode: python ; coding: utf-8 -*-
# TopBackup - PyInstaller Spec File
# Gera pasta completa pronta para distribuição

import os
import sys

block_cipher = None

# Diretório base
BASE_DIR = os.path.dirname(os.path.abspath(SPEC))

# Dados adicionais - serão copiados para a pasta de distribuição
datas = [
    (os.path.join(BASE_DIR, 'assets'), 'assets'),
    (os.path.join(BASE_DIR, 'config', 'config.json.example'), 'config'),
    (os.path.join(BASE_DIR, 'scripts'), 'scripts'),
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
        'email',
        'html',
        'http',
        'xml',
        'pydoc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Executável principal (GUI)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TopBackup',
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
    icon=os.path.join(BASE_DIR, 'assets', 'icon.ico'),
    uac_admin=False,
)

# COLLECT - Gera pasta completa com todos os arquivos
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TopBackup',
)
