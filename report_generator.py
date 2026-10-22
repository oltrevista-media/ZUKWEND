"""
ZUKWEND — Multilingual Billing Agent
Modulo: report_generator.py
Ruolo: Generazione report AR in formato PDF, DOCX, JSON, HTML
Versione: 2.1.5-ENTERPRISE (Full 6-Language Native Edition)
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import html as _html
import io
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, List
from xml.sax.saxutils import escape as _xml_escape

try:
    from resource_utils import APP_VERSION, get_output_dir, _is_inside_meipass
except ImportError:  # pragma: no cover - esecuzione isolata del modulo
    APP_VERSION = "2.1.5"

    def get_output_dir() -> str:
        folder = os.path.abspath("output")
        os.makedirs(folder, exist_ok=True)
        return folder

    def _is_inside_meipass(path: str) -> bool:
        return False

logger = logging.getLogger("zukwend.report_generator")

_TS_SUFFIX_RE = re.compile(r"_\d{8}_\d{6}(?:_\d+)?$")

# ---------------------------------------------------------------------------
# Sanificazione Percorsi (Clean Path)
# ---------------------------------------------------------------------------
def clean_path(percorsi: Union[str, List, tuple, dict, Path, None], basename_only: bool = False) -> str:
    """
    Sanifica la variabile percorso:
    - Se la variabile e' una lista o tupla, estrae la stringa del primo percorso.
    - Se e' un dict, estrae il primo valore stringa.
    - Rimuove eventuali stringhe grezze tipo "['C:\\...']".
    - Applica os.path.normpath() per rimuovere il raddoppio dei backslash.
    - Se basename_only=True, restituisce direttamente os.path.basename(norm).
    """
    if percorsi is None:
        return ""
    if isinstance(percorsi, Path):
        raw = str(percorsi)
    elif isinstance(percorsi, (list, tuple)):
        raw = str(percorsi[0]) if percorsi else ""
    elif isinstance(percorsi, dict):
        raw = str(next(iter(percorsi.values()))) if percorsi else ""
    else:
        raw = str(percorsi)

    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw.strip("[]'\" ")
        parts = [p.strip("'\" ") for p in inner.split(",") if p.strip("'\" ")]
        raw = parts[0] if parts else ""

    if not raw:
        return ""

    norm = os.path.normpath(raw)
    return os.path.basename(norm) if basename_only else norm


def _is_lock_error(exc: BaseException) -> bool:
    """
    True per qualsiasi errore di I/O che indica file bloccato / non scrivibile
    (PermissionError, WinError 5 accesso negato, WinError 32 sharing violation, altri OSError).
    """
    return isinstance(exc, (PermissionError, OSError))

def _get_unique_fallback_path(target_path: Path) -> Path:
    """
    Genera un nome file univoco con timestamp in caso di file bloccato o PermissionError/WinError 5.
    Formato: report_AR_INV123_YYYYMMDD_HHMMSS.pdf
    Se il nome contiene gia' un timestamp finale questo viene sostituito (non duplicato).
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = _TS_SUFFIX_RE.sub("", target_path.stem)
    ext = target_path.suffix
    parent = target_path.parent
    parent.mkdir(parents=True, exist_ok=True)

    alt_path = parent / f"{stem}_{ts}{ext}"
    counter = 1
    while alt_path.exists() or alt_path == target_path:
        alt_path = parent / f"{stem}_{ts}_{counter}{ext}"
        counter += 1
    return Path(clean_path(alt_path))

