# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui_launcher.py'],
    pathex=['C:/OLTREVISTA_AI/ZUKWEND_repo'],
    binaries=[],
    datas=[('C:/Python310_AI/lib/site-packages/customtkinter', 'customtkinter'), ('C:/OLTREVISTA_AI/ZUKWEND_repo/prompts', 'prompts')],
    hiddenimports=['reportlab', 'reportlab.platypus', 'reportlab.lib', 'reportlab.lib.pagesizes', 'reportlab.pdfbase', 'reportlab.pdfbase.ttfonts', 'customtkinter', 'docx', 'requests', 'pdfplumber', 'PyPDF2', 'pypdf', 'PIL', 'resource_utils', 'workflow_engine', 'parser', 'normalizer', 'classifier', 'deducer', 'report_generator', 'export_engine', 'license_manager', 'reminder_engine'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'transformers', 'spacy', 'thinc', 'tensorboard', 'scipy', 'matplotlib', 'pandas', 'numpy.testing', 'pytest', 'unittest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ZUKWEND',
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
    version='C:/OLTREVISTA_AI/ZUKWEND_repo/version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZUKWEND',
)
