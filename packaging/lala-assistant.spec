# PyInstaller spec — builds a single-file native executable for the Python
# assistant:   pip install pyinstaller && pyinstaller packaging/lala-assistant.spec
# Output lands in dist/lala-assistant(.exe)

import os

block_cipher = None

a = Analysis(
    ['assistant/__main__.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[],
    hiddenimports=[
        'assistant.config', 'assistant.memory', 'assistant.router',
        'assistant.llm', 'assistant.stt', 'assistant.tts', 'assistant.wake',
        'assistant.mic', 'assistant.orchestrator', 'assistant.gui',
        'assistant.server', 'assistant.deploy', 'assistant.autostart',
        'assistant.elevenlabs', 'assistant.train_wakeword',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='lala-assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # keep console for logs; set False for a pure GUI binary
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
