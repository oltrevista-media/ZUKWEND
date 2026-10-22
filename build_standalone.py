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
    ]

    if VERSION_FILE.exists():
        cmd.append(f"--version-file={VERSION_FILE}")

    for exc in EXCLUDES:
        cmd.append(f"--exclude-module={exc}")

    cmd.append("gui_launcher.py")

    print(f"[*] Avvio compilazione PyInstaller v2.1.4...")
    res = subprocess.run(cmd)

    if res.returncode == 0:
        print("\n" + "=" * 60)
        print(" BUILD v2.1.4 COMPLETATA CON SUCCESSO!")
        exe_path = DIST_DIR / "ZUKWEND" / "ZUKWEND.exe"
        print(f" Eseguibile generato in: {exe_path}")
        print("=" * 60)
        sign_executable(exe_path)
    else:
        print("\n[!] Errore durante la compilazione PyInstaller.")
        sys.exit(res.returncode)


def sign_executable(exe_path: Path):
    """
    Predisposizione firma digitale EV Code Signing OLTREVISTA tramite signtool.
    Comando standard:
      signtool sign /f oltrevista_cert.pfx /p PASSWORD /tr SERVER_TIMESTAMP /td sha256 ZUKWEND.exe
    """
    cert_file = os.environ.get("OLTREVISTA_CERT_PFX", "oltrevista_cert.pfx")
    cert_pass = os.environ.get("OLTREVISTA_CERT_PASSWORD", "PASSWORD")
    timestamp_server = os.environ.get("OLTREVISTA_TIMESTAMP_URL", "http://timestamp.digicert.com")

    sign_cmd_template = (
        f'signtool sign /f {cert_file} /p {cert_pass} '
        f'/tr {timestamp_server} /td sha256 /fd sha256 "{exe_path}"'
    )
    print("\n[*] Predisposizione EV Code Signing (OLTREVISTA):")
    print(f"    signtool sign /f oltrevista_cert.pfx /p PASSWORD /tr SERVER_TIMESTAMP /td sha256 ZUKWEND.exe")

    if Path(cert_file).exists():
        print(f"[*] Certificato rilevato ({cert_file}). Avvio firma digitale...")
        subprocess.run(
            [
                "signtool", "sign",
                "/f", cert_file,
                "/p", cert_pass,
                "/tr", timestamp_server,
                "/td", "sha256",
                "/fd", "sha256",
                str(exe_path),
            ],
            check=False,
        )
    else:
        print(f"[i] Certificato '{cert_file}' non presente in locale — step signtool pronto per pipeline release.")


if __name__ == "__main__":
    run_build()