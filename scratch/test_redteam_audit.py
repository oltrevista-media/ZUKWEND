#!/usr/bin/env python3
"""
================================================================================
ZUKWEND v2.1.0 — RED TEAM AUDIT & STRESS-TEST SUITE
Destinatario: Antigravity / Flash (Red-Team Audit & Quality Assurance)
Progetto: REPO_TARGET (ZUKWEND_repo)
File: PATH_TEST = scratch/test_redteam_audit.py
================================================================================
"""

import os
import sys
import json
import tempfile
import traceback
from datetime import datetime, date, timedelta
from pathlib import Path

# Setup paths to import ZUKWEND modules
CURRENT_DIR = Path(__file__).resolve().parent

# Check potential directories containing the ZUKWEND core modules
search_paths = [
    CURRENT_DIR.parent,
    CURRENT_DIR.parent / "ZUKWEND_repo",
    CURRENT_DIR.parent / "02_VERTICALI" / "ZUKWEND" / "FULL",
    CURRENT_DIR.parent.parent / "02_VERTICALI" / "ZUKWEND" / "FULL",
    Path(r"c:\OLTREVISTA_AI\02_VERTICALI\ZUKWEND\FULL"),
    Path(r"c:\OLTREVISTA_AI\ZUKWEND_repo"),
]
for p in search_paths:
    p_str = str(p.resolve()) if hasattr(p, "resolve") else str(p)
    if os.path.exists(p_str) and p_str not in sys.path:
        sys.path.insert(0, p_str)

import parser
import normalizer
import classifier
import deducer
import license_manager
import workflow_engine

