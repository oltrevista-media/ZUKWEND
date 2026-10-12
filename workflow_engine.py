"""
ZUKWEND — Multilingual Billing Agent
Modulo: workflow_engine.py
Ruolo: Orchestratore principale della pipeline AR (Account Receivable)
Versione: 1.0.3-ENTERPRISE
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).parent
else:
    ROOT_DIR = Path(__file__).parent

LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_filename = LOG_DIR / f"zukwend_workflow_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("zukwend.workflow_engine")

# ---------------------------------------------------------------------------
# Lazy internal module imports
# ---------------------------------------------------------------------------
def _import_module(name: str):
    import importlib
    
    # Check already loaded modules in sys.modules
    if name in sys.modules and sys.modules[name] is not None:
        return sys.modules[name]

    # Registry of direct internal modules
    try:
        if name == "parser":
            import parser as m; return m
        elif name == "normalizer":
            import normalizer as m; return m
        elif name == "classifier":
            import classifier as m; return m
        elif name == "deducer":
            import deducer as m; return m
        elif name == "report_generator":
            import report_generator as m; return m
        elif name == "export_engine":
            import export_engine as m; return m
        elif name == "license_manager":
            import license_manager as m; return m
    except ImportError as e:
        logger.debug(f"Direct import fallback for {name}: {e}")

    candidates = [name, f"core.{name}"]
    for mod_name in candidates:
        try:
            return importlib.import_module(mod_name)
        except ImportError:
            continue
    logger.error(f"Impossibile importare modulo '{name}' (tentativi: {candidates})")
    return None

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
class WorkflowResult:
    def __init__(
        self,
        invoice: dict,
        classification: dict,
        compliance: dict,
        billing: dict,
        reminder_text: str,
        report_path: Optional[str],
        export_paths: list,
        audit_log: list,
        success: bool,
        errors: list,
    ):
        self.invoice = invoice
        self.classification = classification
        self.compliance = compliance
        self.billing = billing
        self.reminder_text = reminder_text
        self.report_path = report_path
        self.export_paths = export_paths
        self.audit_log = audit_log
        self.success = success
        self.errors = errors
        self.generated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "invoice": self.invoice,
            "classification": self.classification,
            "compliance": self.compliance,
            "billing": self.billing,
            "reminder_text": self.reminder_text,
            "report_path": self.report_path,
            "export_paths": self.export_paths,
            "audit_log": self.audit_log,
            "success": self.success,
            "errors": self.errors,
            "generated_at": self.generated_at,
        }

ERR_PARSE        = "PARSE_ERROR"
ERR_NORMALIZE    = "NORMALIZE_ERROR"
ERR_CLASSIFY     = "CLASSIFY_ERROR"
ERR_COMPLIANCE   = "COMPLIANCE_ERROR"
ERR_BILLING      = "BILLING_ERROR"
ERR_LLM          = "LLM_ERROR"
ERR_REPORT       = "REPORT_ERROR"
ERR_EXPORT       = "EXPORT_ERROR"
ERR_LICENSE      = "LICENSE_ERROR"

def _safe_step(step_name: str, fn, max_retries: int = 3, backoff_s: float = 2.0):
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            result = fn()
            logger.info(f"[STEP {step_name}] OK (tentativo {attempt})")
            return result, None
        except Exception as e:
            last_err = e
            logger.warning(f"[STEP {step_name}] Tentativo {attempt}/{max_retries} fallito: {e}")
            if attempt < max_retries:
                time.sleep(backoff_s)
    logger.error(f"[STEP {step_name}] FALLITO dopo {max_retries} tentativi: {last_err}")
    return None, last_err

def _check_license_gate() -> dict:
    lic_mod = _import_module("license_manager")
    if lic_mod is None:
        logger.warning("license_manager.py non disponibile — fallback DEMO")
        return {
            "license_type": "DEMO",
            "is_valid": True,
            "message": "License manager non trovato — modalita DEMO.",
            "machine_id_short": "N/A",
        }
    status = lic_mod.check_license()
    logger.info(
        f"License check: type={status.get('license_type')} | "
        f"valid={status.get('is_valid')} | days={status.get('days_remaining', 'N/A')}"
    )
    return status

def load_invoice(pdf_path: str) -> dict:
    p = Path(pdf_path)
    if not p.exists():
        raise FileNotFoundError(f"File non trovato: {pdf_path}")
    if p.suffix.lower() != ".pdf":
        raise ValueError(f"Formato non supportato: {p.suffix} (atteso .pdf)")
    stat = p.stat()
    logger.info(f"Fattura caricata: {p.name} ({stat.st_size} bytes)")
    return {
        "path": str(p.resolve()),
        "filename": p.name,
        "size_bytes": stat.st_size,
        "loaded_at": datetime.now().isoformat(),
    }

def parse_invoice(pdf_path: str, use_ocr: bool = False) -> dict:
    parser_mod = _import_module("parser")
    if parser_mod is None:
        logger.warning("parser.py non disponibile — restituisco struttura vuota")
        return {"requires_manual_input": True, "error": "parser module not found"}

    try:
        if hasattr(parser_mod, "parse_invoice_from_path"):
            fields = parser_mod.parse_invoice_from_path(pdf_path, use_ocr=use_ocr)
        else:
            raw = parser_mod.extract_text(pdf_path, use_ocr=use_ocr)
            fields = parser_mod.extract_fields(raw, use_ocr=use_ocr)
        logger.info(f"Parser: {len(fields)} campi estratti")
        return fields
    except Exception as e:
        logger.error(f"Parser error: {e}")
        return {"requires_manual_input": True, "error": str(e)}

def normalize_invoice(raw_fields: dict, language: str = "it") -> dict:
    norm_mod = _import_module("normalizer")
    if norm_mod is None:
        logger.warning("normalizer.py non disponibile — campi grezzi")
        raw_fields["is_normalized"] = False
        return raw_fields
    try:
        normalized = norm_mod.normalize(raw_fields, locale=language)
        normalized["is_normalized"] = True
        logger.info(f"Normalizer: lingua rilevata={normalized.get('detected_language', 'N/A')}")
        return normalized
    except Exception as e:
        logger.error(f"Normalizer error: {e}")
        raw_fields["is_normalized"] = False
        raw_fields["normalize_error"] = str(e)
        return raw_fields

def classify_invoice(normalized: dict, compliance_threshold: float = 10000.0) -> dict:
    clf_mod = _import_module("classifier")
    if clf_mod is None:
        return {
            "payment_status": "UNKNOWN",
            "days_overdue": 0,
            "risk_level": "UNKNOWN",
            "reminder_level": 0,
            "compliance_flag": False,
            "classification_rationale": "Classificatore non disponibile",
        }
    try:
        classification = clf_mod.classify(normalized, compliance_threshold=compliance_threshold)
        logger.info(
            f"Classifier: status={classification.get('payment_status')} "
            f"| risk={classification.get('risk_level')} "
            f"| level={classification.get('reminder_level')}"
        )
        return classification
    except Exception as e:
        logger.error(f"Classifier error: {e}")
        return {
            "payment_status": "UNKNOWN",
            "days_overdue": 0,
            "risk_level": "UNKNOWN",
            "reminder_level": 0,
            "compliance_flag": False,
            "classification_rationale": f"Errore: {e}",
        }

def check_compliance(normalized: dict, classification: dict) -> dict:
    deducer_mod = _import_module("deducer")
    if deducer_mod is None:
        return {
            "compliance_flag": False,
            "flags": [],
            "recommendations": [],
            "disclaimer": "Il software fornisce suggerimenti, non decisioni.",
        }
    try:
        compliance = deducer_mod.check_compliance(normalized, classification)
        logger.info(f"Compliance: flag={compliance.get('compliance_flag')} | flags={compliance.get('flags')}")
        return compliance
    except Exception as e:
        logger.error(f"Compliance check error: {e}")
        return {
            "compliance_flag": False,
            "flags": [],
            "recommendations": [],
            "disclaimer": "Il software fornisce suggerimenti, non decisioni.",
            "error": str(e),
        }

def deduce_billing_action(normalized: dict, classification: dict, language: str) -> dict:
    deducer_mod = _import_module("deducer")
    if deducer_mod is None:
        return {
            "action": "SEND_REMINDER_L1",
            "recommended_channel": "email",
            "template_key": f"reminder_{language}_L1",
            "reminder_level": max(1, classification.get("reminder_level", 1)),
            "next_escalation_days": 15,
        }
    try:
        billing = deducer_mod.deduce(normalized, classification, language=language)
        logger.info(f"Deducer: action={billing.get('action')} | template={billing.get('template_key')}")
        return billing
    except Exception as e:
        logger.error(f"Deducer error: {e}")
        return {
            "action": "SEND_REMINDER_L1",
            "recommended_channel": "email",
            "template_key": f"reminder_{language}_L1",
            "reminder_level": 1,
            "next_escalation_days": 15,
            "error": str(e),
        }

def generate_reminder_text(
    normalized: dict,
    billing: dict,
    language: str,
    mode: str = "local",
    api_key: Optional[str] = None,
) -> str:
    deducer_mod = _import_module("deducer")
    if deducer_mod is None:
        return _static_reminder(normalized, billing, language)
    try:
        text = deducer_mod.generate_reminder_text(
            normalized, billing, language=language, mode=mode, api_key=api_key
        )
        if not text or len(text.strip()) < 20:
            raise ValueError("Testo generato troppo corto o vuoto")
        logger.info(f"Reminder generato: {len(text)} caratteri | lingua={language} | mode={mode}")
        return text
    except Exception as e:
        logger.warning(f"LLM fallback attivato: {e}")
        return _static_reminder(normalized, billing, language)

def _static_reminder(normalized: dict, billing: dict, language: str) -> str:
    level = billing.get("reminder_level", 1)
    num = normalized.get("invoice_number") or "N/A"
    raw_amt = normalized.get("amount")
    amount = 0.0 if raw_amt is None else float(raw_amt)
    currency = normalized.get("currency") or "EUR"
    client = normalized.get("client_name") or "Valued Customer"
    vendor = normalized.get("vendor_name") or ""
    due = normalized.get("due_date") or "N/A"

    templates = {
        "it": {
            1: (f"Gentile {client},\n\nla fattura n. {num} per {currency} {amount:.2f}, "
                f"con scadenza {due}, risulta ancora non saldata.\n"
                f"La invitiamo cortesemente a procedere al pagamento entro 5 giorni lavorativi.\n\n"
                f"Cordiali saluti,\n{vendor}"),
            2: (f"Gentile {client},\n\nNonostante i precedenti solleciti, la fattura n. {num} "
                f"per {currency} {amount:.2f} risulta ancora impagata.\n"
                f"La invitiamo a saldare entro 72 ore per evitare ulteriori azioni.\n\n"
                f"Distinti saluti,\n{vendor}"),
            3: (f"DIFFIDA FORMALE\n\n{client},\n\nla fattura n. {num} per {currency} {amount:.2f} "
                f"e gravemente scaduta. Si diffida a pagare entro 7 giorni, pena azioni legali.\n\n"
                f"NOTA: Consultare un legale prima di inviare questa comunicazione.\n{vendor}"),
        },
        "en": {
            1: (f"Dear {client},\n\nInvoice no. {num} for {currency} {amount:.2f} "
                f"(due {due}) remains unpaid.\nWe kindly ask you to arrange payment within 5 business days.\n\n"
                f"Kind regards,\n{vendor}"),
            2: (f"Dear {client},\n\nDespite our previous reminder, invoice no. {num} "
                f"for {currency} {amount:.2f} remains outstanding.\n"
                f"Please settle within 72 hours to avoid further action.\n\nBest regards,\n{vendor}"),
            3: (f"FORMAL NOTICE\n\nDear {client},\n\nInvoice no. {num} for {currency} {amount:.2f} "
                f"is severely overdue. Payment is required within 7 days or legal action will follow.\n\n"
                f"NOTE: Consult a lawyer before sending this notice.\n{vendor}"),
        },
        "de": {
            1: (f"Sehr geehrte(r) {client},\n\ndie Rechnung Nr. {num} ueber {currency} {amount:.2f} "
                f"(Faelligkeit: {due}) ist noch offen.\nBitte ueberweisen Sie den Betrag innerhalb von 5 Werktagen.\n\n"
                f"Mit freundlichen Gruessen,\n{vendor}"),
            2: (f"Sehr geehrte(r) {client},\n\ntrotz Erinnerung ist die Rechnung Nr. {num} "
                f"ueber {currency} {amount:.2f} weiterhin unbezahlt.\nBitte begleichen Sie den Betrag innerhalb von 72 Stunden.\n\n"
                f"Mit freundlichen Gruessen,\n{vendor}"),
            3: (f"LETZTE MAHNUNG\n\nSehr geehrte(r) {client},\n\ndie Rechnung Nr. {num} ueber {currency} {amount:.2f} "
                f"ist stark ueberfaellig. Zahlen Sie binnen 7 Tagen, andernfalls werden rechtliche Schritte eingeleitet.\n{vendor}"),
        },
        "fr": {
            1: (f"Bonjour {client},\n\nLa facture n° {num} d'un montant de {currency} {amount:.2f} "
                f"(echeance le {due}) est toujours en attente.\nMerci de proceder au reglement sous 5 jours ouvres.\n\n"
                f"Cordialement,\n{vendor}"),
            2: (f"Bonjour {client},\n\nSauf erreur, la facture n° {num} "
                f"de {currency} {amount:.2f} demeure impayee.\nMerci de regulariser la situation sous 72 heures.\n\n"
                f"Cordialement,\n{vendor}"),
            3: (f"MISE EN DEMEURE\n\n{client},\n\nLa facture n° {num} de {currency} {amount:.2f} "
                f"est a echeance critique. Sans reglement sous 7 jours, une procedure legale sera engagee.\n{vendor}"),
        },
        "es": {
            1: (f"Estimado/a {client},\n\nLa factura n.° {num} por importe de {currency} {amount:.2f} "
                f"(vencimiento {due}) se encuentra pendiente.\nLe rogamos efectue el pago en un plazo de 5 dias habiles.\n\n"
                f"Atentamente,\n{vendor}"),
            2: (f"Estimado/a {client},\n\nA pesar de los avisos, la factura n.° {num} "
                f"por {currency} {amount:.2f} sigue impagada.\nRogamos regularice la situacion en 72 horas.\n\n"
                f"Saludos cordiales,\n{vendor}"),
            3: (f"REQUERIMIENTO FORMAL DE PAGO\n\n{client},\n\nLa factura n.° {num} por {currency} {amount:.2f} "
                f"esta gravemente vencida. Dispone de 7 dias para abonarla antes de acciones legales.\n{vendor}"),
        },
        "pt": {
            1: (f"Prezado(a) {client},\n\nA fatura n.º {num} no valor de {currency} {amount:.2f} "
                f"(vencimento a {due}) permanece em aberto.\nSolicitamos a regularizacao no prazo de 5 dias uteis.\n\n"
                f"Com os melhores cumprimentos,\n{vendor}"),
            2: (f"Prezado(a) {client},\n\nApesar dos avisos, a fatura n.º {num} "
                f"de {currency} {amount:.2f} continua por liquidar.\nPedimos a liquidacao em 72 horas.\n\n"
                f"Atenciosamente,\n{vendor}"),
            3: (f"NOTIFICACAO FORMAL DE COBRANCA\n\n{client},\n\nA fatura n.º {num} de {currency} {amount:.2f} "
                f"encontra-se vencida. Exige-se o pagamento no prazo de 7 dias sob pena judicial.\n{vendor}"),
        },
    }
    lang_templates = templates.get(language, templates["en"])
    return lang_templates.get(level, lang_templates[1])

def generate_report(
    normalized: dict,
    classification: dict,
    compliance: dict,
    billing: dict,
    reminder_text: str,
    language: str,
    output_dir: Optional[str] = None,
    formats: Optional[list] = None,
    is_demo: bool = False,
) -> dict:
    rg_mod = _import_module("report_generator")
    if rg_mod is None:
        return {"error": "report_generator module not found", "paths": {}}
    try:
        report = rg_mod.generate(
            invoice=normalized,
            classification=classification,
            compliance=compliance,
            billing=billing,
            reminder_text=reminder_text,
            language=language,
            output_dir=output_dir,
            formats=formats or ["pdf"],
            is_demo=is_demo,
        )
        logger.info(f"Report generato: {report.get('paths', {})}")
        return report
    except Exception as e:
        logger.error(f"Report generator error: {e}")
        return {"error": str(e), "paths": {}}

def export_result(report: dict, output_dir: Optional[str] = None) -> list:
    exp_mod = _import_module("export_engine")
    if exp_mod is None:
        return []
    if hasattr(exp_mod, "ensure_output_structure"):
        exp_mod.ensure_output_structure(output_dir)
    try:
        paths = exp_mod.export(report, output_dir=output_dir)
        logger.info(f"Export completato: {paths}")
        return paths
    except Exception as e:
        logger.error(f"Export error: {e}")
        return []

def run_pipeline(
    pdf_path: str,
    language: str = "it",
    mode: str = "local",
    api_key: Optional[str] = None,
    output_dir: Optional[str] = None,
    formats: Optional[list] = None,
    compliance_threshold: float = 10000.0,
    is_demo: bool = False,
    progress_callback: Optional[Callable[[str, str, str], None]] = None,
) -> WorkflowResult:
    start_time = time.time()
    audit_log = []
    errors = []

    def _audit(step: str, status: str, detail: str = ""):
        entry = {
            "step": step,
            "status": status,
            "detail": detail,
            "timestamp": datetime.now().isoformat(),
        }
        audit_log.append(entry)
        logger.info(f"AUDIT [{step}] {status} — {detail}")
        if progress_callback:
            try:
                progress_callback(step, status, detail)
            except Exception:
                pass

    _audit("PIPELINE_START", "OK", f"pdf={pdf_path} | lang={language} | mode={mode}")

    lic_status = _check_license_gate()
    if not lic_status.get("is_valid", False):
        msg = lic_status.get("message", "Licenza non valida")
        _audit("LICENSE", "FAILED", msg)
        errors.append({"step": "LICENSE", "code": ERR_LICENSE, "error": msg})
        return WorkflowResult({}, {}, {}, {}, "", None, [], audit_log, False, errors)
    else:
        _audit("LICENSE", "OK", f"type={lic_status.get('license_type')}")

    # Aggiorna flag is_demo in base alla licenza attiva
    if lic_status.get("license_type") != "FULL":
        is_demo = True

    file_meta, err = _safe_step("LOAD", lambda: load_invoice(pdf_path))
    if err:
        errors.append({"step": "LOAD", "code": ERR_PARSE, "error": str(err)})
        _audit("LOAD", "FAILED", str(err))
        return WorkflowResult({}, {}, {}, {}, "", None, [], audit_log, False, errors)
    _audit("LOAD", "OK", file_meta.get("filename", ""))

    raw_fields, err = _safe_step("PARSE", lambda: parse_invoice(pdf_path))
    if err or raw_fields.get("requires_manual_input"):
        errors.append({"step": "PARSE", "code": ERR_PARSE, "error": str(err or "manual input required")})
        _audit("PARSE", "FALLBACK", str(err or "requires_manual_input"))
    else:
        _audit("PARSE", "OK", f"{len(raw_fields)} campi estratti")

    normalized, err = _safe_step("NORMALIZE", lambda: normalize_invoice(raw_fields, language))
    if err:
        errors.append({"step": "NORMALIZE", "code": ERR_NORMALIZE, "error": str(err)})
        _audit("NORMALIZE", "FALLBACK", str(err))
        normalized = raw_fields
    else:
        _audit("NORMALIZE", "OK", f"lingua={normalized.get('detected_language', language)}")

    classification, err = _safe_step(
        "CLASSIFY",
        lambda: classify_invoice(normalized, compliance_threshold=compliance_threshold)
    )
    if err:
        errors.append({"step": "CLASSIFY", "code": ERR_CLASSIFY, "error": str(err)})
        _audit("CLASSIFY", "FALLBACK", str(err))
        classification = {"payment_status": "UNKNOWN", "days_overdue": 0, "risk_level": "UNKNOWN", "reminder_level": 0}
    else:
        _audit("CLASSIFY", "OK", f"status={classification.get('payment_status')} | level={classification.get('reminder_level')}")

    compliance, err = _safe_step("COMPLIANCE", lambda: check_compliance(normalized, classification))
    if err:
        errors.append({"step": "COMPLIANCE", "code": ERR_COMPLIANCE, "error": str(err)})
        _audit("COMPLIANCE", "FALLBACK", str(err))
        compliance = {"compliance_flag": False, "flags": [], "recommendations": []}
    else:
        _audit("COMPLIANCE", "OK", f"flags={compliance.get('flags', [])}")

    billing, err = _safe_step(
        "BILLING",
        lambda: deduce_billing_action(normalized, classification, language)
    )
    if err:
        errors.append({"step": "BILLING", "code": ERR_BILLING, "error": str(err)})
        _audit("BILLING", "FALLBACK", str(err))
        billing = {"action": "SEND_REMINDER_L1", "reminder_level": 1}
    else:
        _audit("BILLING", "OK", f"action={billing.get('action')}")

    reminder_text, err = _safe_step(
        "REMINDER",
        lambda: generate_reminder_text(normalized, billing, language, mode, api_key)
    )
    if err or not reminder_text:
        try:
            reminder_text = _static_reminder(normalized, billing, language)
        except Exception as e_rem:
            logger.error(f"Errore generazione reminder statico: {e_rem}")
            reminder_text = f"Notice: Invoice {normalized.get('invoice_number', 'N/A')} payment is required."
        errors.append({"step": "REMINDER", "code": ERR_LLM, "error": str(err) if err else "fallback template"})
        _audit("REMINDER", "FALLBACK", "template statico usato")
    else:
        _audit("REMINDER", "OK", f"{len(reminder_text)} caratteri")

    report, err = _safe_step(
        "REPORT",
        lambda: generate_report(
            normalized, classification, compliance, billing,
            reminder_text, language, output_dir, formats, is_demo
        )
    )
    if err or not report:
        errors.append({"step": "REPORT", "code": ERR_REPORT, "error": str(err or "report vuoto")})
        _audit("REPORT", "FAILED", str(err))
        report = {"paths": {}, "error": str(err)}
    else:
        _audit("REPORT", "OK", f"formati={list(report.get('paths', {}).keys())}")

    export_paths, err = _safe_step("EXPORT", lambda: export_result(report, output_dir))
    if err:
        errors.append({"step": "EXPORT", "code": ERR_EXPORT, "error": str(err)})
        _audit("EXPORT", "FAILED", str(err))
        export_paths = []
    else:
        _audit("EXPORT", "OK", f"percorsi={export_paths}")

    elapsed = round(time.time() - start_time, 2)
    _audit("PIPELINE_END", "OK" if not errors else "PARTIAL", f"elapsed={elapsed}s | errors={len(errors)}")
    logger.info(f"Pipeline completata in {elapsed}s | successo={'SI' if not errors else 'PARZIALE'}")

    return WorkflowResult(
        invoice=normalized,
        classification=classification,
        compliance=compliance,
        billing=billing,
        reminder_text=reminder_text,
        report_path=str(report.get("paths", {}).get("pdf", "")),
        export_paths=export_paths or [],
        audit_log=audit_log,
        success=len(errors) == 0,
        errors=errors,
    )

if __name__ == "__main__":
    import argparse
    parser_cli = argparse.ArgumentParser(description="ZUKWEND — Workflow Engine")
    parser_cli.add_argument("pdf", nargs="?", default=None, help="Percorso al PDF fattura")
    parser_cli.add_argument("--lang", default="it", choices=["it", "en", "fr", "de", "es", "pt"])
    parser_cli.add_argument("--mode", default="local", choices=["local", "cloud"])
    parser_cli.add_argument("--api-key", default=None)
    parser_cli.add_argument("--output", default=None)
    parser_cli.add_argument("--formats", default="pdf", help="pdf,docx,json,html")
    parser_cli.add_argument("--demo", action="store_true")

    args = parser_cli.parse_args()

    if not args.pdf:
        try:
            from gui_launcher import launch_gui_launcher
            launch_gui_launcher()
            sys.exit(0)
        except ImportError:
            print("[!] gui_launcher.py non trovato. Specificare il PDF da riga di comando.")
            sys.exit(1)

    result = run_pipeline(
        pdf_path=args.pdf,
        language=args.lang,
        mode=args.mode,
        api_key=args.api_key,
        output_dir=args.output,
        formats=args.formats.split(","),
        is_demo=args.demo,
    )
    sys.exit(0 if result.success else 1)