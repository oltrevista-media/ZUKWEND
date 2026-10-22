"""
ZUKWEND — Script di Packaging Automatico (REPTANA MODE)
Genera la struttura cartelle e il pacchetto ZIP per la distribuzione.
"""
import os
import shutil
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
PACKAGE_NAME = "ZUKWEND_Billing_Agent_v1.0"
TARGET_DIR = DIST_DIR / PACKAGE_NAME

CORE_FILES = [
    "resource_utils.py",
    "workflow_engine.py",
    "gui_launcher.py",
    "parser.py",
    "classifier.py",
    "deducer.py",
    "report_generator.py",
    "export_engine.py",
    "license_manager.py",
    "normalizer.py",
    "version_info.txt",
]

def make_package():
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Crea sottocartelle obbligatorie da specifica Reptana
    (TARGET_DIR / "output").mkdir(exist_ok=True)
    (TARGET_DIR / "invoices").mkdir(exist_ok=True)
    (TARGET_DIR / "templates").mkdir(exist_ok=True)
    
    # 2. Copia i moduli core
    for file_name in CORE_FILES:
        src = BASE_DIR / file_name
        if src.exists():
            shutil.copy2(src, TARGET_DIR / file_name)
        else:
            print(f"[WARN] File core opzionale o mancante: {file_name}")

    # 3. Crea README e Setup Guide
    readme_content = """# ZUKWEND Multilingual Billing Agent (v1.0)
Offline-First B2B Accounts Receivable Automation

### Requisiti:
- Python 3.10+
- Ollama con modello DeepSeek R1 8B (opzionale per modalità locale 100% offline)

### Setup Rapido:
1. Installa dipendenze: pip install -r requirements.txt
2. Esegui: python workflow_engine.py <tua_fattura.pdf> --mode local

Licenza: DEMO 7 giorni inclusa all'avvio.
Per attivazione licenza FULL: python license_manager.py --activate <IL_TUO_CODICE>
Supporto: contact@oltrevista.com
"""
    (TARGET_DIR / "README.txt").write_text(readme_content, encoding="utf-8")

    # 4. Genera file ZIP finale per Lemon Squeezy
    zip_path = DIST_DIR / f"{PACKAGE_NAME}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(TARGET_DIR):
            for file in files:
                file_path = Path(root) / file
                archive_name = file_path.relative_to(DIST_DIR)
                zipf.write(file_path, archive_name)

    print(f"\n[OK] Pacchetto ZUKWEND generato con successo:")
    print(f"-> Directory: {TARGET_DIR}")
    print(f"-> Archivio ZIP pronto per Lemon Squeezy: {zip_path}\n")

if __name__ == "__main__":
    make_package()