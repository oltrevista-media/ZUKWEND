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

def test_b1_aging_buckets():
    print("\n---> Running B1: Strict Aging Buckets Verification...")
    from i18n_catalog import get_aging_bucket
    assert get_aging_bucket(0) == "Current / Not Due"
    assert get_aging_bucket(-10) == "Current / Not Due"
    assert get_aging_bucket(1) == "0-30 Days"
    assert get_aging_bucket(15) == "0-30 Days"
    assert get_aging_bucket(30) == "0-30 Days"
    assert get_aging_bucket(31) == "31-60 Days"
    assert get_aging_bucket(60) == "31-60 Days"
    assert get_aging_bucket(61) == "61-90 Days"
    assert get_aging_bucket(90) == "61-90 Days"
    assert get_aging_bucket(91) == "90+ Days (Critical)"
    assert get_aging_bucket(120) == "90+ Days (Critical)"
    print("  [PASS] All Aging Buckets strictly match specification.")

def test_b2_amounts():
    print("\n---> Running B2: Amount <= 0 and Non-Numeric Sanitization Verification...")
    import classifier
    import deducer

    # 1. Zero amount
    r_zero_es = classifier.classify({"amount": 0, "due_date": "2026-05-01"}, language="es")
    assert r_zero_es["payment_status"] == "SETTLED"
    assert r_zero_es["action"] == "NO_REMINDER_NEEDED"
    assert r_zero_es["status_label"] == "Factura Pagada / Settled"
    assert r_zero_es["reminder_level"] == 0

    d_zero = deducer.deduce({"amount": 0.0}, r_zero_es, language="es")
    assert d_zero["action"] == "NO_REMINDER_NEEDED"
    assert d_zero["reminder_level"] == 0
    t_zero = deducer.generate_reminder_text({"amount": 0.0}, d_zero, language="es", classification=r_zero_es)
    assert t_zero == ""

    # 2. Negative amount (Credit note)
    r_neg_es = classifier.classify({"amount": -250.0, "due_date": "2026-05-01"}, language="es")
    assert r_neg_es["payment_status"] == "CREDIT_NOTE"
    assert r_neg_es["action"] == "NO_REMINDER_NEEDED"
    assert r_neg_es["status_label"] == "Nota de Crédito / Credit Note"
    assert r_neg_es["reminder_level"] == 0

    d_neg = deducer.deduce({"amount": -250.0}, r_neg_es, language="es")
    assert d_neg["action"] == "NO_REMINDER_NEEDED"
    assert d_neg["reminder_level"] == 0
    t_neg = deducer.generate_reminder_text({"amount": -250.0}, d_neg, language="es", classification=r_neg_es)
    assert t_neg == ""

    # 3. Non-numeric and None amounts
    r_none = classifier.classify({"amount": None, "due_date": "2026-05-01"}, language="en")
    assert r_none["payment_status"] == "SETTLED"
    assert r_none["action"] == "NO_REMINDER_NEEDED"

    r_str = classifier.classify({"amount": "invalid_amt", "due_date": "2026-05-01"}, language="en")
    assert r_str["payment_status"] == "SETTLED"
    assert "invalid_amount_format" in r_str["errors"]

    print("  [PASS] Amount <= 0 and non-numeric sanitization verified.")

def test_m1_parse_failure():
    print("\n---> Running M1: Parse Error Handling & Zero Output Pollution Verification...")
    import tempfile
    out_dir = REPO_DIR / "output"
    files_before = set(out_dir.glob("**/*"))

    # Create dummy corrupt file
    corrupt_file = REPO_DIR / "corrupt_test_doc.pdf"
    corrupt_file.write_bytes(b"NOT_A_VALID_PDF_STREAM")

    try:
        res = workflow_engine.run_pipeline(
            pdf_path=str(corrupt_file),
            language="en",
            mode="local",
            is_demo=False
        )
        assert not res.success, "Pipeline should report success=False on corrupt PDF"
        assert len(res.errors) > 0, "Errors should contain parse failure details"
        assert res.report_path is None, "No report should be generated"
        assert len(res.export_paths) == 0, "No files should be exported"

        # Check output directory has not received any report_AR_UNKNOWN files
        unknown_reports = list(out_dir.glob("**/report_AR_UNKNOWN*"))
        assert len(unknown_reports) == 0, f"Output directory polluted with unknown reports: {unknown_reports}"

        print("  [PASS] Parse error handled without polluting output directory.")
    finally:
        if corrupt_file.exists():
            corrupt_file.unlink()

