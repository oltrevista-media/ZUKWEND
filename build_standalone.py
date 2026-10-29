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

    VERSION_FILE = ROOT_DIR / "version_info.txt"

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
        "--hidden-import=reportlab.pdfbase",
        "--hidden-import=reportlab.pdfbase.ttfonts",
        "--hidden-import=customtkinter",
        "--hidden-import=docx",
        "--hidden-import=requests",
        "--hidden-import=pdfplumber",
        "--hidden-import=PyPDF2",
        "--hidden-import=pypdf",
        "--hidden-import=PIL",
        "--hidden-import=resource_utils",
        "--hidden-import=workflow_engine",
        "--hidden-import=parser",
        "--hidden-import=normalizer",
        "--hidden-import=classifier",
        "--hidden-import=deducer",
        "--hidden-import=report_generator",
        "--hidden-import=export_engine",
        "--hidden-import=license_manager",
        "--hidden-import=reminder_engine",
        "--hidden-import=engine_dispatcher",
    ]

    if VERSION_FILE.exists():
        cmd.append(f"--version-file={VERSION_FILE}")

    for exc in EXCLUDES:
        cmd.append(f"--exclude-module={exc}")

    cmd.append("gui_launcher.py")

    print(f"[*] Avvio compilazione PyInstaller v2.1.5...")
    res = subprocess.run(cmd)

    if res.returncode == 0:
        print("\n" + "=" * 60)
        print(" BUILD v2.1.5 COMPLETATA CON SUCCESSO!")
        exe_path = DIST_DIR / "ZUKWEND" / "ZUKWEND.exe"
        print(f" Eseguibile generato in: {exe_path}")
        print("=" * 60)
        sign_executable(exe_path)
    else:
        print("\n[!] Errore durante la compilazione PyInstaller.")
        sys.exit(res.returncode)


def sign_executable(exe_path: Path):
    """
    EV Code Signing via Certum SimplySign and RFC 3161 SHA256 timestamping (time.certum.pl).
    """
    signtool_candidates = [
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
        "signtool.exe"
    ]
    signtool = None
    for cand in signtool_candidates:
        if os.path.exists(cand) or cand == "signtool.exe":
            signtool = cand
            break

    thumbprint = "15524BC0B781512EB092F60A6F60E7223B61C43B"
    timestamp_server = "http://time.certum.pl"

    print("\n[*] Applying Certum EV Code Signing with SHA256 RFC 3161 timestamping...")
    cmd = [
        signtool, "sign",
        "/sha1", thumbprint,
        "/fd", "sha256",
        "/tr", timestamp_server,
        "/td", "sha256",
        str(exe_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

    # Verification
    verify = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"Get-AuthenticodeSignature '{exe_path}' | Format-List Status, SignerCertificate"],
        capture_output=True,
        text=True
    )
    print("[*] Signature Status Verification:")
    print(verify.stdout)


if __name__ == "__main__":
    run_build()