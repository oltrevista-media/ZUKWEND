import zipfile
from pathlib import Path

U = chr(95)
rootDir = Path("C:/OLTREVISTA" + U + "AI")
repoPath = rootDir / ("ZUKWEND" + U + "repo")
outputDir = rootDir / ("02" + U + "VERTICALI/ZUKWEND/FULL")
zipNameBase = "ZUKWEND" + U + "FULL" + U + "v2" + U + "1" + U + "4" + U + "Setup"
zipExt = "." + "z" + "ip"
zipFilename = zipNameBase + zipExt
targetZip = repoPath / "dist" / zipFilename
if not targetZip.exists():
    targetZip = outputDir / zipFilename

assert targetZip.exists(), f"ZIP non trovato: {targetZip}"

with zipfile.ZipFile(targetZip, "r") as zf:
    namelist = zf.namelist()
    
    # 1. Verifica assenza totale di file con estensione .py
    py_files = [f for f in namelist if f.endswith(".py")]
    
    # Verifica esclusione script di test e rimasugli
    source_leak_files = [f for f in namelist if any(f.endswith(ext) for ext in [".py", ".pyc", ".pyw"])]
    cache_dirs = [f for f in namelist if any(bad in f for bad in ["__pycache__", ".git/", ".pytest_cache", "build/", "dist/"])]
    
    # 2. Elenco esatto dei file/cartelle presenti nella radice dello ZIP
    root_entries = sorted(list(set(f.split("/")[0] for f in namelist)))
    
    # Whitelist di riferimento SEZIONE 3
    whitelist_expected = sorted([
        "ZUKWEND.exe",
        "_internal",
        "prompts",
        "output",
        "zukwend_config.json",
        "b2b_invoice_sample_en.pdf",
        "DISCLAIMER_EULA.md",
        "README.txt",
        "ISTRUZIONI_INSTALLAZIONE_WINDOWS.txt",
        "WINDOWS_INSTALLATION_NOTE.txt"
    ])
    
    # 3. Verifica presenza cartella output/ con .gitkeep
    output_gitkeep_present = "output/.gitkeep" in namelist
    
    # 4. Dimensione finale dell'archivio
    stat = targetZip.stat()
    size_mb = stat.st_size / (1024 * 1024)
    size_bytes = stat.st_size

print("=" * 72)
print("VERIFICA ISPETTIVA CLEAN RELEASE PACKAGING v2.1.3 — ZUKWEND")
print("=" * 72)
print(f"Target Zip: {targetZip}")
print(f"Totale record archiviati: {len(namelist)}")
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
    print(f"   {i:2d}. {entry:<35} {status}")

print(f"\n   Confronto Whitelist Sezione 3: {'CONFORME AL 100%' if check2_passed else 'NON CONFORME'}")
print("-" * 72)

# CHECK 3
print("PUNTO 3 — PRESENZA CARTELLA output/ E PLACEHOLDER .gitkeep:")
if output_gitkeep_present:
    print("   [CONFERMATO] output/.gitkeep presente all'interno del pacchetto.")
    check3_passed = True
else:
    print("   [FALLITO] output/.gitkeep mancante nello ZIP.")
    check3_passed = False

print("-" * 72)

# CHECK 4
print("PUNTO 4 — DIMENSIONE FINALE ARCHIVIO ED ESITO:")
print(f"   Dimensione: {size_mb:.2f} MB ({size_bytes} bytes)")
check4_passed = stat.st_size > 0

print("=" * 72)
if check1_passed and check2_passed and check3_passed and check4_passed and len(cache_dirs) == 0:
    print("ESITO FINALE: SUCCESS")
else:
    print("ESITO FINALE: FAILED")
print("=" * 72)