class RedTeamTestRunner:
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.results = []

    def record_test(self, test_id: str, description: str, passed: bool, detail: str = ""):
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status_str = "[PASS]"
        else:
            self.failed_tests += 1
            status_str = "[FAIL]"
        
        entry = {
            "id": test_id,
            "description": description,
            "status": "PASS" if passed else "FAIL",
            "detail": detail
        }
        self.results.append(entry)
        print(f"  {status_str} {test_id}: {description}")
        if detail and not passed:
            print(f"         Dettaglio: {detail}")

    def run_all(self):
        print("=" * 75)
        print("   ZUKWEND v2.1.0 — RED TEAM AUDIT & AUTOMATED STRESS-TEST")
        print("=" * 75)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Target: REPO_TARGET (ZUKWEND_repo)")
        print(f"Modules loaded from: {getattr(workflow_engine, '__file__', 'unknown')}")
        print("-" * 75)

        self.test_1_corrupted_empty_pdfs()
        self.test_2_special_chars_and_currencies()
        self.test_3_graceful_fallback()
        self.test_4_license_tampering_and_hardware_binding()

        print("\n" + "=" * 75)
        print(f"   ESITO COMPLESSIVO RED-TEAM AUDIT: {self.passed_tests} / {self.total_tests} SUPERATI")
        print("=" * 75)
        if self.failed_tests == 0:
            print("[CONFERMA] 100% RED-TEAM SAFE — NESSUN VETTORE DI CRASH RILEVATO.")
            return 0
        else:
            print(f"[ATTENZIONE] RILEVATI {self.failed_tests} ERRORI / REGRESSIONI.")
            return 1

    # -------------------------------------------------------------------------
    # SEZIONE 1: Handling PDF Corrotti / Vuoti
    # -------------------------------------------------------------------------
    def test_1_corrupted_empty_pdfs(self):
        print("\n[TEST SECTION 1] LEVEL 1 NATIVE ENGINE — HANDLING PDF CORROTTI / VUOTI")

        # 1.1 File a 0 byte
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f0:
            f0_path = f0.name
        try:
            res_p = parser.parse_invoice_from_path(f0_path)
            p_ok = res_p.get("requires_manual_input") is True and "error" in res_p
            self.record_test(
                "SEC-1.1",
                "PDF 0-byte (vuoto) — Parser restituisce requires_manual_input gestito",
                p_ok,
                f"res={res_p}"
            )

            res_wf = workflow_engine.run_pipeline(f0_path, mode="local")
            wf_ok = (not res_wf.success) and any(e.get("step") == "PARSE" for e in res_wf.errors)
            self.record_test(
                "SEC-1.2",
                "PDF 0-byte (vuoto) — Pipeline completa senza eccezioni non gestite",
                wf_ok,
                f"success={res_wf.success}, errors={res_wf.errors}"
            )
        except Exception as e:
            self.record_test("SEC-1.1", "PDF 0-byte (vuoto) — Crash inatteso", False, traceback.format_exc())
        finally:
            if os.path.exists(f0_path):
                os.unlink(f0_path)

        # 1.2 Header corrotto (non-PDF)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f1:
            f1.write(b"GARBAGE_HEADER_CORRUPTED_NOT_PDF_CONTENT_XYZ")
            f1_path = f1.name
        try:
            res_p = parser.parse_invoice_from_path(f1_path)
            p_ok = res_p.get("requires_manual_input") is True and "error" in res_p
            self.record_test(
                "SEC-1.3",
                "PDF Header Corrotto — Parser gestisce il fallimento senza crash",
                p_ok,
                f"res={res_p}"
            )

            res_wf = workflow_engine.run_pipeline(f1_path, mode="local")
            wf_ok = (not res_wf.success) and any(e.get("step") == "PARSE" for e in res_wf.errors)
            self.record_test(
                "SEC-1.4",
                "PDF Header Corrotto — Pipeline resiste senza eccezioni non gestite",
                wf_ok,
                f"success={res_wf.success}, errors={res_wf.errors}"
            )
        except Exception as e:
            self.record_test("SEC-1.3", "PDF Header Corrotto — Crash inatteso", False, traceback.format_exc())
        finally:
            if os.path.exists(f1_path):
                os.unlink(f1_path)

        # 1.3 PDF Troncato
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f2:
            f2.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\n")
            f2_path = f2.name
        try:
            res_p = parser.parse_invoice_from_path(f2_path)
            p_ok = res_p.get("requires_manual_input") is True and "error" in res_p
            self.record_test(
                "SEC-1.5",
                "PDF Troncato a meta' — Parser gestisce EOF inatteso senza eccezioni",
                p_ok,
                f"res={res_p}"
            )

            res_wf = workflow_engine.run_pipeline(f2_path, mode="local")
            wf_ok = (not res_wf.success) and any(e.get("step") == "PARSE" for e in res_wf.errors)
            self.record_test(
                "SEC-1.6",
                "PDF Troncato a meta' — Pipeline produce fallback parziale senza crash",
                wf_ok,
                f"success={res_wf.success}, errors={res_wf.errors}"
            )
        except Exception as e:
            self.record_test("SEC-1.5", "PDF Troncato — Crash inatteso", False, traceback.format_exc())
        finally:
            if os.path.exists(f2_path):
                os.unlink(f2_path)

    # -------------------------------------------------------------------------
    # SEZIONE 2: Parsing Caratteri Speciali & Importi
    # -------------------------------------------------------------------------
    def test_2_special_chars_and_currencies(self):
        print("\n[TEST SECTION 2] LEVEL 1 NATIVE ENGINE — CARATTERI SPECIALI, VALUTE E DATE")

        # 2.1 Lettere accentate e nomi internazionali
        names = [
            ("société générale sa", "Société Générale SA"),
            ("são paulo logística srl", "São Paulo Logística Srl"),
            ("müller & söhne gmbh", "Müller & Söhne GmbH"),
            ("caffè & pasticceria snc", "Caffè & Pasticceria SNC"),
        ]
        all_names_ok = True
        for raw_n, expected_n in names:
            norm_n = normalizer.normalize_name(raw_n)
            if not norm_n or norm_n != expected_n:
                all_names_ok = False
                break
        self.record_test(
            "SEC-2.1",
            "Lettere accentate nei nomi (é, ã, ü, è) — Preservazione e capitalizzazione corretta",
            all_names_ok,
            f"test names={names}"
        )

        # 2.2 Simboli di valuta ($; £; ¥; CHF)
        currencies_to_test = [
            ("$", "USD"),
            ("£", "GBP"),
            ("¥", "JPY"),
            ("CHF", "CHF"),
            ("€", "EUR"),
        ]
        all_cur_ok = True
        for sym, expected_iso in currencies_to_test:
            res_iso = normalizer.normalize_currency(sym)
            if res_iso != expected_iso:
                all_cur_ok = False
                break
        self.record_test(
            "SEC-2.2",
            "Simboli di valuta ($; £; ¥; CHF; €) mappati a codici ISO corretti",
            all_cur_ok,
            f"currencies={currencies_to_test}"
        )

        # 2.3 Importi con valute e formati diversi
        amounts_to_test = [
            ("$ 3,450.00", 3450.0),
            ("£ 890.20", 890.2),
            ("¥ 50000", 50000.0),
            ("¥ 50.000", 50000.0),
            ("CHF 1 200.50", 1200.5),
            ("CHF 1.200,50", 1200.5),
            ("1.250,50 €", 1250.5),
        ]
        all_amt_ok = True
        for amt_str, expected_val in amounts_to_test:
            parsed_val = normalizer.normalize_amount(amt_str)
            if parsed_val != expected_val:
                all_amt_ok = False
                print(f"             Mismatch amount: {amt_str} -> {parsed_val} (atteso: {expected_val})")
                break
        self.record_test(
            "SEC-2.3",
            "Parsing importi complessi con simboli valuta ($; £; ¥; CHF) e separatori misti",
            all_amt_ok,
            f"amounts={amounts_to_test}"
        )

        # 2.4 Formati data anomali (YYYY-DD-MM, spazi extra)
        dates_to_test = [
            ("2026-28-02", "2026-02-28"),  # YYYY-DD-MM anomalo
            ("2026/28/02", "2026-02-28"),  # YYYY/DD/MM anomalo
            ("  2026-05-15  ", "2026-05-15"), # Spazi extra inizio/fine
            ("15 / 05 / 2026", "2026-05-15"), # Spazi intorno ai separatori
            ("2026 - 10 - 25", "2026-10-25"), # Spazi ISO
        ]
        all_dates_ok = True
        for raw_d, expected_d in dates_to_test:
            norm_d = normalizer.normalize_date(raw_d)
            if norm_d != expected_d:
                all_dates_ok = False
                print(f"             Mismatch date: '{raw_d}' -> '{norm_d}' (atteso: '{expected_d}')")
                break
        self.record_test(
            "SEC-2.4",
            "Normalizzazione date anomale (YYYY-DD-MM e spazi extra) a ISO standard",
            all_dates_ok,
            f"dates={dates_to_test}"
        )

        # 2.5 Classifier supporta date anomale
        clf_date = classifier._parse_date("2026-28-02")
        self.record_test(
            "SEC-2.5",
            "Classifier _parse_date interpreta correttamente la data anomala 2026-28-02",
            clf_date == date(2026, 2, 28),
            f"parsed={clf_date}"
        )

    # -------------------------------------------------------------------------
    # SEZIONE 3: Fallback Graceful & Manual Fields
    # -------------------------------------------------------------------------
    def test_3_graceful_fallback(self):
        print("\n[TEST SECTION 3] LEVEL 1 NATIVE ENGINE — FALLBACK GRACEFUL")

        # 3.1 Estrazione fallita restituisce flag requires_manual_input
        dummy_bad_text = "Fattura illeggibile senza importo né data"
        fields = parser._fallback_regex_extraction(dummy_bad_text)
        self.record_test(
            "SEC-3.1",
            "Fallimento estrazione Regex segnala requires_manual_input=True senza bloccare",
            fields.get("requires_manual_input") is True,
            f"fields={fields}"
        )

        # 3.2 Tutti i campi restano presenti per modifica manuale
        expected_keys = ["invoice_number", "amount", "currency", "due_date", "client_name", "vendor_name"]
        has_all_keys = all(k in fields for k in expected_keys)
        self.record_test(
            "SEC-3.2",
            "Campi chiave presenti e pronti per input manuale utente",
            has_all_keys,
            f"keys={list(fields.keys())}"
        )

        # 3.3 Reminder statico sicuro al 100% con campi vuoti o None
        try:
            empty_invoice = {
                "invoice_number": None,
                "amount": None,
                "currency": None,
                "client_name": None,
                "vendor_name": None,
                "due_date": None,
            }
            billing_dummy = {"reminder_level": 1, "grace_days": 5}
            rem_text = workflow_engine._static_reminder(empty_invoice, billing_dummy, "it")
            rem_ok = "0.00" in rem_text and "Gentile" in rem_text
            self.record_test(
                "SEC-3.3",
                "Workflow Engine: _static_reminder gestisce amount=None senza TypeError",
                rem_ok,
                f"rem_text snippet: {rem_text[:60]}..."
            )
        except Exception as e:
            self.record_test("SEC-3.3", "Workflow Engine: _static_reminder crash con amount=None", False, traceback.format_exc())

    # -------------------------------------------------------------------------
    # SEZIONE 4: Audit License Manager & Hardware Binding
    # -------------------------------------------------------------------------
    def test_4_license_tampering_and_hardware_binding(self):
        print("\n[TEST SECTION 4] AUDIT LICENSE MANAGER & HARDWARE BINDING")

        app_dir = license_manager._get_app_dir()
        lic_file = app_dir / "license.key"
        lock_file = app_dir / "demo.lock"

        # Backup existing license and lock files
        backup_lic = lic_file.read_text(encoding="utf-8") if lic_file.exists() else None
        backup_lock = lock_file.read_text(encoding="utf-8") if lock_file.exists() else None

        try:
            # 4.1 Licenza FULL con firma alterata / manomessa
            lic_file.write_text(json.dumps({
                "payload": {"machine_id": license_manager.get_machine_id(), "type": "FULL"},
                "signature": "TAMPERED_INVALID_SIGNATURE_HEX_0000"
            }), encoding="utf-8")

            lm = license_manager.LicenseManager()
            val_tampered = lm._validate_full_license()
            self.record_test(
                "SEC-4.1",
                "Licenza FULL con firma manomessa viene bloccata (is_valid=False)",
                val_tampered.get("is_valid") is False and val_tampered.get("license_type") == "INVALID",
                f"res={val_tampered}"
            )

            # 4.2 Licenza FULL con Hardware ID non corrispondente
            fake_hwid = "DIFFERENT_MACHINE_HWID_999999"
            payload_fake = {
                "license_code": "ZKW-TEST-DIFF-HWID",
                "machine_id": fake_hwid,
                "activated_at": datetime.now().isoformat(),
                "product": "ZUKWEND",
                "version": "1",
                "type": "FULL"
            }
            payload_str = json.dumps(payload_fake, sort_keys=True)
            valid_sig_for_fake = license_manager._sign(payload_str)
            lic_file.write_text(json.dumps({
                "payload": payload_fake,
                "signature": valid_sig_for_fake
            }), encoding="utf-8")

            val_hwid = lm._validate_full_license()
            self.record_test(
                "SEC-4.2",
                "Licenza valida ma trasferita su hardware differente viene respinta",
                val_hwid.get("is_valid") is False and "questa macchina" in val_hwid.get("message", ""),
                f"res={val_hwid}"
            )

            # 4.3 Tentativo attivazione con codice associato ad altro Hardware ID
            code_other_machine = license_manager.generate_license_code_for_machine("OTHER_HWID_12345678")
            act_res = lm.activate(code_other_machine)
            self.record_test(
                "SEC-4.3",
                "Attivazione con License Key calcolata per altra macchina viene bloccata",
                act_res.get("success") is False and act_res.get("license_type") == "INVALID",
                f"res={act_res}"
            )

            # 4.4 Demo Lock con firma manomessa
            if lic_file.exists():
                lic_file.unlink()  # Rimuovi temporaneamente FULL per testare demo lock

            lock_file.write_text(json.dumps({
                "payload": {
                    "machine_id": license_manager.get_machine_id(),
                    "first_run": datetime.now().isoformat(),
                    "invoice_count": 0
                },
                "signature": "BAD_SIGNATURE_TAMPERED"
            }), encoding="utf-8")

            demo_tampered = lm._demo_manager.get_status()
            self.record_test(
                "SEC-4.4",
                "Demo Lock manomesso (firma alterata) transiziona in stato INVALID",
                demo_tampered.get("is_valid") is False and demo_tampered.get("license_type") == "INVALID",
                f"res={demo_tampered}"
            )

            # 4.5 Demo Scaduta per superamento 7 giorni
            past_date = (datetime.now() - timedelta(days=10)).isoformat()
            payload_exp_days = {
                "first_run": past_date,
                "machine_id": license_manager.get_machine_id(),
                "demo_days": 7,
                "invoice_count": 0,
                "max_invoices": 10,
                "version": "1",
                "product": "ZUKWEND",
                "created_at": past_date,
            }
            payload_str = json.dumps(payload_exp_days, sort_keys=True)
            sig_exp_days = license_manager._sign(payload_str)
            lock_file.write_text(json.dumps({
                "payload": payload_exp_days,
                "signature": sig_exp_days
            }), encoding="utf-8")

            status_exp_days = lm.get_status()
            self.record_test(
                "SEC-4.5",
                "Demo con timer oltre 7 giorni transiziona in EXPIRED (accesso bloccato)",
                status_exp_days.get("license_type") == "EXPIRED" and status_exp_days.get("is_valid") is False,
                f"res={status_exp_days}"
            )

            # 4.6 Demo Scaduta per raggiungimento tetto 10 fatture
            payload_exp_cnt = {
                "first_run": datetime.now().isoformat(),
                "machine_id": license_manager.get_machine_id(),
                "demo_days": 7,
                "invoice_count": 10,
                "max_invoices": 10,
                "version": "1",
                "product": "ZUKWEND",
                "created_at": datetime.now().isoformat(),
            }
            payload_str = json.dumps(payload_exp_cnt, sort_keys=True)
            sig_exp_cnt = license_manager._sign(payload_str)
            lock_file.write_text(json.dumps({
                "payload": payload_exp_cnt,
                "signature": sig_exp_cnt
            }), encoding="utf-8")

            status_exp_cnt = lm.get_status()
            self.record_test(
                "SEC-4.6",
                "Demo con tetto fatture raggiunto (10/10) transiziona in EXPIRED",
                status_exp_cnt.get("license_type") == "EXPIRED" and status_exp_cnt.get("is_valid") is False,
                f"res={status_exp_cnt}"
            )

            # 4.7 Blocco pipeline quando la licenza e' scaduta
            res_blocked = workflow_engine.run_pipeline("any.pdf")
            blocked_ok = (not res_blocked.success) and any(e.get("step") == "LICENSE" for e in res_blocked.errors)
            self.record_test(
                "SEC-4.7",
                "Workflow Engine gate blocca pipeline su licenza non valida senza eccezioni",
                blocked_ok,
                f"errors={res_blocked.errors}"
            )

        finally:
            # Restore initial license and lock files
            if backup_lic is not None:
                lic_file.write_text(backup_lic, encoding="utf-8")
            elif lic_file.exists():
                lic_file.unlink()

            if backup_lock is not None:
                lock_file.write_text(backup_lock, encoding="utf-8")
            elif lock_file.exists():
                lock_file.unlink()

if __name__ == "__main__":
    runner = RedTeamTestRunner()
    exit_code = runner.run_all()
    sys.exit(exit_code)
