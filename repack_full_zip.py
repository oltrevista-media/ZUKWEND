"""
ZUKWEND Clean Release Packaging v2.1.4 Enterprise
Compliant with ORDINE OPERATIVO ESECUTIVO - ZUKWEND v2.1.4 Enterprise
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

U = chr(95)
rootDir = Path("C:/OLTREVISTA" + U + "AI")
repoPath = rootDir / ("ZUKWEND" + U + "repo")
outputDir = rootDir / ("02" + U + "VERTICALI/ZUKWEND/FULL")
zipNameBase = "ZUKWEND" + U + "FULL" + U + "v2" + U + "1" + U + "4" + U + "Setup"
zipExt = "." + "z" + "ip"
zipFilename = zipNameBase + zipExt

targetZip = repoPath / "dist" / zipFilename
tempZip = repoPath / "dist" / (zipNameBase + ".tmp" + zipExt)

distZukwend = repoPath / "dist" / "ZUKWEND"
if not distZukwend.exists():
    distZukwend = outputDir / "dist" / "ZUKWEND"


print("=" * 70)
print(f"[*] CLEAN RELEASE PACKAGING v2.1.3 started at: {datetime.now()}")
print(f"[*] Target ZIP: {targetZip}")
print("=" * 70)

if tempZip.exists():
    tempZip.unlink()

# Whitelist elements definition:
# 1. ZUKWEND.exe (eseguibile principale ricompilato v2.1.3)
# 2. _internal/ (cartella dipendenze runtime PyInstaller)
# 3. prompts/ (cartella dei prompt di sistema)
# 4. output/ (cartella di destinazione report contenente il file placeholder .gitkeep)
# 5. zukwend_config.json (configurazione di runtime)
# 6. b2b_invoice_sample_en.pdf (sample di test cliente)
# 7. DISCLAIMER_EULA.md (licenza ed EULA)
# 8. README.txt (documentazione cliente)
# 9. ISTRUZIONI_INSTALLAZIONE_WINDOWS.txt (guida installazione)
# 10. WINDOWS_INSTALLATION_NOTE.txt (note tecniche Windows)

with zipfile.ZipFile(tempZip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    # 1. ZUKWEND.exe
    exe_path = distZukwend / "ZUKWEND.exe"
    assert exe_path.exists(), f"Missing {exe_path}"
    print(f"  [+] Adding {exe_path.name} ({exe_path.stat().st_size / (1024*1024):.2f} MB)...")
    zf.write(exe_path, "ZUKWEND.exe")

    # 2. _internal/
    internal_dir = distZukwend / "_internal"
    assert internal_dir.exists(), f"Missing {internal_dir}"
    print("  [+] Adding _internal/ tree (filtering out .py, __pycache__, .git)...")
    internal_count = 0
    for root, dirs, files in os.walk(internal_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache", "build", "dist")]
        for f in files:
            # Exclude *.py, test files, .DS_Store
            if f.endswith(".py") or f.startswith("."):
                continue
            fpath = Path(root) / f
            arcname = "_internal/" + str(fpath.relative_to(internal_dir)).replace("\\", "/")
            zf.write(fpath, arcname)
            internal_count += 1
    print(f"      Included {internal_count} files in _internal/.")

    # 3. prompts/
    prompts_dir = outputDir / "prompts"
    if not prompts_dir.exists():
        prompts_dir = repoPath / "prompts"
    assert prompts_dir.exists(), f"Missing {prompts_dir}"
    print("  [+] Adding prompts/...")
    prompts_count = 0
    for root, dirs, files in os.walk(prompts_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for f in files:
            if f.endswith(".py"):
                continue
            fpath = Path(root) / f
            arcname = "prompts/" + str(fpath.relative_to(prompts_dir)).replace("\\", "/")
            zf.write(fpath, arcname)
            prompts_count += 1
    print(f"      Included {prompts_count} files in prompts/.")

    # 4. output/ (.gitkeep)
    gitkeep_path = outputDir / "output" / ".gitkeep"
    if not gitkeep_path.exists():
        gitkeep_path = repoPath / "output" / ".gitkeep"
    if not gitkeep_path.exists():
        gitkeep_path.parent.mkdir(parents=True, exist_ok=True)
        gitkeep_path.touch()
    print("  [+] Adding output/.gitkeep...")
    zf.writestr("output/", "")
    zf.write(gitkeep_path, "output/.gitkeep")

    # 5. zukwend_config.json
    cfg_path = distZukwend / "zukwend_config.json"
    if not cfg_path.exists():
        cfg_path = outputDir / "zukwend_config.json"
    if not cfg_path.exists():
        cfg_path = repoPath / "zukwend_config.json"
    assert cfg_path.exists(), f"Missing {cfg_path}"
    print(f"  [+] Adding {cfg_path.name}...")
    zf.write(cfg_path, "zukwend_config.json")

    # 6. b2b_invoice_sample_en.pdf
    sample_pdf = outputDir / "b2b_invoice_sample_en.pdf"
    if not sample_pdf.exists():
        sample_pdf = repoPath / "b2b_invoice_sample_en.pdf"
    assert sample_pdf.exists(), f"Missing {sample_pdf}"
    print(f"  [+] Adding {sample_pdf.name}...")
    zf.write(sample_pdf, "b2b_invoice_sample_en.pdf")

    # 7. DISCLAIMER_EULA.md
    eula_path = outputDir / "DISCLAIMER_EULA.md"
    if not eula_path.exists():
        eula_path = repoPath / "DISCLAIMER_EULA.md"
    assert eula_path.exists(), f"Missing {eula_path}"
    print(f"  [+] Adding {eula_path.name}...")
    zf.write(eula_path, "DISCLAIMER_EULA.md")

    # 8. README.txt
    readme_path = outputDir / "README.txt"
    if not readme_path.exists():
        readme_path = repoPath / "README.txt"
    assert readme_path.exists(), f"Missing {readme_path}"
    print(f"  [+] Adding {readme_path.name}...")
    zf.write(readme_path, "README.txt")

    # 9. ISTRUZIONI_INSTALLAZIONE_WINDOWS.txt
    istr_path = outputDir / "ISTRUZIONI_INSTALLAZIONE_WINDOWS.txt"
    if not istr_path.exists():
        istr_path = repoPath / "downloads" / "ISTRUZIONI_INSTALLAZIONE_WINDOWS.txt"
    assert istr_path.exists(), f"Missing {istr_path}"
    print(f"  [+] Adding {istr_path.name}...")
    zf.write(istr_path, "ISTRUZIONI_INSTALLAZIONE_WINDOWS.txt")

    # 10. WINDOWS_INSTALLATION_NOTE.txt
    note_path = outputDir / "WINDOWS_INSTALLATION_NOTE.txt"
    if not note_path.exists():
        note_path = repoPath / "downloads" / "WINDOWS_INSTALLATION_NOTE.txt"
    assert note_path.exists(), f"Missing {note_path}"
    print(f"  [+] Adding {note_path.name}...")
    zf.write(note_path, "WINDOWS_INSTALLATION_NOTE.txt")

# Atomic replacement
if targetZip.exists():
    targetZip.unlink()
tempZip.rename(targetZip)

stat = targetZip.stat()
print("\n" + "=" * 70)
print(f"[OK] Pacchetto compresso generato con successo:")
print(f"  Percorso: {targetZip}")
print(f"  Dimensione: {stat.st_size / (1024*1024):.2f} MB ({stat.st_size} bytes)")
print("=" * 70)
