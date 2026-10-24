"""
ZUKWEND Enterprise Clean Release Packaging v2.1.5
Compliant with ORDINE OPERATIVO ANTIGRAVITY — MASTER CLEANUP & CODE SIGNING v2.1.5
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

ZIP_FILENAME = "ZUKWEND_FULL_v2_1_5_Setup.zip"
TARGET_ZIP = DIST_DIR / ZIP_FILENAME
TEMP_ZIP = DIST_DIR / (ZIP_FILENAME + ".tmp")

DIST_ZUKWEND = DIST_DIR / "ZUKWEND"

print("=" * 70)
print(f"[*] RELEASE PACKAGING v2.1.5 started at: {datetime.now()}")
print(f"[*] Target ZIP: {TARGET_ZIP}")
print("=" * 70)

if TEMP_ZIP.exists():
    TEMP_ZIP.unlink()

with zipfile.ZipFile(TEMP_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    # 1. ZUKWEND.exe (signed)
    exe_path = DIST_ZUKWEND / "ZUKWEND.exe"
    assert exe_path.exists(), f"Missing {exe_path}"
    print(f"  [+] Adding {exe_path.name} ({exe_path.stat().st_size / (1024*1024):.2f} MB)...")
    zf.write(exe_path, "ZUKWEND.exe")

    # 2. INSTALLATION_GUIDE.txt
    guide_path = REPO_DIR / "INSTALLATION_GUIDE.txt"
    assert guide_path.exists(), f"Missing {guide_path}"
    print(f"  [+] Adding {guide_path.name}...")
    zf.write(guide_path, "INSTALLATION_GUIDE.txt")

    # 2b. USER_MANUAL_EN.pdf
    manual_path = REPO_DIR / "USER_MANUAL_EN.pdf"
    if manual_path.exists():
        print(f"  [+] Adding {manual_path.name}...")
        zf.write(manual_path, "USER_MANUAL_EN.pdf")

    # 3. LICENSE_EULA.txt
    eula_path = REPO_DIR / "LICENSE_EULA.txt"
    assert eula_path.exists(), f"Missing {eula_path}"
    print(f"  [+] Adding {eula_path.name}...")
    zf.write(eula_path, "LICENSE_EULA.txt")

    # 4. zukwend_config.json
    cfg_path = REPO_DIR / "zukwend_config.json"
    assert cfg_path.exists(), f"Missing {cfg_path}"
    print(f"  [+] Adding {cfg_path.name}...")
    zf.write(cfg_path, "zukwend_config.json")

    # 5. demo/
    demo_dir = REPO_DIR / "demo"
    assert demo_dir.exists(), f"Missing {demo_dir}"
    print("  [+] Adding demo/...")
    zf.writestr("demo/", "")
    for root, dirs, files in os.walk(demo_dir):
        for f in files:
            fpath = Path(root) / f
            arcname = "demo/" + str(fpath.relative_to(demo_dir)).replace("\\", "/")
            zf.write(fpath, arcname)
            print(f"      Included {arcname}")

    # 6. output/ (.gitkeep)
    gitkeep_path = REPO_DIR / "output" / ".gitkeep"
    if not gitkeep_path.exists():
        gitkeep_path.parent.mkdir(parents=True, exist_ok=True)
        gitkeep_path.touch()
    print("  [+] Adding output/.gitkeep...")
    zf.writestr("output/", "")
    zf.write(gitkeep_path, "output/.gitkeep")

    # 7. prompts/
    prompts_dir = REPO_DIR / "prompts"
    assert prompts_dir.exists(), f"Missing {prompts_dir}"
    print("  [+] Adding prompts/...")
    zf.writestr("prompts/", "")
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

    # 8. _internal/
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

# Sincronizza anche in 02_VERTICALI/ZUKWEND/FULL se presente
shutil.copy2(exe_path, DIST_DIR / "ZUKWEND.exe")
print(f"[+] Eseguibile firmato copiato in: {DIST_DIR / 'ZUKWEND.exe'}")

if VERTICAL_DIR.exists():
    vert_target = VERTICAL_DIR / ZIP_FILENAME
    shutil.copy2(TARGET_ZIP, vert_target)
    print(f"[+] Pacchetto sincronizzato anche in: {vert_target}")
    shutil.copy2(exe_path, VERTICAL_DIR / "ZUKWEND.exe")
    print(f"[+] Eseguibile firmato sincronizzato anche in: {VERTICAL_DIR / 'ZUKWEND.exe'}")
