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
try:
    from resource_utils import get_writable_dir, get_output_dir
except ImportError:  # pragma: no cover - esecuzione isolata del modulo
    def get_writable_dir(preferred: Path, fallback_name: str) -> Path:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred

    def get_output_dir() -> str:
        folder = os.path.abspath("output")
        os.makedirs(folder, exist_ok=True)
        return folder

try:
    from report_generator import clean_path
except ImportError:
    def clean_path(p, basename_only=False):
        if isinstance(p, (list, tuple)):
            raw = str(p[0]) if p else ""
        elif isinstance(p, dict):
            raw = str(next(iter(p.values()))) if p else ""
        else:
            raw = str(p or "")
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw.strip("[]'\" ")
        norm = os.path.normpath(raw) if raw else ""
        return os.path.basename(norm) if basename_only else norm

# ---------------------------------------------------------------------------
# Console & Audit i18n Localization Dictionary (6 Languages: EN, IT, DE, FR, ES, PT)
# ---------------------------------------------------------------------------
I18N_CONSOLE = {
    "en": {
        "fields_extracted": "fields extracted",
        "characters": "characters",
        "path_prefix": "path=",
        "language_prefix": "language=",
        "formats_prefix": "formats=",
        "static_template_used": "static template used",
        "manual_input_required": "manual input required",
        "invalid_license": "Invalid license",
        "pipeline_completed": "Pipeline completed in",
        "success_label": "success",
        "yes_label": "YES",
        "partial_label": "PARTIAL",
        "report_empty": "empty report",
    },
    "it": {
        "fields_extracted": "campi estratti",
        "characters": "caratteri",
        "path_prefix": "percorso=",
        "language_prefix": "lingua=",
        "formats_prefix": "formati=",
        "static_template_used": "template statico usato",
        "manual_input_required": "input manuale richiesto",
        "invalid_license": "Licenza non valida",
        "pipeline_completed": "Pipeline completata in",
        "success_label": "successo",
        "yes_label": "SI",
        "partial_label": "PARZIALE",
        "report_empty": "report vuoto",
    },
    "de": {
        "fields_extracted": "Felder extrahiert",
        "characters": "Zeichen",
        "path_prefix": "pfad=",
        "language_prefix": "sprache=",
        "formats_prefix": "formate=",
        "static_template_used": "statisches Template verwendet",
        "manual_input_required": "manuelle Eingabe erforderlich",
        "invalid_license": "Ungültige Lizenz",
        "pipeline_completed": "Pipeline abgeschlossen in",
        "success_label": "Erfolg",
        "yes_label": "JA",
        "partial_label": "TEILWEISE",
        "report_empty": "leerer Bericht",
    },
    "fr": {
        "fields_extracted": "champs extraits",
        "characters": "caractères",
        "path_prefix": "chemin=",
        "language_prefix": "langue=",
        "formats_prefix": "formats=",
        "static_template_used": "modèle statique utilisé",
        "manual_input_required": "saisie manuelle requise",
        "invalid_license": "Licence non valide",
        "pipeline_completed": "Pipeline terminée en",
        "success_label": "succès",
        "yes_label": "OUI",
        "partial_label": "PARTIEL",
        "report_empty": "rapport vide",
    },
    "es": {
        "fields_extracted": "campos extraídos",
        "characters": "caracteres",
        "path_prefix": "ruta=",
        "language_prefix": "idioma=",
        "formats_prefix": "formatos=",
        "static_template_used": "plantilla estática utilizada",
        "manual_input_required": "entrada manual requerida",
        "invalid_license": "Licencia no válida",
        "pipeline_completed": "Pipeline completada en",
        "success_label": "éxito",
        "yes_label": "SÍ",
        "partial_label": "PARCIAL",
        "report_empty": "informe vacío",
    },
    "pt": {
        "fields_extracted": "campos extraídos",
        "characters": "caracteres",
        "path_prefix": "caminho=",
        "language_prefix": "idioma=",
        "formats_prefix": "formatos=",
        "static_template_used": "modelo estático utilizado",
        "manual_input_required": "entrada manual necessária",
        "invalid_license": "Licença inválida",
        "pipeline_completed": "Pipeline concluída em",
        "success_label": "sucesso",
        "yes_label": "SIM",
        "partial_label": "PARCIAL",
        "report_empty": "relatório vazio",
    },
}

