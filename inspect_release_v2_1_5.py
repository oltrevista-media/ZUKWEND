import zipfile
import subprocess
from pathlib import Path

rootDir = Path("C:/OLTREVISTA_AI")
repoPath = rootDir / "ZUKWEND_repo"
zipPath = repoPath / "dist" / "ZUKWEND_FULL_v2_1_5_Setup.zip"

assert zipPath.exists(), f"ZIP non trovato: {zipPath}"

print("=" * 72)
print("VERIFICA ISPETTIVA RELEASE PACKAGING v2.1.5 — ZUKWEND")
print("=" * 72)
print(f"Target Zip: {zipPath}")

with zipfile.ZipFile(zipPath, "r") as zf:
    namelist = zf.namelist()
    
    # 1. Verifica assenza totale di file con estensione .py
    py_files = [f for f in namelist if f.endswith(".py")]
    
    # Verifica esclusione script di test e rimasugli
    source_leak_files = [f for f in namelist if any(f.endswith(ext) for ext in [".py", ".pyc", ".pyw"])]
    cache_dirs = [f for f in namelist if any(bad in f for bad in ["__pycache__", ".git/", ".pytest_cache", "build/", "dist/"])]
    
    # 2. Elenco esatto dei file/cartelle presenti nella radice dello ZIP
    root_entries = sorted(list(set(f.split("/")[0] for f in namelist)))
    
    # Whitelist di riferimento da Ordine Operativo v2.1.5:
    # - ZUKWEND.exe (firmato)
    # - INSTALLATION_GUIDE.txt
    # - LICENSE_EULA.txt
    # - zukwend_config.json
    # - demo/
    # - output/
    # - prompts/
    # - _internal/
    whitelist_expected = sorted([
        "ZUKWEND.exe",
        "INSTALLATION_GUIDE.txt",
        "LICENSE_EULA.txt",
        "zukwend_config.json",
        "demo",
        "output",
        "prompts",
        "_internal"
    ])
    
    # 3. Verifica presenza demo/b2b_invoice_sample_en.pdf
    demo_sample_present = "demo/b2b_invoice_sample_en.pdf" in namelist
    
    # 4. Verifica presenza output/.gitkeep
    output_gitkeep_present = "output/.gitkeep" in namelist

    # 5. Dimensione finale dell'archivio
    stat = zipPath.stat()
    size_mb = stat.st_size / (1024 * 1024)
    size_bytes = stat.st_size

print(f"Totale file/cartelle archiviati: {len(namelist)}")
print("-" * 72)

# CHECK 1
print("PUNTO 1 — ASSENZA TOTALE DI FILE CON ESTENSIONE .py (NO SOURCE LEAK):")
if len(py_files) == 0:
    print("   [CONFERMATO] Nessun file .py rilevato nell'intero archivio (0 file .py).")
    print("   [CONFERMATO] Nessun file sorgente Python, test o utilità esposto (NO SOURCE LEAK).")
    check1_passed = True
else:
    print(f"   [FALLITO] Rilevati {len(py_files)} file .py:")
    for pf in py_files:
        print(f"     - {pf}")
    check1_passed = False

print("-" * 72)

# CHECK 2
print("PUNTO 2 — ELENCO ESATTO DEI FILE/CARTELLE NELLA RADICE DELLO ZIP:")
check2_passed = (root_entries == whitelist_expected)
for i, entry in enumerate(root_entries, 1):
    status = "[WHITELIST OK]" if entry in whitelist_expected else "[NON AUTORIZZATO]"
    print(f"   {i:2d}. {entry:<30} {status}")

print(f"\n   Confronto Whitelist Ordine Operativo v2.1.5: {'CONFORME AL 100%' if check2_passed else 'NON CONFORME'}")
print("-" * 72)

# CHECK 3
print("PUNTO 3 — PRESENZA demo/ ED output/:")
print(f"   demo/b2b_invoice_sample_en.pdf: {'[CONFERMATO]' if demo_sample_present else '[MANCANTE]'}")
print(f"   output/.gitkeep:                {'[CONFERMATO]' if output_gitkeep_present else '[MANCANTE]'}")
check3_passed = demo_sample_present and output_gitkeep_present

print("-" * 72)

# CHECK 4
print("PUNTO 4 — DIMENSIONE FINALE ARCHIVIO:")
print(f"   Dimensione: {size_mb:.2f} MB ({size_bytes} bytes)")
check4_passed = stat.st_size > 0

print("=" * 72)
if check1_passed and check2_passed and check3_passed and check4_passed and len(cache_dirs) == 0:
    print("ESITO VERIFICA ZIP: SUCCESS (CONFORME)")
else:
    print("ESITO VERIFICA ZIP: FAILED")
print("=" * 72)
