"""
ZUKWEND Enterprise Clean Release Packaging v2.1.4
Packages the production build into ZUKWEND_FULL_v2_1_4_Setup.zip
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("C:/OLTREVISTA_AI")
REPO_DIR = ROOT_DIR / "ZUKWEND_repo"
DIST_DIR = REPO_DIR / "dist"
VERTICAL_DIR = ROOT_DIR / "02_VERTICALI" / "ZUKWEND" / "FULL"

ZIP_FILENAME = "ZUKWEND_FULL_v2_1_4_Setup.zip"
TARGET_ZIP = DIST_DIR / ZIP_FILENAME
TEMP_ZIP = DIST_DIR / (ZIP_FILENAME + ".tmp")

DIST_ZUKWEND = DIST_DIR / "ZUKWEND"

print("=" * 70)
print(f"[*] RELEASE PACKAGING v2.1.4 started at: {datetime.now()}")
print(f"[*] Target ZIP: {TARGET_ZIP}")
print("=" * 70)

if TEMP_ZIP.exists():
    TEMP_ZIP.unlink()

with zipfile.ZipFile(TEMP_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    # 1. ZUKWEND.exe
    exe_path = DIST_ZUKWEND / "ZUKWEND.exe"
    assert exe_path.exists(), f"Missing {exe_path}"
    print(f"  [+] Adding {exe_path.name} ({exe_path.stat().st_size / (1024*1024):.2f} MB)...")
    zf.write(exe_path, "ZUKWEND.exe")

    # 2. _internal/
    internal_dir = DIST_ZUKWEND / "_internal"
    assert internal_dir.exists(), f"Missing {internal_dir}"
    print("  [+] Adding _internal/ tree (filtering out .py, __pycache__, .git)...")
    internal_count = 0
    for root, dirs, files in os.walk(internal_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache", "build", "dist")]
        for f in files:
            if f.endswith(".py") or f.startswith("."):
                continue
            fpath = Path(root) / f
            arcname = "_internal/" + str(fpath.relative_to(internal_dir)).replace("\\", "/")
            zf.write(fpath, arcname)
            internal_count += 1
    print(f"      Included {internal_count} files in _internal/.")

    # 3. prompts/
    prompts_dir = REPO_DIR / "prompts"
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
    gitkeep_path = REPO_DIR / "output" / ".gitkeep"
    if not gitkeep_path.exists():
        gitkeep_path.parent.mkdir(parents=True, exist_ok=True)
        gitkeep_path.touch()
    print("  [+] Adding output/.gitkeep...")
    zf.writestr("output/", "")
    zf.write(gitkeep_path, "output/.gitkeep")

    # 5. zukwend_config.json
    cfg_path = REPO_DIR / "zukwend_config.json"
    assert cfg_path.exists(), f"Missing {cfg_path}"
    print(f"  [+] Adding {cfg_path.name}...")
    zf.write(cfg_path, "zukwend_config.json")

    # 6. b2b_invoice_sample_en.pdf
    sample_pdf = REPO_DIR / "b2b_invoice_sample_en.pdf"
    assert sample_pdf.exists(), f"Missing {sample_pdf}"
    print(f"  [+] Adding {sample_pdf.name}...")
    zf.write(sample_pdf, "b2b_invoice_sample_en.pdf")

    # 7. DISCLAIMER_EULA.md
    eula_path = REPO_DIR / "DISCLAIMER_EULA.md"
    assert eula_path.exists(), f"Missing {eula_path}"
    print(f"  [+] Adding {eula_path.name}...")
    zf.write(eula_path, "DISCLAIMER_EULA.md")

    # 8. README.txt
    readme_path = REPO_DIR / "README.txt"
    assert readme_path.exists(), f"Missing {readme_path}"
    print(f"  [+] Adding {readme_path.name}...")
    zf.write(readme_path, "README.txt")

    # 9. ISTRUZIONI_INSTALLAZIONE_WINDOWS.txt
    istr_path = REPO_DIR / "downloads" / "ISTRUZIONI_INSTALLAZIONE_WINDOWS.txt"
    assert istr_path.exists(), f"Missing {istr_path}"
    print(f"  [+] Adding {istr_path.name}...")
    zf.write(istr_path, "ISTRUZIONI_INSTALLAZIONE_WINDOWS.txt")

    # 10. WINDOWS_INSTALLATION_NOTE.txt
    note_path = REPO_DIR / "downloads" / "WINDOWS_INSTALLATION_NOTE.txt"
    assert note_path.exists(), f"Missing {note_path}"
    print(f"  [+] Adding {note_path.name}...")
    zf.write(note_path, "WINDOWS_INSTALLATION_NOTE.txt")

# Atomic replacement
if TARGET_ZIP.exists():
    TARGET_ZIP.unlink()
TEMP_ZIP.rename(TARGET_ZIP)

stat = TARGET_ZIP.stat()
print("\n" + "=" * 70)
print(f"[OK] Pacchetto compresso generato con successo:")
print(f"  Percorso: {TARGET_ZIP}")
print(f"  Dimensione: {stat.st_size / (1024*1024):.2f} MB ({stat.st_size} bytes)")
print("=" * 70)

# Copia anche in 02_VERTICALI/ZUKWEND/FULL se presente
if VERTICAL_DIR.exists():
    vert_target = VERTICAL_DIR / ZIP_FILENAME
    shutil.copy2(TARGET_ZIP, vert_target)
    print(f"[+] Pacchetto sincronizzato anche in: {vert_target}")
