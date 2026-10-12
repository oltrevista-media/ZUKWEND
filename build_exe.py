"""
ZUKWEND — Builder Eseguibile Windows (.exe)
Inclusione esplicita di moduli core e prompt.
"""
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
ENTRY_POINT = BASE_DIR / "workflow_engine.py"
PROMPTS_DIR = BASE_DIR / "prompts"

MODULES_TO_INCLUDE = [
    "parser",
    "normalizer",
    "classifier",
    "deducer",
    "report_generator",
    "export_engine",
    "license_manager",
]

def build():
    print("[*] Avvio compilazione ZUKWEND completa per Windows (.exe)...")
    
    if not ENTRY_POINT.exists():
        print(f"[ERR] Entry point non trovato: {ENTRY_POINT}")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name=ZUKWEND_Billing_Agent",
        f"--paths={BASE_DIR}",
        f"--add-data={PROMPTS_DIR};prompts",
    ]

    for mod in MODULES_TO_INCLUDE:
        cmd.append(f"--hidden-import={mod}")

    cmd.append(str(ENTRY_POINT))

    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n[OK] Compilazione completata con successo!")
        print(f"File generato in: {BASE_DIR / 'dist' / 'ZUKWEND_Billing_Agent' / 'ZUKWEND_Billing_Agent.exe'}")
    else:
        print("\n[ERR] Errore durante la compilazione.")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build()