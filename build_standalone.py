"""
ZUKWEND — Standalone Executable Builder (Production / Slim Edition)
Compilazione industriale PyInstaller con esclusione Bloatware (Torch, Transformers, Spacy)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"

def run_build():
    print("[*] Inizializzazione build industriale per ZUKWEND Billing Agent...")

    import customtkinter
    ctk_path = Path(customtkinter.__file__).parent

    # Lista nera pacchetti pesanti non utilizzati dall'agente desktop
    EXCLUDES = [
        "torch",
        "torchvision",
        "torchaudio",
        "transformers",
        "spacy",
        "thinc",
        "tensorboard",
        "scipy",
        "matplotlib",
        "pandas",
        "numpy.testing",
        "pytest",
        "unittest",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ZUKWEND",
        "--noconsole",
        "--clean",
        "--noconfirm",
        f"--paths={ROOT_DIR}",
        f"--add-data={ctk_path};customtkinter",
        f"--add-data={ROOT_DIR / 'prompts'};prompts",
        "--hidden-import=reportlab",
        "--hidden-import=reportlab.platypus",
        "--hidden-import=reportlab.lib",
        "--hidden-import=reportlab.lib.pagesizes",
        "--hidden-import=customtkinter",
        "--hidden-import=docx",
        "--hidden-import=requests",
        "--hidden-import=pdfplumber",
        "--hidden-import=PyPDF2",
        "--hidden-import=pypdf",
        "--hidden-import=PIL",
        "--hidden-import=workflow_engine",
        "--hidden-import=parser",
        "--hidden-import=normalizer",
        "--hidden-import=classifier",
        "--hidden-import=deducer",
        "--hidden-import=report_generator",
        "--hidden-import=export_engine",
        "--hidden-import=license_manager",
        "--hidden-import=reminder_engine",
    ]

    for exc in EXCLUDES:
        cmd.append(f"--exclude-module={exc}")

    cmd.append("gui_launcher.py")

    print(f"[*] Avvio compilazione PyInstaller...")
    res = subprocess.run(cmd)

    if res.returncode == 0:
        print("\n" + "=" * 60)
        print(" BUILD COMPLETATA CON SUCCESSO!")
        exe_path = DIST_DIR / "ZUKWEND" / "ZUKWEND.exe"
        print(f" Eseguibile generato in: {exe_path}")
        print("=" * 60)
    else:
        print("\n[!] Errore durante la compilazione PyInstaller.")
        sys.exit(res.returncode)

if __name__ == "__main__":
    run_build()