def test_e2e_negative_credit_note():
    print("\n---> Running E2E Negative Credit Note PDF Verification...")
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    test_pdf_path = REPO_DIR / "test_credit_note_sample.pdf"
    c = canvas.Canvas(str(test_pdf_path), pagesize=letter)
    c.drawString(100, 750, "CREDIT NOTE")
    c.drawString(100, 720, "Document Number: CN-2026-999")
    c.drawString(100, 690, "Issue Date: 2026-05-10")
    c.drawString(100, 660, "Due Date: 2026-06-10")
    c.drawString(100, 630, "Client: Acme Corporation Ltd.")
    c.drawString(100, 600, "Total Amount: EUR -500.00")
    c.save()

    try:
        res = workflow_engine.run_pipeline(
            pdf_path=str(test_pdf_path),
            language="en",
            mode="local",
            is_demo=False
        )
        assert res.success, f"Pipeline execution failed for credit note: {res.errors}"

        # a. amount estratto sia == -500.00
        extracted_amount = float(res.invoice.get("amount", 0.0))
        assert extracted_amount == -500.00, f"Expected amount -500.00, got {extracted_amount}"

        # b. payment_status sia 'CREDIT_NOTE'
        clf_status = res.classification.get("payment_status")
        assert clf_status == "CREDIT_NOTE", f"Expected payment_status CREDIT_NOTE, got {clf_status}"

        # c. action sia 'NO_REMINDER_NEEDED'
        billing_action = res.billing.get("action")
        assert billing_action == "NO_REMINDER_NEEDED", f"Expected action NO_REMINDER_NEEDED, got {billing_action}"

        # d. reminder_level sia 0
        rem_level = res.classification.get("reminder_level")
        assert rem_level == 0, f"Expected classification reminder_level 0, got {rem_level}"
        b_rem_level = res.billing.get("reminder_level")
        assert b_rem_level == 0, f"Expected billing reminder_level 0, got {b_rem_level}"

        # Check generated JSON export as well
        json_path = None
        for p in res.export_paths:
            if p.endswith(".json"):
                json_path = Path(p)
                break
        assert json_path and json_path.exists(), "Exported JSON report not found"
        with open(json_path, "r", encoding="utf-8") as f:
            jdata = json.load(f)
        assert jdata["classification"]["reminder_level"] == 0, f"JSON reminder_level not 0: {jdata['classification']['reminder_level']}"
        assert jdata["invoice"]["amount"] == -500.00
        assert jdata["billing"]["action"] == "NO_REMINDER_NEEDED"

        print("  [PASS] E2E Negative Credit Note PDF verified successfully:")
        print(f"         - Amount: {extracted_amount}")
        print(f"         - Payment Status: {clf_status}")
        print(f"         - Action: {billing_action}")
        print(f"         - Reminder Level: {rem_level}")
    finally:
        if test_pdf_path.exists():
            test_pdf_path.unlink()

def cleanup_output_folder():
    import shutil
    for d in [REPO_DIR / "output", Path("C:/OLTREVISTA_AI/output")]:
        if d.exists():
            for item in d.iterdir():
                if item.name == ".gitkeep":
                    continue
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    try:
                        item.unlink()
                    except Exception:
                        pass

if __name__ == "__main__":
    test_b1_aging_buckets()
    test_b2_amounts()
    test_m1_parse_failure()
    test_e2e_negative_credit_note()
    run_multilingual_test()
    cleanup_output_folder()
