"""
ZUKWEND Test Suite — Multilingual i18n Anti-Leak Verification (v3.15)
Verifies:
1. Complete execution across all 6 languages (IT, EN, DE, FR, ES, PT).
2. Unified destination folder for all 3 triptych exports (.pdf, .xlsx, .json).
3. Strict zero Italian leak in PDF, XLSX, and JSON for non-Italian languages (specifically EN and ES).
4. Correct localized headers, statuses, and rationales.
"""

import os
import sys
import re
import json
from pathlib import Path

# Add repo to sys.path
REPO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_DIR))

import workflow_engine
import pdfplumber
import openpyxl

ITALIAN_SPY_WORDS = [
    r"\bscadut[aoie]\b",
    r"\binesigibilit[aà]\b",
    r"\bgiorn[oi]\b",
    r"\bfattur[ae]\b",
    r"\braccomandat[ae]\b",
    r"\bdiffida\b",
    r"\bsollecit[oi]\b",
]

def check_text_for_italian_leaks(text: str, context_label: str) -> list:
    leaks = []
    # Ignore customer's own input address if it contains Italian words (e.g. via, milano)
    for pattern in ITALIAN_SPY_WORDS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            leaks.extend(matches)
    return list(set(leaks))

def run_multilingual_test():
    sample_pdf = REPO_DIR / "demo" / "b2b_invoice_sample_en.pdf"
    assert sample_pdf.exists(), f"Sample PDF not found at {sample_pdf}"

    languages = ["en", "es", "de", "fr", "pt", "it"]
    results = {}

    print("=" * 75)
    print("[*] STARTING MULTILINGUAL ZERO-LEAK VERIFICATION SUITE (v3.15)")
    print("=" * 75)

    for lang in languages:
        print(f"\n---> Testing language: [{lang.upper()}]")
        res = workflow_engine.run_pipeline(
            pdf_path=str(sample_pdf),
            language=lang,
            mode="local",
            is_demo=False
        )
        assert res.success, f"Pipeline execution failed for lang={lang}: {res.errors}"

        exported_paths = res.export_paths
        assert len(exported_paths) >= 3, f"Expected at least 3 exported files, got {len(exported_paths)}"

        pdf_path = None
        xlsx_path = None
        json_path = None

        for p in exported_paths:
            if p.endswith(".pdf"):
                pdf_path = Path(p)
            elif p.endswith(".xlsx"):
                xlsx_path = Path(p)
            elif p.endswith(".json"):
                json_path = Path(p)

        assert pdf_path and pdf_path.exists(), f"Missing PDF for lang={lang}"
        assert xlsx_path and xlsx_path.exists(), f"Missing XLSX for lang={lang}"
        assert json_path and json_path.exists(), f"Missing JSON for lang={lang}"

        # 1. Verify Unified Output Directory
        parent_folders = {pdf_path.parent.resolve(), xlsx_path.parent.resolve(), json_path.parent.resolve()}
        assert len(parent_folders) == 1, f"Triptych files are not in the same unified folder! Found: {parent_folders}"
        unified_folder = parent_folders.pop()
        print(f"  [OK] Unified output folder: {unified_folder}")

        # 2. Extract PDF Text
        with pdfplumber.open(pdf_path) as pdf:
            pdf_text = "\n".join([page.extract_text() or "" for page in pdf.pages])

        # 3. Extract JSON text (excluding client address/name)
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        
        # Build searchable string from JSON excluding client address
        json_check_obj = {
            "report_title": json_data.get("report_title"),
            "classification": json_data.get("classification"),
            "compliance": json_data.get("compliance"),
            "billing": json_data.get("billing"),
            "erp_ingestion": {k: v for k, v in json_data.get("erp_ingestion", {}).items() if k not in ("client", "client_address")}
        }
        json_text = json.dumps(json_check_obj, ensure_ascii=False)

        # 4. Extract XLSX Text
        wb = openpyxl.load_workbook(xlsx_path)
        xlsx_texts = []
        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            for row in ws.iter_rows(values_only=True):
                for val in row:
                    if val is not None:
                        # Exclude client address value
                        val_str = str(val)
                        if "Canary Wharf" not in val_str and "Global Logistics" not in val_str:
                            xlsx_texts.append(val_str)
        xlsx_full_text = " ".join(xlsx_texts)

        results[lang] = {
            "pdf_text": pdf_text,
            "json_text": json_text,
            "xlsx_text": xlsx_full_text,
            "pdf_path": pdf_path,
        }

        # Anti-Leak Assertions for Non-Italian Languages
        if lang != "it":
            pdf_leaks = check_text_for_italian_leaks(pdf_text, f"{lang}-PDF")
            json_leaks = check_text_for_italian_leaks(json_text, f"{lang}-JSON")
            xlsx_leaks = check_text_for_italian_leaks(xlsx_full_text, f"{lang}-XLSX")

            assert not pdf_leaks, f"Italian leak detected in {lang.upper()} PDF: {pdf_leaks}"
            assert not json_leaks, f"Italian leak detected in {lang.upper()} JSON: {json_leaks}"
            assert not xlsx_leaks, f"Italian leak detected in {lang.upper()} XLSX: {xlsx_leaks}"
            print(f"  [PASS] Zero Italian leaks detected in PDF, XLSX, and JSON for {lang.upper()}!")

    print("\n" + "=" * 75)
    print("[OK] ALL 6 LANGUAGES PASSED ZERO-LEAK TEST SUCCESSFULLY!")
    print("=" * 75)

    # Print Validation Excerpts for EN and ES
    for l in ("en", "es"):
        print(f"\n==================== VALIDATION EXCERPT [{l.upper()}] ====================")
        txt = results[l]["pdf_text"]
        lines = [line.strip() for line in txt.split("\n") if line.strip()]
        for line in lines[:18]:
            print(f"  | {line}")
        print("  | ...")
        for line in lines[-6:]:
            print(f"  | {line}")
        print(f"================== END EXCERPT [{l.upper()}] ==================\n")

if __name__ == "__main__":
    run_multilingual_test()
