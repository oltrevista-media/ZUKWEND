"""
ZUKWEND — Builder Eseguibile Windows (.exe)
Inclusione esplicita di moduli core e prompt.
"""
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
ENTRY_POINT = BASE_DIR / "workflow_engine.py"
PROMPTS_DIR = BASE_DIR / "prompts"
VERSION_FILE = BASE_DIR / "version_info.txt"

MODULES_TO_INCLUDE = [
    "resource_utils",
    "parser",
    "normalizer",
    "classifier",
    "deducer",
    "report_generator",
    "export_engine",
    "license_manager",
]

def build():
    print("[*] Avvio compilazione ZUKWEND v2.1.5 completa per Windows (.exe)...")
    
    if not ENTRY_POINT.exists():
        print(f"[ERR] Entry point non trovato: {ENTRY_POINT}")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name=ZUKWEND",
        f"--paths={BASE_DIR}",
        f"--add-data={PROMPTS_DIR};prompts",
    ]

    if VERSION_FILE.exists():
        cmd.append(f"--version-file={VERSION_FILE}")

    for mod in MODULES_TO_INCLUDE:
        cmd.append(f"--hidden-import={mod}")

    cmd.append(str(ENTRY_POINT))

    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        exe_out = BASE_DIR / "dist" / "ZUKWEND" / "ZUKWEND.exe"
        print("\n[OK] Compilazione completata con successo!")
        print(f"File generato in: {exe_out}")
        print("\n[*] Comando EV Code Signing (OLTREVISTA):")
        print("    signtool sign /f oltrevista_cert.pfx /p PASSWORD /tr SERVER_TIMESTAMP /td sha256 ZUKWEND.exe")
        if Path("oltrevista_cert.pfx").exists():
            subprocess.run([
                "signtool", "sign",
                "/f", "oltrevista_cert.pfx",
                "/p", os.environ.get("OLTREVISTA_CERT_PASSWORD", "PASSWORD"),
                "/tr", os.environ.get("OLTREVISTA_TIMESTAMP_URL", "http://timestamp.digicert.com"),
                "/td", "sha256",
                str(exe_out),
            ], check=False)
    else:
        print("\n[ERR] Errore durante la compilazione.")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build()