def _write_bytes_with_fallback(path: Path, data: bytes) -> Path:
    """Scrive `data` su `path`; se il file e' bloccato salva con timestamp univoco."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_bytes(data)
        return Path(clean_path(path))
    except OSError as e:
        alt = _get_unique_fallback_path(path)
        logger.warning(
            f"[LOCK_RECOVERY] Destinazione '{path.name}' bloccata o aperta da altra applicazione ({e}). "
            f"Salvataggio automatico con timestamp univoco: '{alt.name}'"
        )
        alt.write_bytes(data)
        return Path(clean_path(alt))

# ---------------------------------------------------------------------------
# Import librerie opzionali con fallback
# ---------------------------------------------------------------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.platypus.flowables import KeepTogether
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not available — PDF fallback to plain text")

# ---------------------------------------------------------------------------
# Font Unicode per PDF (accenti à è é ì ò ù ä ö ü ß ñ ç e valute € $ £)
# ---------------------------------------------------------------------------
PDF_FONT_REGULAR = "Helvetica"
PDF_FONT_BOLD = "Helvetica-Bold"
PDF_UNICODE_FONT = False

def _register_pdf_fonts() -> None:
    """Registra una famiglia TrueType Unicode di sistema; fallback su Helvetica (WinAnsi/Latin-1)."""
    global PDF_FONT_REGULAR, PDF_FONT_BOLD, PDF_UNICODE_FONT
    if not REPORTLAB_AVAILABLE:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    win_fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    candidates = [
        (os.path.join(win_fonts, "arial.ttf"), os.path.join(win_fonts, "arialbd.ttf"),
         os.path.join(win_fonts, "ariali.ttf"), os.path.join(win_fonts, "arialbi.ttf")),
        (os.path.join(win_fonts, "segoeui.ttf"), os.path.join(win_fonts, "segoeuib.ttf"),
         os.path.join(win_fonts, "segoeuii.ttf"), os.path.join(win_fonts, "segoeuiz.ttf")),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"),
    ]
    for regular, bold, italic, bold_italic in candidates:
        if not (os.path.isfile(regular) and os.path.isfile(bold)):
            continue
        try:
            pdfmetrics.registerFont(TTFont("ZukSans", regular))
            pdfmetrics.registerFont(TTFont("ZukSans-Bold", bold))
            pdfmetrics.registerFont(TTFont("ZukSans-Italic", italic if os.path.isfile(italic) else regular))
            pdfmetrics.registerFont(TTFont("ZukSans-BoldItalic", bold_italic if os.path.isfile(bold_italic) else bold))
            pdfmetrics.registerFontFamily(
                "ZukSans", normal="ZukSans", bold="ZukSans-Bold",
                italic="ZukSans-Italic", boldItalic="ZukSans-BoldItalic",
            )
            PDF_FONT_REGULAR, PDF_FONT_BOLD, PDF_UNICODE_FONT = "ZukSans", "ZukSans-Bold", True
            logger.info(f"Unicode PDF font registered: {os.path.basename(regular)}")
            return
        except Exception as e:
            logger.warning(f"Font registration '{regular}' failed: {e}")
    logger.warning("No TrueType Unicode font available: using Helvetica (WinAnsi Latin-1)")

_register_pdf_fonts()

def _pdf_text_raw(value) -> str:
    """
    Normalizza un testo per il rendering PDF (senza escape XML, per canvas.drawString):
    - rimuove i glifi emoji/simboli non presenti nei font (⚠ U+26A0 + VS16)
    - con il fallback Helvetica converte garantendo preservazione dei caratteri latini/accentati
    """
    s = "" if value is None else str(value)
    s = s.replace("\u26a0\ufe0f", "(!)").replace("\u26a0", "(!)")
    if not PDF_UNICODE_FONT:
        s = s.encode("latin-1", errors="replace").decode("latin-1")
    return s

def _pdf_text(value) -> str:
    """Testo sanitizzato + escape XML (&, <, >) per Paragraph: evita crash del parser su nomi come 'A & B <srl>'."""
    return _xml_escape(_pdf_text_raw(value))

_CTRL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")

def _clean_strings(obj):
    """Rimuove ricorsivamente i caratteri di controllo non ammessi in XML (DOCX) / PDF."""
    if isinstance(obj, str):
        return _CTRL_CHARS_RE.sub("", obj)
    if isinstance(obj, dict):
        return {k: _clean_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_strings(v) for v in obj]
    return obj


try:
    from docx import Document as DocxDocument
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx not available — DOCX disabled")

# ---------------------------------------------------------------------------
# Costanti e Dizionari Multilingua Completi (6 Lingue: IT, EN, DE, FR, ES, PT)
# ---------------------------------------------------------------------------
BRAND_COLOR_HEX = "#FF6B00"   # Arancione OLTREVISTA
TEXT_COLOR      = "#1A1A1A"
LIGHT_GRAY      = "#F5F5F5"
MEDIUM_GRAY     = "#CCCCCC"

DISCLAIMER_TEXT = {
    "it": "Il software fornisce suggerimenti, non decisioni. Output da verificare prima dell'uso operativo. Nessun dato inviato a server esterni.",
    "en": "This software provides suggestions, not decisions. Output must be verified before operational use. No data sent to external servers.",
    "de": "Diese Software liefert Vorschläge, keine Entscheidungen. Die Ausgabe muss vor dem operativen Einsatz geprüft werden. Keine Daten an externe Server gesendet.",
    "fr": "Ce logiciel fournit des suggestions, pas des décisions. La sortie doit être vérifiée avant utilisation opérationnelle. Aucune donnée envoyée à des serveurs externes.",
    "es": "Este software proporciona sugerencias, no decisiones. La salida debe verificarse antes del uso operativo. Ningún dato enviado a servidores externos.",
    "pt": "Este software fornece sugestões, não decisões. A saída deve ser verificada antes do uso operacional. Nenhum dado enviado a servidores externos.",
}

STATUS_LABELS = {
    "it": {"OVERDUE": "SCADUTA", "PENDING": "IN ATTESA", "PAID": "PAGATA", "DISPUTED": "CONTESTATA", "UNKNOWN": "N/D"},
    "en": {"OVERDUE": "OVERDUE", "PENDING": "PENDING", "PAID": "PAID", "DISPUTED": "DISPUTED", "UNKNOWN": "N/A"},
    "de": {"OVERDUE": "ÜBERFÄLLIG", "PENDING": "AUSSTEHEND", "PAID": "BEZAHLT", "DISPUTED": "BEANSTANDET", "UNKNOWN": "N/B"},
    "fr": {"OVERDUE": "EN RETARD", "PENDING": "EN ATTENTE", "PAID": "PAYÉE", "DISPUTED": "CONTESTÉE", "UNKNOWN": "N/D"},
    "es": {"OVERDUE": "VENCIDA", "PENDING": "PENDIENTE", "PAID": "PAGADA", "DISPUTED": "EN DISPUTA", "UNKNOWN": "N/D"},
    "pt": {"OVERDUE": "VENCIDA", "PENDING": "PENDENTE", "PAID": "PAGA", "DISPUTED": "CONTESTADA", "UNKNOWN": "N/D"},
}

RISK_LABELS = {
    "it": {"LOW": "BASSO", "MEDIUM": "MEDIO", "HIGH": "ALTO", "NONE": "NESSUNO", "UNKNOWN": "N/D"},
    "en": {"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH", "NONE": "NONE", "UNKNOWN": "N/A"},
    "de": {"LOW": "NIEDRIG", "MEDIUM": "MITTEL", "HIGH": "HOCH", "NONE": "KEIN", "UNKNOWN": "N/B"},
    "fr": {"LOW": "FAIBLE", "MEDIUM": "MOYEN", "HIGH": "ÉLEVÉ", "NONE": "AUCUN", "UNKNOWN": "N/D"},
    "es": {"LOW": "BAJO", "MEDIUM": "MEDIO", "HIGH": "ALTO", "NONE": "NINGUNO", "UNKNOWN": "N/D"},
    "pt": {"LOW": "BAIXO", "MEDIUM": "MÉDIO", "HIGH": "ALTO", "NONE": "NENHUM", "UNKNOWN": "N/D"},
}

REPORT_LABELS = {
    "it": {
        "report_title": "Rapporto Analisi Aging Crediti",
        "title": "Dati Fattura",
        "inv_num": "Numero Fattura",
        "issue_date": "Data Emissione",
        "due_date": "Data Scadenza",
        "amount": "Importo",
        "client": "Cliente",
        "client_address": "Indirizzo",
        "status": "Stato Fattura",
        "overdue": "Giorni Scaduta",
        "risk": "Rischio Inesigibilità",
        "reminder_lvl": "Livello Sollecito",
        "rem_title": "Sollecito Generato",
        "recs_title": "Azioni Raccomandate",
        "audit_title": "Riepilogo Elaborazione",
        "no_anomalies": "Nessuna anomalia rilevata.",
        "processed": "Data Generazione",
        "offline_tag": "Dati inviati esternamente: NO | Offline-First",
        "field": "Campo",
        "value": "Valore",
        "notice_prefix": "Livello",
        "software_name": "ZUKWEND — Agente di Fatturazione Multilingua",
        "demo_banner": "",
    },
    "en": {
        "report_title": "Accounts Receivable Aging Report",
        "title": "Invoice Details",
        "inv_num": "Invoice Number",
        "issue_date": "Issue Date",
        "due_date": "Due Date",
        "amount": "Amount",
        "client": "Client",
        "client_address": "Address",
        "status": "Invoice Status",
        "overdue": "Days Overdue",
        "risk": "Bad Debt Risk",
        "reminder_lvl": "Reminder Level",
        "rem_title": "Generated Collection Notice",
        "recs_title": "Recommended Actions",
        "audit_title": "Processing Audit",
        "no_anomalies": "No anomalies detected.",
        "processed": "Generation Date",
        "offline_tag": "Data sent externally: NO | Offline-First",
        "field": "Field",
        "value": "Value",
        "notice_prefix": "Level",
        "software_name": "ZUKWEND — Multilingual Billing Agent",
        "demo_banner": "",
    },
    "de": {
        "report_title": "Debitorenalter-Analysebericht",
        "title": "Rechnungsdaten",
        "inv_num": "Rechnungsnummer",
        "issue_date": "Rechnungsdatum",
        "due_date": "Fälligkeitsdatum",
        "amount": "Betrag",
        "client": "Kunde",
        "client_address": "Adresse",
        "status": "Rechnungsstatus",
        "overdue": "Tage überfällig",
        "risk": "Ausfallrisiko",
        "reminder_lvl": "Mahnstufe",
        "rem_title": "Erstelltes Mahnschreiben",
        "recs_title": "Empfohlene Massnahmen",
        "audit_title": "Verarbeitungsprotokoll",
        "no_anomalies": "Keine Unregelmäßigkeiten festgestellt.",
        "processed": "Erstellungsdatum",
        "offline_tag": "Daten extern gesendet: NEIN | Offline-First",
        "field": "Feld",
        "value": "Wert",
        "notice_prefix": "Stufe",
        "software_name": "ZUKWEND — Mehrsprachiger Rechnungsagent",
        "demo_banner": "",
    },
    "fr": {
        "report_title": "Rapport d'Analyse de Solvabilité",
        "title": "Détails de la Facture",
        "inv_num": "Numéro de Facture",
        "issue_date": "Date d'Émission",
        "due_date": "Date d'Échéance",
        "amount": "Montant",
        "client": "Client",
        "client_address": "Adresse",
        "status": "Statut de la Facture",
        "overdue": "Jours de Retard",
        "risk": "Risque d'Insolvabilité",
        "reminder_lvl": "Niveau de Relance",
        "rem_title": "Relance Générée",
        "recs_title": "Actions Recommandées",
        "audit_title": "Journal de Traitement",
        "no_anomalies": "Aucune anomalie détectée.",
        "processed": "Date de Génération",
        "offline_tag": "Données envoyées à l'extérieur : NON | Offline-First",
        "field": "Champ",
        "value": "Valeur",
        "notice_prefix": "Niveau",
        "software_name": "ZUKWEND — Agent de Facturation Multilingue",
        "demo_banner": "",
    },
    "es": {
        "report_title": "Informe de Análisis de Vencimientos",
        "title": "Datos de la Factura",
        "inv_num": "Número de Factura",
        "issue_date": "Fecha de Emisión",
        "due_date": "Fecha de Vencimiento",
        "amount": "Importe",
        "client": "Cliente",
        "client_address": "Dirección",
        "status": "Estado de la Factura",
        "overdue": "Días Vencida",
        "risk": "Riesgo de Impago",
        "reminder_lvl": "Nivel de Reclamación",
        "rem_title": "Aviso de Pago Generado",
        "recs_title": "Acciones Recomendadas",
        "audit_title": "Registro de Procesamiento",
        "no_anomalies": "No se detectaron anomalías.",
        "processed": "Fecha de Generación",
        "offline_tag": "Datos enviados externamente: NO | Offline-First",
        "field": "Campo",
        "value": "Valor",
        "notice_prefix": "Nivel",
        "software_name": "ZUKWEND — Agente de Facturación Multilingüe",
        "demo_banner": "",
    },
    "pt": {
        "report_title": "Relatório de Análise de Aging",
        "title": "Dados da Fatura",
        "inv_num": "Número da Fatura",
        "issue_date": "Data de Emissão",
        "due_date": "Data de Vencimento",
        "amount": "Valor",
        "client": "Cliente",
        "client_address": "Endereço",
        "status": "Estado da Fatura",
        "overdue": "Dias em Atraso",
        "risk": "Risco de Inadimplência",
        "reminder_lvl": "Nível de Cobrança",
        "rem_title": "Aviso de Cobrança Gerado",
        "recs_title": "Ações Recomendadas",
        "audit_title": "Registo de Processamento",
        "no_anomalies": "Nenhuma anomalia detetada.",
        "processed": "Data de Geração",
        "offline_tag": "Dados enviados externamente: NÃO | Offline-First",
        "field": "Campo",
        "value": "Valor",
        "notice_prefix": "Nível",
        "software_name": "ZUKWEND — Agente de Faturação Multilíngue",
        "demo_banner": "",
    },
}

RECOMMENDATIONS_I18N = {
    "it": {
        "threshold": "Importo superiore alla soglia di conformità: richiesta autorizzazione.",
        "legal": "Sollecito livello 3: consultare l'ufficio legale prima di un'azione formale.",
        "overdue_90": "Scaduta da oltre 90 giorni: valutare recupero crediti o svalutazione.",
        "kyc": "Importo elevato: verificare le procedure antiriciclaggio KYC/AML.",
        "none": "Nessuna anomalia rilevata."
    },
    "en": {
        "threshold": "Amount exceeds compliance threshold: authorization required.",
        "legal": "Notice level 3: consult legal counsel prior to formal escalation.",
        "overdue_90": "Overdue exceeds 90 days: evaluate debt recovery or bad debt provisioning.",
        "kyc": "High value amount: verify KYC/AML procedures.",
        "none": "No anomalies detected."
    },
    "de": {
        "threshold": "Betrag überschreitet Compliance-Schwelle: Genehmigung erforderlich.",
        "legal": "Mahnstufe 3: Vor formellen Schritten Rechtsberatung hinzuziehen.",
        "overdue_90": "Über 90 Tage überfällig: Inkassoverfahren oder Wertberichtigung prüfen.",
        "kyc": "Hoher Betrag: KYC/AML-Compliance-Verfahren überprüfen.",
        "none": "Keine Unregelmäßigkeiten festgestellt."
    },
    "fr": {
        "threshold": "Montant supérieur au seuil de conformité : autorisation requise.",
        "legal": "Relance niveau 3 : consulter le service juridique avant toute procédure formelle.",
        "overdue_90": "Retard supérieur à 90 jours : évaluer le recouvrement ou la provision pour créance douteuse.",
        "kyc": "Montant élevé : vérifier les procédures de conformité KYC/AML.",
        "none": "Aucune anomalie détectée."
    },
    "es": {
        "threshold": "Importe superior al umbral de cumplimiento: autorización requerida.",
        "legal": "Nivel de reclamación 3: consultar con asesoría jurídica antes de proceder formalmente.",
        "overdue_90": "Vencimiento superior a 90 días: evaluar cobro de deudas o provisión por insolvencia.",
        "kyc": "Importe elevado: verificar procedimientos KYC/AML.",
        "none": "No se detectaron anomalías."
    },
    "pt": {
        "threshold": "Valor excede o limite de conformidade: autorização necessária.",
        "legal": "Aviso nível 3: consultar o departamento jurídico antes de qualquer ação formal.",
        "overdue_90": "Vencimento superior a 90 dias: avaliar recuperação de crédito ou imparidade.",
        "kyc": "Valor elevado: verificar procedimentos KYC/AML.",
        "none": "Nenhuma anomalia detetada."
    }
}

# ---------------------------------------------------------------------------
# Funzione principale: generate()
# ---------------------------------------------------------------------------
def generate(
    invoice: dict,
    classification: dict,
    compliance: dict,
    billing: dict,
    reminder_text: str,
    language: str = "it",
    output_dir: Optional[str] = None,
    formats: Optional[list] = None,
    is_demo: bool = False,
) -> dict:
    if formats is None:
        formats = ["pdf"]

    lang_code = language.lower() if language else "en"
    if lang_code not in REPORT_LABELS:
        lang_code = "en"

    default_output = get_output_dir()
    if output_dir and not _is_inside_meipass(str(output_dir)):
        out_dir = Path(clean_path(output_dir))
    else:
        out_dir = Path(clean_path(default_output))
    out_dir.mkdir(parents=True, exist_ok=True)

    inv_num_raw = str(invoice.get("invoice_number") or "UNKNOWN")
    inv_num = re.sub(r"[^\w.\-]+", "-", inv_num_raw).strip("-.") or "UNKNOWN"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"report_AR_{inv_num}_{timestamp}"

    paths = {}
    errors = []

    report_data = _clean_strings(
        _build_report_data(invoice, classification, compliance, billing, reminder_text, lang_code, is_demo)
    )

    for fmt in formats:
        fmt = fmt.lower().strip()
        try:
            if fmt == "pdf":
                p = _generate_pdf(report_data, out_dir / f"{base_name}.pdf", is_demo)
                paths["pdf"] = clean_path(p)
            elif fmt == "docx":
                p = _generate_docx(report_data, out_dir / f"{base_name}.docx", is_demo)
                paths["docx"] = clean_path(p)
            elif fmt == "json":
                p = _generate_json(report_data, out_dir / f"{base_name}.json")
                paths["json"] = clean_path(p)
            elif fmt == "html":
                p = _generate_html(report_data, out_dir / f"{base_name}.html", is_demo)
                paths["html"] = clean_path(p)
            else:
                logger.warning(f"Unsupported format: {fmt}")
                errors.append(f"unsupported_format:{fmt}")
        except (PermissionError, OSError) as e:
            if _is_lock_error(e):
                logger.error(
                    f"[LOCK_ERROR] Permission error or file locked (WinError 5 / PermissionError) "
                    f"during generation of {fmt}: {e}."
                )
                errors.append(f"file_locked:{fmt}:{e}")
            else:
                logger.error(f"Error generating {fmt}: {e}")
                errors.append(f"{fmt}:{e}")
        except Exception as e:
            logger.error(f"Error generating {fmt}: {e}")
            errors.append(f"{fmt}:{e}")

    clean_out_dir = clean_path(out_dir)
    logger.info(f"Reports generated: {list(paths.keys())} in {clean_out_dir}")
    return {
        "paths": paths,
        "base_name": base_name,
        "output_dir": clean_out_dir,
        "errors": errors
    }

def _clean_layout_tokens(raw: Optional[str]) -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    pattern = r"(?i)\s*[\-_|/:]*\s*\b(?:invoice|facture|rechnung|page|fattura|fatura)\b.*$"
    s = re.sub(pattern, "", s)
    s = re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", s)
    return re.sub(r"\s+", " ", s).strip()

# ---------------------------------------------------------------------------
# Builder dati report
# ---------------------------------------------------------------------------
def _build_report_data(invoice, classification, compliance, billing, reminder_text, language, is_demo):
    lang_code = (language or "en").lower()
    if lang_code not in REPORT_LABELS:
        lang_code = "en"

    labels = REPORT_LABELS.get(lang_code, REPORT_LABELS["en"])

    risk_map = RISK_LABELS.get(lang_code, RISK_LABELS["en"])
    risk_raw = str(classification.get("risk_level", "UNKNOWN")).upper()
    risk_label = risk_map.get(risk_raw, risk_raw)

    status_map = STATUS_LABELS.get(lang_code, STATUS_LABELS["en"])
    status_raw = str(classification.get("payment_status", "UNKNOWN")).upper()
    status_label = status_map.get(status_raw, status_raw)

    safe_amount = float(invoice.get("amount") or 0.0)

    recommendations = compliance.get("recommendations", [])
    rec_dict = RECOMMENDATIONS_I18N.get(lang_code, RECOMMENDATIONS_I18N["en"])
    translated_recs = []
    for rec in recommendations:
        rec_str = str(rec).strip()
        if "superiore alla soglia" in rec_str or "exceeds compliance threshold" in rec_str or "Compliance-Schwelle" in rec_str:
            translated_recs.append(rec_dict["threshold"])
        elif ("consultare" in rec_str or "consult legal" in rec_str or "Rechtsberatung" in rec_str) and ("legale" in rec_str or "diffida" in rec_str or "3" in rec_str):
            translated_recs.append(rec_dict["legal"])
        elif "90" in rec_str and ("giorni" in rec_str or "days" in rec_str or "Tage" in rec_str or "jours" in rec_str or "días" in rec_str or "dias" in rec_str):
            translated_recs.append(rec_dict["overdue_90"])
        elif "KYC" in rec_str or "AML" in rec_str or "Importo elevato" in rec_str or "High value" in rec_str:
            translated_recs.append(rec_dict["kyc"])
        elif "Nessuna anomalia" in rec_str or "No anomalies" in rec_str or "Keine Unregelmäßigkeiten" in rec_str:
            translated_recs.append(rec_dict["none"])
        else:
            translated_recs.append(rec_str)

    if not translated_recs:
        translated_recs = [rec_dict["none"]]

    client_name = _clean_layout_tokens(invoice.get("client_name") or "N/A")
    client_address = _clean_layout_tokens(invoice.get("client_address") or invoice.get("address") or "")
    vendor_name = _clean_layout_tokens(invoice.get("vendor_name") or "N/A")

    return {
        "generated_at": datetime.now().isoformat(),
        "software": labels["software_name"],
        "version": APP_VERSION,
        "language": lang_code,
        "labels": labels,
        "is_demo": is_demo,
        "invoice": {
            "number":         str(invoice.get("invoice_number") or "N/A"),
            "issue_date":     str(invoice.get("issue_date") or "N/A"),
            "due_date":       str(invoice.get("due_date") or "N/A"),
            "amount":         safe_amount,
            "currency":       str(invoice.get("currency") or "EUR"),
            "client":         client_name or "N/A",
            "client_address": client_address,
            "vendor":         vendor_name or "N/A",
        },
        "classification": {
            "payment_status":     status_label,
            "payment_status_raw": status_raw,
            "days_overdue":       int(classification.get("days_overdue") or 0),
            "risk_level_raw":     risk_raw,
            "risk_level_label":   risk_label,
            "reminder_level":     int(classification.get("reminder_level") or 1),
            "compliance_flag":    bool(classification.get("compliance_flag") or False),
            "rationale":          str(classification.get("classification_rationale") or ""),
            "next_escalation":    str(classification.get("next_escalation_date") or "N/A"),
        },
        "compliance": {
            "flags":           compliance.get("flags", []),
            "recommendations": translated_recs,
            "disclaimer":       str(compliance.get("disclaimer") or DISCLAIMER_TEXT.get(lang_code, DISCLAIMER_TEXT["en"])),
        },
        "billing": {
            "action":     str(billing.get("action") or "N/A"),
            "channel":    str(billing.get("recommended_channel") or "N/A"),
            "grace_days": int(billing.get("grace_days") or 5),
        },
        "reminder_text": str(reminder_text or ""),
        "audit": {
            "processed_at": datetime.now().isoformat(),
            "software_version": APP_VERSION,
            "is_demo": is_demo,
            "data_sent_externally": False,
            "disclaimer": DISCLAIMER_TEXT.get(lang_code, DISCLAIMER_TEXT["en"]),
        },
    }

# ---------------------------------------------------------------------------
# Generatore PDF (ReportLab con fallback testuale UTF-8)
# ---------------------------------------------------------------------------
def _generate_pdf(data: dict, path: Path, is_demo: bool = False) -> Path:
    if REPORTLAB_AVAILABLE:
        return _generate_pdf_reportlab(data, path, is_demo)
    else:
        return _generate_pdf_text_fallback(data, path, is_demo)

def _generate_pdf_reportlab(data: dict, path: Path, is_demo: bool) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    for _st in styles.byName.values():
        _is_bold = "bold" in str(getattr(_st, "fontName", "")).lower()
        _st.fontName = PDF_FONT_BOLD if _is_bold else PDF_FONT_REGULAR

    brand_color = colors.HexColor(BRAND_COLOR_HEX)
    labels = data["labels"]
    story = []

    title_style = ParagraphStyle(
        "ZTitle", parent=styles["Title"],
        textColor=brand_color, fontSize=16, spaceAfter=4,
        fontName=PDF_FONT_BOLD
    )
    story.append(Paragraph(_pdf_text(labels["software_name"]), title_style))
    story.append(Paragraph(_pdf_text(f"{labels['report_title']} | {data['generated_at'][:10]}"), styles["Normal"]))
    story.append(HRFlowable(width="100%", thickness=1, color=brand_color, spaceAfter=8))

    inv = data["invoice"]
    clf = data["classification"]
    story.append(Paragraph(_pdf_text(labels["title"]), styles["Heading2"]))
    table_data = [
        [labels["inv_num"],      inv["number"]],
        [labels["issue_date"],   inv["issue_date"]],
        [labels["due_date"],     inv["due_date"]],
        [labels["amount"],       f"{inv['currency']} {inv['amount']:,.2f}"],
        [labels["client"],       inv["client"]],
    ]
    if inv.get("client_address"):
        table_data.append([labels["client_address"], inv["client_address"]])
    table_data.extend([
        [labels["status"],       clf["payment_status"]],
        [labels["overdue"],      str(clf["days_overdue"])],
        [labels["risk"],         clf["risk_level_label"]],
        [labels["reminder_lvl"], f"{labels['notice_prefix']} {clf['reminder_level']}"],
    ])
    cell_style = ParagraphStyle("ZCell", parent=styles["Normal"], fontSize=10, leading=12)
    table_cells = [[Paragraph(_pdf_text(k), cell_style), Paragraph(_pdf_text(v), cell_style)]
                   for k, v in table_data]
    t = Table(table_cells, colWidths=[5.5*cm, 10.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor(LIGHT_GRAY)),
        ("FONTNAME", (0,0), (-1,-1), PDF_FONT_REGULAR),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor(MEDIUM_GRAY)),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor(LIGHT_GRAY)]),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph(_pdf_text(labels["rem_title"]), styles["Heading2"]))
    for line in data["reminder_text"].split("\n"):
        if line.strip():
            story.append(Paragraph(_pdf_text(line), styles["Normal"]))
        else:
            story.append(Spacer(1, 0.2*cm))
    story.append(Spacer(1, 0.5*cm))

    if data["compliance"]["recommendations"]:
        story.append(Paragraph(_pdf_text(labels["recs_title"]), styles["Heading2"]))
        for rec in data["compliance"]["recommendations"]:
            story.append(Paragraph(_pdf_text(f"• {rec}"), styles["Normal"]))
        story.append(Spacer(1, 0.3*cm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(MEDIUM_GRAY), spaceAfter=4))
    audit_style = ParagraphStyle("Audit", parent=styles["Normal"], fontSize=8, textColor=colors.gray)
    story.append(Paragraph(_pdf_text(f"{labels['processed']}: {data['audit']['processed_at']} | {data['software']} {data['version']}"), audit_style))
    story.append(Paragraph(_pdf_text(labels["offline_tag"]), audit_style))
    story.append(Spacer(1, 0.2*cm))

    disc_style = ParagraphStyle("Disc", parent=styles["Normal"], fontSize=8,
                                 textColor=colors.gray, borderPadding=4)
    story.append(Paragraph(_pdf_text(data["audit"]["disclaimer"]), disc_style))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    saved_path = _write_bytes_with_fallback(path, pdf_bytes)
    logger.info(f"PDF generated: {clean_path(saved_path)}")
    return Path(clean_path(saved_path))

def _generate_pdf_text_fallback(data: dict, path: Path, is_demo: bool) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    txt_path = path.with_suffix(".txt")
    content = _build_text_report(data, is_demo)
    target_path = txt_path
    try:
        target_path.write_text(content, encoding="utf-8")
    except (PermissionError, OSError) as e:
        if _is_lock_error(e):
            target_path = _get_unique_fallback_path(txt_path)
            logger.warning(
                f"[LOCK_RECOVERY] TXT destination '{txt_path.name}' locked ({e}). "
                f"Saving to '{target_path.name}'"
            )
            target_path.write_text(content, encoding="utf-8")
        else:
            raise e
    logger.warning(f"PDF fallback (text): {clean_path(target_path)}")
    return Path(clean_path(target_path))

def _build_text_report(data: dict, is_demo: bool) -> str:
    sep = "=" * 60
    inv = data["invoice"]
    clf = data["classification"]
    labels = data["labels"]
    lines = [
        sep,
        labels["software_name"],
        f"{labels['report_title']} | {data['generated_at'][:10]}",
        sep,
        labels["title"].upper(),
        f"  {labels['inv_num']}:     {inv['number']}",
        f"  {labels['due_date']}:    {inv['due_date']}",
        f"  {labels['amount']}:      {inv['currency']} {inv['amount']:,.2f}",
        f"  {labels['client']}:      {inv['client']}",
    ] + ([f"  {labels['client_address']}:     {inv['client_address']}"] if inv.get("client_address") else []) + [
        f"  {labels['status']}:      {clf['payment_status']} ({clf['days_overdue']})",
        f"  {labels['risk']}:        {clf['risk_level_label']} | {labels['notice_prefix']} {clf['reminder_level']}",
        sep,
        labels["rem_title"].upper(),
        data["reminder_text"],
        sep,
        labels["recs_title"].upper(),
    ] + [f"  • {r}" for r in data["compliance"]["recommendations"]] + [
        sep,
        f"{labels['processed']}: {data['audit']['processed_at']}",
        data["audit"]["disclaimer"],
        sep,
    ]
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Generatore DOCX
# ---------------------------------------------------------------------------
def _generate_docx(data: dict, path: Path, is_demo: bool = False) -> Path:
    if not DOCX_AVAILABLE:
        raise RuntimeError("python-docx non disponibile")

    labels = data["labels"]
    doc = DocxDocument()
    inv = data["invoice"]
    clf = data["classification"]

    title = doc.add_heading(labels["software_name"], level=1)
    title.runs[0].font.color.rgb = RGBColor(0xFF, 0x6B, 0x00)
    doc.add_paragraph(f"{labels['report_title']} | {data['generated_at'][:10]}")

    doc.add_heading(labels["title"], level=2)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = labels["field"]
    hdr[1].text = labels["value"]
    rows = [
        (labels["inv_num"],      inv["number"]),
        (labels["issue_date"],   str(inv["issue_date"])),
        (labels["due_date"],     str(inv["due_date"])),
        (labels["amount"],       f"{inv['currency']} {inv['amount']:,.2f}"),
        (labels["client"],       inv["client"]),
    ] + ([(labels["client_address"], inv["client_address"])] if inv.get("client_address") else []) + [
        (labels["status"],       clf["payment_status"]),
        (labels["overdue"],      str(clf["days_overdue"])),
        (labels["risk"],         clf["risk_level_label"]),
        (labels["reminder_lvl"], f"{labels['notice_prefix']} {clf['reminder_level']}"),
    ]
    for field, value in rows:
        row = table.add_row().cells
        row[0].text = field
        row[1].text = str(value)

    doc.add_heading(labels["rem_title"], level=2)
    doc.add_paragraph(data["reminder_text"])

    doc.add_heading(labels["recs_title"], level=2)
    for rec in data["compliance"]["recommendations"]:
        doc.add_paragraph(f"• {rec}")

    doc.add_heading(labels["audit_title"], level=3)
    audit_para = doc.add_paragraph(
        f"{labels['processed']}: {data['audit']['processed_at']} | {data['software']}\n"
        f"{labels['offline_tag']}"
    )
    audit_para.runs[0].font.size = Pt(9)

    disclaimer = doc.add_paragraph(data["audit"]["disclaimer"])
    disclaimer.runs[0].font.size = Pt(9)
    disclaimer.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    path.parent.mkdir(parents=True, exist_ok=True)
    target_path = path
    try:
        doc.save(str(target_path))
    except (PermissionError, OSError) as e:
        if _is_lock_error(e):
            target_path = _get_unique_fallback_path(path)
            logger.warning(
                f"[LOCK_RECOVERY] DOCX destination '{path.name}' locked ({e}). "
                f"Saving to '{target_path.name}'"
            )
            doc.save(str(target_path))
        else:
            raise e
    clean_docx = clean_path(target_path)
    logger.info(f"DOCX generated: {clean_docx}")
    return Path(clean_docx)

# ---------------------------------------------------------------------------
# Generatore JSON
# ---------------------------------------------------------------------------
def _generate_json(data: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    json_out = {
        "zukwend_version": data["version"],
        "generated_at": data["generated_at"],
        "language": data["language"],
        "report_title": data["labels"]["report_title"],
        "invoice": data["invoice"],
        "classification": data["classification"],
        "compliance": data["compliance"],
        "billing": data["billing"],
        "reminder_text": data["reminder_text"],
        "audit": data["audit"],
    }
    content = json.dumps(json_out, indent=2, ensure_ascii=False)
    target_path = path
    try:
        target_path.write_text(content, encoding="utf-8")
    except (PermissionError, OSError) as e:
        if _is_lock_error(e):
            target_path = _get_unique_fallback_path(path)
            logger.warning(
                f"[LOCK_RECOVERY] JSON destination '{path.name}' locked ({e}). "
                f"Saving to '{target_path.name}'"
            )
            target_path.write_text(content, encoding="utf-8")
        else:
            raise e
    clean_json = clean_path(target_path)
    logger.info(f"JSON generated: {clean_json}")
    return Path(clean_json)

# ---------------------------------------------------------------------------
# Generatore HTML
# ---------------------------------------------------------------------------
def _generate_html(data: dict, path: Path, is_demo: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    def _esc_map(src: dict) -> dict:
        return {k: (_html.escape(v, quote=False) if isinstance(v, str) else v) for k, v in src.items()}

    inv = _esc_map(data["invoice"])
    clf = _esc_map(data["classification"])
    labels = _esc_map(data["labels"])
    data = {**data, "audit": _esc_map(data["audit"])}
    risk_class = {"LOW": "risk-low", "MEDIUM": "risk-medium", "HIGH": "risk-high"}.get(
        data["classification"]["risk_level_raw"], ""
    )
    recs_html = "".join(f"<li>{_html.escape(str(r))}</li>" for r in data["compliance"]["recommendations"])
    reminder_html = _html.escape(data["reminder_text"]).replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html lang="{data['language']}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{labels['report_title']} — ZUKWEND</title>
  <style>
    body {{ font-family: Calibri, 'Segoe UI', sans-serif; color: #1a1a1a; margin: 0; padding: 20px; background: #f9f9f9; }}
    .header {{ background: #ff6b00; color: white; padding: 20px 24px; border-radius: 6px 6px 0 0; }}
    .header h1 {{ margin: 0; font-size: 1.4em; }}
    .header p  {{ margin: 4px 0 0; font-size: 0.9em; opacity: 0.9; }}
    .container {{ background: white; border: 1px solid #e0e0e0; border-radius: 0 0 6px 6px; padding: 24px; }}
    .section-title {{ color: #ff6b00; border-bottom: 2px solid #ff6b00; padding-bottom: 4px; margin-top: 24px; font-size: 1.1em; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ padding: 8px 12px; text-align: left; border: 1px solid #e0e0e0; font-size: 0.95em; }}
    th {{ background: #f5f5f5; font-weight: bold; width: 35%; }}
    .risk-low    {{ color: #28a745; font-weight: bold; }}
    .risk-medium {{ color: #ffc107; font-weight: bold; }}
    .risk-high   {{ color: #dc3545; font-weight: bold; }}
    .reminder-box {{ background: #f9f4ef; border-left: 4px solid #ff6b00; padding: 16px; margin-top: 12px; border-radius: 0 4px 4px 0; font-size: 0.95em; line-height: 1.6; }}
    .disclaimer {{ font-size: 0.82em; color: #888; margin-top: 20px; border-top: 1px solid #eee; padding-top: 12px; }}
    .audit {{ font-size: 0.82em; color: #aaa; margin-top: 8px; }}
    ul {{ padding-left: 20px; }}
    li {{ margin-bottom: 4px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>{labels['software_name']}</h1>
    <p>{labels['report_title']} | {data['generated_at'][:10]} | {data['version']}</p>
  </div>
  <div class="container">
    <div class="section-title">{labels['title']}</div>
    <table>
      <tr><th>{labels['inv_num']}</th><td>{inv['number']}</td></tr>
      <tr><th>{labels['issue_date']}</th><td>{inv['issue_date']}</td></tr>
      <tr><th>{labels['due_date']}</th><td>{inv['due_date']}</td></tr>
      <tr><th>{labels['amount']}</th><td><strong>{inv['currency']} {inv['amount']:,.2f}</strong></td></tr>
      <tr><th>{labels['client']}</th><td>{inv['client']}</td></tr>
      {f"<tr><th>{labels['client_address']}</th><td>{inv['client_address']}</td></tr>" if inv.get("client_address") else ""}
      <tr><th>{labels['status']}</th><td>{clf['payment_status']}</td></tr>
      <tr><th>{labels['overdue']}</th><td>{clf['days_overdue']}</td></tr>
      <tr><th>{labels['risk']}</th><td class="{risk_class}">{clf['risk_level_label']}</td></tr>
      <tr><th>{labels['reminder_lvl']}</th><td>{labels['notice_prefix']} {clf['reminder_level']}</td></tr>
    </table>
    <div class="section-title">{labels['rem_title']}</div>
    <div class="reminder-box">{reminder_html}</div>
    <div class="section-title">{labels['recs_title']}</div>
    <ul>{recs_html}</ul>
    <div class="disclaimer">{data['audit']['disclaimer']}</div>
    <div class="audit">
      {labels['processed']}: {data['audit']['processed_at']} | {labels['offline_tag']}
    </div>
  </div>
</body>
</html>"""

    target_path = path
    try:
        target_path.write_text(html, encoding="utf-8")
    except (PermissionError, OSError) as e:
        if _is_lock_error(e):
            target_path = _get_unique_fallback_path(path)
            logger.warning(
                f"[LOCK_RECOVERY] HTML destination '{path.name}' locked ({e}). "
                f"Saving to '{target_path.name}'"
            )
            target_path.write_text(html, encoding="utf-8")
        else:
            raise e
    clean_html = clean_path(target_path)
    logger.info(f"HTML generated: {clean_html}")
    return Path(clean_html)
