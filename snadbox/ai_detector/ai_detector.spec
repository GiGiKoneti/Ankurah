# -*- mode: python ; coding: utf-8 -*-
# ai_detector.spec — PyInstaller spec for a single-file AI detector executable.
# Build with: pyinstaller ai_detector.spec

import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # psutil and its platform sub-modules
        'psutil',
        'psutil._pswindows',
        'psutil._pslinux',
        'psutil._psosx',
        'psutil._common',
        'psutil._psposix',
        # GPU monitoring
        'pynvml',
        # Clipboard
        'pyperclip',
        'pyperclip.backends',
        # WebSocket server
        'websockets',
        'websockets.server',
        'websockets.client',
        'websockets.connection',
        'websockets.exceptions',
        'websockets.frames',
        'websockets.handshake',
        'websockets.http11',
        'websockets.legacy',
        'websockets.legacy.server',
        'websockets.legacy.client',
        'websockets.legacy.protocol',
        # File watcher
        'watchdog',
        'watchdog.observers',
        'watchdog.observers.polling',
        'watchdog.observers.fsevents',
        'watchdog.observers.inotify',
        'watchdog.observers.winapi',
        'watchdog.events',
        # Internal project packages
        'config',
        'capability',
        'aggregator',
        'emitter',
        'db',
        'db.ai_domains',
        'layers',
        'layers.browser',
        'layers.process',
        'layers.hardware',
        'layers.behavioral',
        'layers.network',
        # FastAPI / Uvicorn / Starlette
        'fastapi', 'uvicorn', 'uvicorn.main', 'uvicorn.config',
        'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols',
        'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan', 'uvicorn.lifespan.on',
        'starlette', 'starlette.routing', 'starlette.websockets',
        'anyio', 'anyio._backends._asyncio',
        # New layers
        'layers.stealth_windows',
    ],
    excludes=[
        # Must exclude scapy entirely (AV flagging risk)
        'scapy',
        # Heavy scientific packages not needed at runtime
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        # GUI toolkits not used
        'tkinter',
        '_tkinter',
        'PIL',
        'Pillow',
        # Test frameworks
        'pytest',
        'unittest',
        # Other unused heavy packages
        'IPython',
        'notebook',
        'jupyter',
        'sphinx',
        'docutils',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ai_detector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # Console app — required for consent prompt input
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,       # Single executable, no folder
)