if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).parent
else:
    ROOT_DIR = Path(__file__).parent

# Cartella log scrivibile (l'installazione in C:\Program Files non lo e' per utenti standard)
try:
    LOG_DIR = get_writable_dir(ROOT_DIR / "logs", "logs")
except Exception:
    import tempfile
    LOG_DIR = Path(tempfile.gettempdir())

log_filename = LOG_DIR / f"zukwend_workflow_{datetime.now().strftime('%Y%m%d')}.log"

_log_handlers = []
try:
    _log_handlers.append(logging.FileHandler(log_filename, encoding="utf-8"))
except OSError:
    pass  # log su file non disponibile: l'app deve comunque avviarsi
if sys.stdout is not None:  # con PyInstaller --noconsole sys.stdout e' None
    _log_handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
    handlers=_log_handlers or [logging.NullHandler()],
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
            logger.info(f"[STEP {step_name}] OK (attempt {attempt})")
            return result, None
        except Exception as e:
            last_err = e
            logger.warning(f"[STEP {step_name}] Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(backoff_s)
    logger.error(f"[STEP {step_name}] FAILED after {max_retries} attempts: {last_err}")
    return None, last_err

def _check_license_gate() -> dict:
    lic_mod = _import_module("license_manager")
    if lic_mod is None:
        logger.warning("license_manager.py not available — DEMO fallback")
        return {
            "license_type": "DEMO",
            "is_valid": True,
            "message": "License manager not found — DEMO mode.",
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
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if p.suffix.lower() != ".pdf":
        raise ValueError(f"Unsupported format: {p.suffix} (expected .pdf)")
    stat = p.stat()
    logger.info(f"Invoice loaded: {p.name} ({stat.st_size} bytes)")
    return {
        "path": str(p.resolve()),
        "filename": p.name,
        "size_bytes": stat.st_size,
        "loaded_at": datetime.now().isoformat(),
    }

def parse_invoice(pdf_path: str, use_ocr: bool = False, mode: str = "local", api_key: Optional[str] = None) -> dict:
    parser_mod = _import_module("parser")
    if parser_mod is None:
        logger.warning("parser.py not available — returning empty structure")
        return {"requires_manual_input": True, "error": "parser module not found"}

    try:
        raw = parser_mod.extract_text(pdf_path, use_ocr=use_ocr)
        fields = parser_mod.extract_fields(raw, use_ocr=use_ocr, mode=mode, api_key=api_key)
        logger.info(f"Parser: {len(fields)} fields extracted")
        return fields
    except Exception as e:
        logger.error(f"Parser error: {e}")
        return {"requires_manual_input": True, "error": str(e)}

def normalize_invoice(raw_fields: dict, language: str = "it") -> dict:
    norm_mod = _import_module("normalizer")
    if norm_mod is None:
        logger.warning("normalizer.py not available — raw fields")
        raw_fields["is_normalized"] = False
        return raw_fields
    try:
        normalized = norm_mod.normalize(raw_fields, locale=language)
        normalized["is_normalized"] = True
        logger.info(f"Normalizer: detected_language={normalized.get('detected_language', 'N/A')}")
        return normalized
    except Exception as e:
        logger.error(f"Normalizer error: {e}")
        raw_fields["is_normalized"] = False
        raw_fields["normalize_error"] = str(e)
        return raw_fields

def classify_invoice(normalized: dict, compliance_threshold: float = 10000.0, language: str = "it") -> dict:
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
        import inspect
        sig = inspect.signature(clf_mod.classify)
        if "language" in sig.parameters:
            classification = clf_mod.classify(normalized, compliance_threshold=compliance_threshold, language=language)
        else:
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

DISCLAIMER_BY_LANG = {
    "it": (
        "NOTA: Questo documento è generato da software. "
        "Il software fornisce suggerimenti, non decisioni. "
        "Consultare un professionista legale prima di inviare comunicazioni di livello 3."
    ),
    "en": (
        "NOTE: This document is software-generated. "
        "The software provides suggestions, not decisions. "
        "Consult a legal professional before sending level-3 notices."
    ),
    "fr": (
        "NOTE: Ce document est généré par logiciel. "
        "Le logiciel fournit des suggestions, pas des décisions. "
        "Consultez un professionnel juridique avant d'envoyer des avis de niveau 3."
    ),
    "de": (
        "HINWEIS: Dieses Dokument wurde von Software erstellt. "
        "Die Software liefert Vorschläge, keine Entscheidungen. "
        "Konsultieren Sie einen Rechtsanwalt, bevor Sie Mahnstufe-3-Schreiben versenden."
    ),
    "es": (
        "NOTA: Este documento es generado por software. "
        "El software proporciona sugerencias, no decisiones. "
        "Consulte a un profesional legal antes de enviar avisos de nivel 3."
    ),
    "pt": (
        "NOTA: Este documento é gerado por software. "
        "O software fornece sugestões, não decisões. "
        "Consulte um profissional jurídico antes de enviar avisos de nível 3."
    ),
}

def check_compliance(normalized: dict, classification: dict, language: Optional[str] = None) -> dict:
    deducer_mod = _import_module("deducer")
    lang = (language or normalized.get("detected_language") or normalized.get("language") or "en").lower()
    disclaimer_text = DISCLAIMER_BY_LANG.get(lang, DISCLAIMER_BY_LANG["en"])
    if deducer_mod is None:
        return {
            "compliance_flag": False,
            "flags": [],
            "recommendations": [],
            "disclaimer": disclaimer_text,
        }
    try:
        import inspect
        sig = inspect.signature(deducer_mod.check_compliance)
        if "language" in sig.parameters:
            compliance = deducer_mod.check_compliance(normalized, classification, language=lang)
        else:
            compliance = deducer_mod.check_compliance(normalized, classification)
        logger.info(f"Compliance: flag={compliance.get('compliance_flag')} | flags={compliance.get('flags')}")
        return compliance
    except Exception as e:
        logger.error(f"Compliance check error: {e}")
        return {
            "compliance_flag": False,
            "flags": [],
            "recommendations": [],
            "disclaimer": disclaimer_text,
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
            "days_overdue": classification.get("days_overdue", 0),
        }
    try:
        billing = deducer_mod.deduce(normalized, classification, language=language)
        if "days_overdue" not in billing:
            billing["days_overdue"] = classification.get("days_overdue", 0)
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
            "days_overdue": classification.get("days_overdue", 0),
            "error": str(e),
        }

def generate_reminder_text(
    normalized: dict,
    billing: dict,
    language: str,
    mode: str = "local",
    api_key: Optional[str] = None,
    classification: Optional[dict] = None,
) -> str:
    deducer_mod = _import_module("deducer")
    if classification and "days_overdue" not in billing:
        billing["days_overdue"] = classification.get("days_overdue", 0)
    if deducer_mod is None:
        return _static_reminder(normalized, billing, language)
    try:
        import inspect
        sig = inspect.signature(deducer_mod.generate_reminder_text)
        if "classification" in sig.parameters:
            text = deducer_mod.generate_reminder_text(
                normalized, billing, language=language, mode=mode, api_key=api_key, classification=classification
            )
        else:
            text = deducer_mod.generate_reminder_text(
                normalized, billing, language=language, mode=mode, api_key=api_key
            )
        if not text or len(text.strip()) < 20:
            raise ValueError("Generated text too short or empty")
        logger.info(f"Reminder generated: {len(text)} characters | language={language} | mode={mode}")
        return text
    except Exception as e:
        logger.warning(f"LLM fallback triggered: {e}")
        return _static_reminder(normalized, billing, language)

def _static_reminder(normalized: dict, billing: dict, language: str) -> str:
    import re
    level = billing.get("reminder_level", 1)
    num = normalized.get("invoice_number") or "N/A"
    raw_amt = normalized.get("amount")
    amount = 0.0 if raw_amt is None else float(raw_amt)
    currency = normalized.get("currency") or "EUR"

    client = normalized.get("client_name") or "Valued Customer"
    client = re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", str(client).strip())
    client = re.sub(r"\s+", " ", client)

    vendor = normalized.get("vendor_name") or ""
    vendor = re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", str(vendor).strip())
    vendor = re.sub(r"\s+", " ", vendor)

    due = normalized.get("due_date") or "N/A"
    days_overdue = billing.get("days_overdue") or normalized.get("days_overdue") or 0
    grace_days = billing.get("grace_days") or (7 if level == 3 else (3 if level == 2 else 5))

    templates = {
        "it": {
            1: (f"Gentile {client},\n\nla fattura n. {num} per {currency} {amount:,.2f}, "
                f"con scadenza {due}, risulta ancora non saldata.\n"
                f"La invitiamo cortesemente a procedere al pagamento entro {grace_days} giorni lavorativi.\n\n"
                f"Cordiali saluti,\n{vendor}"),
            2: (f"Gentile {client},\n\nNonostante i precedenti solleciti, la fattura n. {num} "
                f"per {currency} {amount:,.2f} ({days_overdue} giorni di ritardo) risulta ancora impagata.\n"
                f"La invitiamo a saldare entro {grace_days} giorni per evitare ulteriori azioni.\n\n"
                f"Distinti saluti,\n{vendor}"),
            3: (f"DIFFIDA FORMALE\n\n{client},\n\nla fattura n. {num} per {currency} {amount:,.2f} "
                f"è gravemente scaduta da {days_overdue} giorni. Si diffida a pagare entro {grace_days} giorni, pena azioni legali.\n\n"
                f"NOTA: Consultare un legale prima di inviare questa comunicazione.\n{vendor}"),
        },
        "en": {
            1: (f"Dear {client},\n\nInvoice no. {num} for {currency} {amount:,.2f} "
                f"(due {due}) remains unpaid.\nWe kindly ask you to arrange payment within {grace_days} business days.\n\n"
                f"Kind regards,\n{vendor}"),
            2: (f"Dear {client},\n\nDespite our previous notice, invoice no. {num} ({currency} {amount:,.2f}) "
                f"due on {due} is overdue by {days_overdue} days.\n"
                f"Please settle within {grace_days} days to prevent further escalation.\n\nBest regards,\n{vendor}"),
            3: (f"FORMAL COLLECTION NOTICE\n\n{client},\n\n"
                f"You are formally required to settle invoice no. {num} ({currency} {amount:,.2f}), "
                f"overdue by {days_overdue} days, within {grace_days} days. "
                f"Failure to comply will result in immediate legal action.\n\n{vendor}"),
        },
        "de": {
            1: (f"Sehr geehrte(r) {client},\n\ndie Rechnung Nr. {num} über {currency} {amount:,.2f} "
                f"(Fälligkeit: {due}) ist noch offen.\nBitte überweisen Sie den Betrag innerhalb von {grace_days} Werktagen.\n\n"
                f"Mit freundlichen Grüßen,\n{vendor}"),
            2: (f"Sehr geehrte(r) {client},\n\ntrotz Erinnerung ist die Rechnung Nr. {num} "
                f"über {currency} {amount:,.2f} seit {days_overdue} Tagen überfällig.\nBitte begleichen Sie den Betrag innerhalb von {grace_days} Tagen.\n\n"
                f"Mit freundlichen Grüßen,\n{vendor}"),
            3: (f"LETZTE MAHNUNG\n\nSehr geehrte(r) {client},\n\ndie Rechnung Nr. {num} über {currency} {amount:,.2f} "
                f"ist stark überfällig ({days_overdue} Tage). Zahlen Sie binnen {grace_days} Tagen, andernfalls werden rechtliche Schritte eingeleitet.\n{vendor}"),
        },
        "fr": {
            1: (f"Bonjour {client},\n\nLa facture n° {num} d'un montant de {currency} {amount:,.2f} "
                f"(échéance le {due}) est toujours en attente.\nMerci de procéder au règlement sous {grace_days} jours ouvrés.\n\n"
                f"Cordialement,\n{vendor}"),
            2: (f"Bonjour {client},\n\nSauf erreur, la facture n° {num} "
                f"de {currency} {amount:,.2f} est en retard de {days_overdue} jours.\nMerci de régulariser la situation sous {grace_days} jours.\n\n"
                f"Cordialement,\n{vendor}"),
            3: (f"MISE EN DEMEURE\n\n{client},\n\nLa facture n° {num} de {currency} {amount:,.2f} "
                f"est en retard critique ({days_overdue} jours). Sans règlement sous {grace_days} jours, une procédure légale sera engagée.\n{vendor}"),
        },
        "es": {
            1: (f"Estimado/a {client},\n\nLa factura n.° {num} por importe de {currency} {amount:,.2f} "
                f"(vencimiento {due}) se encuentra pendiente.\nLe rogamos efectúe el pago en un plazo de {grace_days} días hábiles.\n\n"
                f"Atentamente,\n{vendor}"),
            2: (f"Estimado/a {client},\n\nA pesar de los avisos, la factura n.° {num} "
                f"por {currency} {amount:,.2f} acumula {days_overdue} días de retraso.\nRogamos regularice la situación en {grace_days} días.\n\n"
                f"Saludos cordiales,\n{vendor}"),
            3: (f"REQUERIMIENTO FORMAL DE PAGO\n\n{client},\n\nLa factura n.° {num} por {currency} {amount:,.2f} "
                f"acumula {days_overdue} días de retraso. Dispone de {grace_days} días para abonarla antes de acciones legales.\n{vendor}"),
        },
        "pt": {
            1: (f"Prezado(a) {client},\n\nA fatura n.º {num} no valor de {currency} {amount:,.2f} "
                f"(vencimento a {due}) permanece em aberto.\nSolicitamos a regularização no prazo de {grace_days} dias úteis.\n\n"
                f"Com os melhores cumprimentos,\n{vendor}"),
            2: (f"Prezado(a) {client},\n\nApesar dos avisos, a fatura n.º {num} "
                f"de {currency} {amount:,.2f} encontra-se vencida há {days_overdue} dias.\nPedimos a liquidação em {grace_days} dias.\n\n"
                f"Atenciosamente,\n{vendor}"),
            3: (f"NOTIFICAÇÃO FORMAL DE COBRANÇA\n\n{client},\n\nA fatura n.º {num} de {currency} {amount:,.2f} "
                f"encontra-se vencida há {days_overdue} dias. Exige-se o pagamento no prazo de {grace_days} dias sob pena judicial.\n{vendor}"),
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
    get_output_dir()  # crea cwd/output se mancante (mai dentro _MEIPASS)
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
            formats=formats or ["pdf", "xlsx", "json"],
            is_demo=is_demo,
        )
        logger.info(f"Report generated: {report.get('paths', {})}")
        return report
    except Exception as e:
        logger.error(f"Report generator error: {e}")
        return {"error": str(e), "paths": {}}

def export_result(report: dict, output_dir: Optional[str] = None) -> list:
    get_output_dir()  # crea cwd/output se mancante (mai dentro _MEIPASS)
    exp_mod = _import_module("export_engine")
    if exp_mod is None:
        return []
    if hasattr(exp_mod, "ensure_output_structure"):
        exp_mod.ensure_output_structure(output_dir)
    try:
        paths = exp_mod.export(report, output_dir=output_dir)
        logger.info(f"Export completed: {paths}")
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

    if formats is None:
        formats = ["pdf", "xlsx", "json"]

    lang_key = (language or "en").strip().lower()[:2]
    i18n = I18N_CONSOLE.get(lang_key, I18N_CONSOLE["en"])

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

    # Controllo esplicito Ollama: zero fallback silenzioso se Ollama non è attivo
    if mode == "ollama":
        import urllib.request
        ollama_alive = False
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags", headers={"User-Agent": "ZUKWEND"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                ollama_alive = (resp.status == 200)
        except Exception:
            ollama_alive = False

        if not ollama_alive:
            msg = "Ollama non rilevato su localhost:11434. Avvia il server Ollama oppure seleziona ⚡ ZUKWEND CORE AI."
            _audit("OLLAMA", "FAILED", msg)
            errors.append({"step": "OLLAMA", "code": "ERR_OLLAMA", "error": msg})
            return WorkflowResult({}, {}, {}, {}, "", None, [], audit_log, False, errors)
        else:
            _audit("OLLAMA", "OK", "Server Ollama connesso su localhost:11434")

    lic_status = _check_license_gate()
    if not lic_status.get("is_valid", False):
        msg = lic_status.get("message") or i18n["invalid_license"]
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

    raw_fields, err = _safe_step("PARSE", lambda: parse_invoice(pdf_path, mode=mode, api_key=api_key))
    if err or raw_fields.get("requires_manual_input"):
        errors.append({"step": "PARSE", "code": ERR_PARSE, "error": str(err or i18n["manual_input_required"])})
        _audit("PARSE", "FALLBACK", str(err or i18n["manual_input_required"]))
    else:
        _audit("PARSE", "OK", f"{len(raw_fields)} {i18n['fields_extracted']}")

    normalized, err = _safe_step("NORMALIZE", lambda: normalize_invoice(raw_fields, language))
    if err:
        errors.append({"step": "NORMALIZE", "code": ERR_NORMALIZE, "error": str(err)})
        _audit("NORMALIZE", "FALLBACK", str(err))
        normalized = raw_fields
    else:
        _audit("NORMALIZE", "OK", f"{i18n['language_prefix']}{normalized.get('detected_language', language)}")

    classification, err = _safe_step(
        "CLASSIFY",
        lambda: classify_invoice(normalized, compliance_threshold=compliance_threshold, language=language)
    )
    if err:
        errors.append({"step": "CLASSIFY", "code": ERR_CLASSIFY, "error": str(err)})
        _audit("CLASSIFY", "FALLBACK", str(err))
        classification = {"payment_status": "UNKNOWN", "days_overdue": 0, "risk_level": "UNKNOWN", "reminder_level": 0}
    else:
        if lang_key == "en" and "flags" in classification:
            classification["flags"] = [
                "critical_overdue_bad_debt_risk" if f == "critical_overdue_risk_inesigibilita" else f
                for f in classification["flags"]
            ]
        _audit("CLASSIFY", "OK", f"status={classification.get('payment_status')} | level={classification.get('reminder_level')}")

    compliance, err = _safe_step("COMPLIANCE", lambda: check_compliance(normalized, classification, language=language))
    if err:
        errors.append({"step": "COMPLIANCE", "code": ERR_COMPLIANCE, "error": str(err)})
        _audit("COMPLIANCE", "FALLBACK", str(err))
        compliance = {"compliance_flag": False, "flags": [], "recommendations": []}
    else:
        if lang_key == "en" and "flags" in compliance:
            compliance["flags"] = [
                "critical_overdue_bad_debt_risk" if f == "critical_overdue_risk_inesigibilita" else f
                for f in compliance["flags"]
            ]
        flags_list = compliance.get("flags", [])
        flags_str = ", ".join(flags_list) if flags_list else "none"
        _audit("COMPLIANCE", "OK", f"flags={flags_str}")

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
        lambda: generate_reminder_text(normalized, billing, language, mode, api_key, classification=classification)
    )
    if err or not reminder_text:
        try:
            reminder_text = _static_reminder(normalized, billing, language)
        except Exception as e_rem:
            logger.error(f"Static reminder generation error: {e_rem}")
            reminder_text = f"Notice: Invoice {normalized.get('invoice_number', 'N/A')} payment is required."
        errors.append({"step": "REMINDER", "code": ERR_LLM, "error": str(err) if err else "fallback template"})
        _audit("REMINDER", "FALLBACK", i18n["static_template_used"])
    else:
        _audit("REMINDER", "OK", f"{len(reminder_text)} {i18n['characters']}")

    report, err = _safe_step(
        "REPORT",
        lambda: generate_report(
            normalized, classification, compliance, billing,
            reminder_text, language, output_dir, formats, is_demo
        )
    )
    if err or not report:
        errors.append({"step": "REPORT", "code": ERR_REPORT, "error": str(err or i18n["report_empty"])})
        _audit("REPORT", "FAILED", str(err))
        report = {"paths": {}, "error": str(err)}
    else:
        fmts_list = list(report.get("paths", {}).keys())
        fmts_str = ", ".join(fmts_list) if fmts_list else "none"
        _audit("REPORT", "OK", f"{i18n['formats_prefix']}{fmts_str}")

    export_paths, err = _safe_step("EXPORT", lambda: export_result(report, output_dir))
    if err:
        errors.append({"step": "EXPORT", "code": ERR_EXPORT, "error": str(err)})
        _audit("EXPORT", "FAILED", str(err))
        export_paths = []
    else:
        _audit("EXPORT", "OK", f"{i18n['path_prefix']}{clean_path(export_paths)}")

    elapsed = round(time.time() - start_time, 2)
    _audit("PIPELINE_END", "OK" if not errors else "PARTIAL", f"elapsed={elapsed}s | errors={len(errors)}")
    logger.info(f"{i18n['pipeline_completed']} {elapsed}s | {i18n['success_label']}={i18n['yes_label'] if not errors else i18n['partial_label']}")

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