"""
ZUKWEND — Multilingual Billing Agent
Modulo: deducer.py
Versione: 2.1.0-ENTERPRISE (Full 6-Language Native Edition)
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import json
import logging
import re
import requests
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from i18n_catalog import normalize_lang, get_text, get_channel_label, get_legal_disclaimer, format_human_date

try:
    from resource_utils import get_resource_path, is_local_llm_available
except ImportError:  # pragma: no cover - esecuzione isolata del modulo
    def get_resource_path(relative_path: str) -> str:
        return str(Path(__file__).parent / relative_path)

    def is_local_llm_available(*_args, **_kwargs) -> bool:
        return True

logger = logging.getLogger("zukwend.deducer")

TEMPLATE_DIR = Path(__file__).parent.parent / "billing" / "templates"

LEVEL_CHANNELS = {
    1: "email",
    2: "certified_email",
    3: "registered_mail",
}

LEVEL_GRACE_DAYS = {
    1: 5,
    2: 3,
    3: 7,
}

SUPPORTED_LANGS = ["it", "en", "fr", "de", "es", "pt"]

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

# Matrice Completa Template Deterministici (6 Lingue x 3 Livelli)
STATIC_TEMPLATES = {
    # ITALIANO
    ("it", 1): (
        "OGGETTO: Sollecito di pagamento fattura n. {invoice_number} - {client_name}\n\n"
        "CORPO:\n"
        "Gentile {client_name},\n"
        "La fattura n. {invoice_number}, emessa il {issue_date} per {currency} {amount}, è scaduta il {due_date}.\n"
        "La invitiamo a procedere al pagamento entro {grace_days} giorni lavorativi."
    ),
    ("it", 2): (
        "OGGETTO: Secondo sollecito di pagamento fattura n. {invoice_number} - {client_name}\n\n"
        "CORPO:\n"
        "Gentile {client_name},\n"
        "La fattura n. {invoice_number} ({currency} {amount}), scaduta il {due_date}, risulta ancora non saldata da {days_overdue} giorni.\n"
        "La invitiamo a saldare entro {grace_days} giorni per evitare ulteriori azioni."
    ),
    ("it", 3): (
        "OGGETTO: Diffida formale e messa in mora - Fattura n. {invoice_number}\n\n"
        "CORPO:\n"
        "Gentile {client_name},\n"
        "La diffidiamo a saldare la fattura n. {invoice_number} "
        "({currency} {amount}), scaduta il {due_date} ({days_overdue} giorni fa), "
        "entro {grace_days} giorni, pena il ricorso alle vie legali."
    ),
    # ENGLISH
    ("en", 1): (
        "SUBJECT: Payment Reminder: Invoice no. {invoice_number} - {client_name}\n\n"
        "BODY:\n"
        "Dear {client_name},\n"
        "Invoice no. {invoice_number} for {currency} {amount} (due {due_date}) remains unpaid.\n"
        "We kindly ask you to arrange payment within {grace_days} business days."
    ),
    ("en", 2): (
        "SUBJECT: Overdue Notice: Invoice no. {invoice_number} - {client_name}\n\n"
        "BODY:\n"
        "Dear {client_name},\n"
        "Despite our previous notice, invoice no. {invoice_number} ({currency} {amount}) "
        "due on {due_date} is overdue by {days_overdue} days.\n"
        "Please settle within {grace_days} days to prevent further escalation."
    ),
    ("en", 3): (
        "SUBJECT: Formal Collection Notice: Invoice no. {invoice_number}\n\n"
        "BODY:\n"
        "Dear {client_name},\n"
        "You are formally required to settle invoice no. {invoice_number} "
        "({currency} {amount}), overdue by {days_overdue} days, within {grace_days} days. "
        "Failure to comply will result in immediate legal action."
    ),
    # DEUTSCH
    ("de", 1): (
        "BETREFF: Zahlungserinnerung: Rechnung Nr. {invoice_number} - {client_name}\n\n"
        "TEXT:\n"
        "Sehr geehrte(r) {client_name},\n"
        "die Rechnung Nr. {invoice_number} über {currency} {amount} (Fälligkeit: {due_date}) ist noch offen.\n"
        "Bitte überweisen Sie den Betrag innerhalb von {grace_days} Werktagen."
    ),
    ("de", 2): (
        "BETREFF: Zweite Mahnung: Rechnung Nr. {invoice_number} - {client_name}\n\n"
        "TEXT:\n"
        "Sehr geehrte(r) {client_name},\n"
        "trotz Mahnung ist die Rechnung Nr. {invoice_number} über {currency} {amount} "
        "seit {days_overdue} Tagen überfällig.\n"
        "Bitte begleichen Sie die Forderung innerhalb von {grace_days} Tagen."
    ),
    ("de", 3): (
        "BETREFF: Letzte Mahnung vor rechtlichen Schritten: Rechnung Nr. {invoice_number}\n\n"
        "TEXT:\n"
        "Sehr geehrte(r) {client_name},\n"
        "Sie werden aufgefordert, die Rechnung Nr. {invoice_number} ({currency} {amount}) "
        "binnen {grace_days} Tagen zu begleichen. Andernfalls werden unverzüglich rechtliche Schritte eingeleitet."
    ),
    # FRANÇAIS
    ("fr", 1): (
        "OBJET: Relance de paiement : Facture n° {invoice_number} - {client_name}\n\n"
        "CORPS:\n"
        "Bonjour {client_name},\n"
        "La facture n° {invoice_number} d'un montant de {currency} {amount} "
        "(échéance le {due_date}) demeure impayée.\n"
        "Merci de procéder au règlement sous {grace_days} jours ouvrés."
    ),
    ("fr", 2): (
        "OBJET: Deuxième rappel de paiement : Facture n° {invoice_number} - {client_name}\n\n"
        "CORPS:\n"
        "Bonjour {client_name},\n"
        "Sauf erreur, la facture n° {invoice_number} ({currency} {amount}) "
        "est en retard de {days_overdue} jours.\n"
        "Merci de régulariser la situation sous {grace_days} jours."
    ),
    ("fr", 3): (
        "OBJET: Mise en demeure formelle : Facture n° {invoice_number}\n\n"
        "CORPS:\n"
        "Bonjour {client_name},\n"
        "Nous vous mettons en demeure de régler la facture n° {invoice_number} "
        "({currency} {amount}) sous {grace_days} jours. À défaut, une procédure contentieuse sera engagée."
    ),
    # ESPAÑOL
    ("es", 1): (
        "ASUNTO: Recordatorio de pago: Factura n.° {invoice_number} - {client_name}\n\n"
        "CUERPO:\n"
        "Estimado/a {client_name},\n"
        "La factura n.° {invoice_number} por importe de {currency} {amount} "
        "(vencimiento el {due_date}) se encuentra pendiente de pago.\n"
        "Le rogamos efectúe el abono en un plazo de {grace_days} días hábiles."
    ),
    ("es", 2): (
        "ASUNTO: Segundo aviso de vencimiento: Factura n.° {invoice_number} - {client_name}\n\n"
        "CUERPO:\n"
        "Estimado/a {client_name},\n"
        "A pesar de nuestros avisos, la factura n.° {invoice_number} ({currency} {amount}) "
        "acumula {days_overdue} días de retraso.\n"
        "Rogamos regularice la situación en {grace_days} días."
    ),
    ("es", 3): (
        "ASUNTO: Requerimiento formal de pago: Factura n.° {invoice_number}\n\n"
        "CUERPO:\n"
        "Estimado/a {client_name},\n"
        "Le requerimos formalmente el pago de la factura n.° {invoice_number} "
        "({currency} {amount}) en el plazo improrrogable de {grace_days} días, bajo apercibimiento de acciones legales."
    ),
    # PORTUGUÊS
    ("pt", 1): (
        "ASSUNTO: Lembrete de pagamento: Fatura n.º {invoice_number} - {client_name}\n\n"
        "CORPO:\n"
        "Prezado(a) {client_name},\n"
        "A fatura n.º {invoice_number} no valor de {currency} {amount} "
        "(com vencimento a {due_date}) permanece em aberto.\n"
        "Solicitamos a regularização no prazo de {grace_days} dias úteis."
    ),
    ("pt", 2): (
        "ASSUNTO: Segundo aviso de cobrança: Fatura n.º {invoice_number} - {client_name}\n\n"
        "CORPO:\n"
        "Prezado(a) {client_name},\n"
        "Apesar dos contactos anteriores, a fatura n.º {invoice_number} ({currency} {amount}) "
        "encontra-se vencida há {days_overdue} dias.\n"
        "Pedimos a liquidação no prazo de {grace_days} dias para evitar procedimentos adicionais."
    ),
    ("pt", 3): (
        "ASSUNTO: Notificação formal de cobrança: Fatura n.º {invoice_number}\n\n"
        "CORPO:\n"
        "Prezado(a) {client_name},\n"
        "Fica pela presente notificado a liquidar a fatura n.º {invoice_number} "
        "({currency} {amount}) no prazo de {grace_days} dias, sob pena de recurso imediato às vias judiciais."
    ),
}

def deduce(invoice: dict, classification: dict, language: str = "it") -> dict:
    lang = language.lower() if language and language.lower() in SUPPORTED_LANGS else "en"

    reminder_level = classification.get("reminder_level", 0)
    days_overdue   = classification.get("days_overdue", 0)
    payment_status = classification.get("payment_status", "UNKNOWN")
    invoice_number = invoice.get("invoice_number", "N/A")

    raw_amt = invoice.get("amount")
    try:
        amt_val = float(raw_amt) if raw_amt is not None else 0.0
    except (ValueError, TypeError):
        amt_val = 0.0

    if (
        payment_status in ("PAID", "DISPUTED", "SETTLED", "CREDIT_NOTE")
        or reminder_level == 0
        or classification.get("action") == "NO_REMINDER_NEEDED"
        or amt_val <= 0.0
    ):
        return {
            "action": "NO_REMINDER_NEEDED",
            "recommended_channel": "none",
            "template_key": None,
            "reminder_level": 0,
            "grace_days": 0,
            "next_escalation_days": 0,
            "days_overdue": days_overdue,
            "language": lang,
            "deduced_at": datetime.now().isoformat(),
        }

    action = f"SEND_REMINDER_L{reminder_level}"
    channel = LEVEL_CHANNELS.get(reminder_level, "email")
    template_key = f"{lang}_L{reminder_level}"
    grace_days = LEVEL_GRACE_DAYS.get(reminder_level, 5)

    if reminder_level == 1:
        next_esc_days = max(0, 15 - days_overdue)
    elif reminder_level == 2:
        next_esc_days = max(0, 30 - days_overdue)
    else:
        next_esc_days = 0

    if action == "NO_REMINDER_NEEDED" or payment_status in ("PAID", "DISPUTED", "SETTLED", "CREDIT_NOTE"):
        reminder_level = 0
        action = "NO_REMINDER_NEEDED"
        channel = "none"
        template_key = None
        next_esc_days = 0

    return {
        "action": action,
        "recommended_channel": channel,
        "template_key": template_key,
        "reminder_level": reminder_level,
        "grace_days": grace_days,
        "next_escalation_days": next_esc_days,
        "days_overdue": days_overdue,
        "language": lang,
        "deduced_at": datetime.now().isoformat(),
    }

RECOMMENDATIONS_BY_LANG = {
    "en": {
        "threshold": "Amount exceeds compliance threshold: authorization required.",
        "high_value": "High value amount: verify KYC/AML procedures.",
        "level_3": "Notice level 3: consult legal counsel prior to formal escalation.",
        "overdue_90": "Overdue exceeds 90 days: evaluate debt recovery or bad debt provisioning.",
        "clean": "No anomalies detected.",
    },
    "it": {
        "threshold": "Importo superiore alla soglia: verifica autorizzazione.",
        "high_value": "Importo elevato: verifica procedure KYC/AML.",
        "level_3": "Livello 3: consultare un legale prima della diffida.",
        "overdue_90": "Oltre 90 giorni: valutare recupero crediti o accantonamento.",
        "clean": "Nessuna anomalia rilevata.",
    },
    "de": {
        "threshold": "Betrag überschreitet Compliance-Schwellenwert: Genehmigung erforderlich.",
        "high_value": "Hoher Betrag: KYC/AML-Verfahren überprüfen.",
        "level_3": "Mahnstufe 3: Vor formeller Eskalation Rechtsbeistand hinzuziehen.",
        "overdue_90": "Überfälligkeit über 90 Tage: Inkasso oder Forderungsabschreibung prüfen.",
        "clean": "Keine Unregelmäßigkeiten festgestellt.",
    },
    "fr": {
        "threshold": "Montant supérieur au seuil de conformité: autorisation requise.",
        "high_value": "Montant élevé: vérifier les procédures KYC/AML.",
        "level_3": "Niveau 3: consulter un conseiller juridique avant mise en demeure.",
        "overdue_90": "Retard supérieur à 90 jours: évaluer le recouvrement ou la provision pour créance douteuse.",
        "clean": "Aucune anomalie détectée.",
    },
    "es": {
        "threshold": "Importe superior al umbral de cumplimiento: autorización requerida.",
        "high_value": "Importe elevado: verificar procedimientos KYC/AML.",
        "level_3": "Nivel 3: consultar con asesoría jurídica antes de la reclamación formal.",
        "overdue_90": "Vencimiento superior a 90 días: evaluar recobro o provisión por insolvencia.",
        "clean": "No se detectaron anomalías.",
    },
    "pt": {
        "threshold": "Montante excede o limiar de conformidade: autorização necessária.",
        "high_value": "Montante elevado: verificar procedimentos KYC/AML.",
        "level_3": "Nível 3: consultar apoio jurídico antes de notificação formal.",
        "overdue_90": "Atraso superior a 90 dias: avaliar cobrança difícil ou imparidade de dívida.",
        "clean": "Nenhuma anomalia detetada.",
    },
}

def check_compliance(invoice: dict, classification: dict, language: Optional[str] = None) -> dict:
    flags = list(classification.get("flags", []))
    recommendations = []
    reminder_level = classification.get("reminder_level", 0)
    compliance_flag = classification.get("compliance_flag", False)

    # Verifica della lingua: priorità al parametro language, poi campi fattura, fallback tassativo 'en'
    lang = normalize_lang(language or invoice.get("detected_language") or invoice.get("language") or "en")

    if compliance_flag:
        recommendations.append(get_text("recommendations", "threshold", lang))
    if "high_value_kyc_aml" in flags:
        recommendations.append(get_text("recommendations", "kyc", lang))
    if reminder_level >= 3:
        recommendations.append(get_text("recommendations", "legal", lang))
    if "critical_overdue_bad_debt_risk" in flags or "critical_overdue_risk_inesigibilita" in flags:
        recommendations.append(get_text("recommendations", "overdue_90", lang))
    if not recommendations:
        recommendations.append(get_text("recommendations", "none", lang))

    return {
        "compliance_flag": compliance_flag,
        "flags": flags,
        "recommendations": recommendations,
        "disclaimer": get_legal_disclaimer(lang),
        "checked_at": datetime.now().isoformat(),
    }

def sanitize_reminder_text(text: str, deadline_days: int = 7) -> str:
    if not text:
        return ""
    clean = text.replace("**", "")
    from datetime import timedelta
    deadline_date = (datetime.now() + timedelta(days=deadline_days)).strftime("%Y-%m-%d")
    clean = re.sub(r"\[insert\s+deadline[^\]]*\]", deadline_date, clean, flags=re.IGNORECASE)
    clean = re.sub(r"\[insert\s+due\s+date[^\]]*\]", deadline_date, clean, flags=re.IGNORECASE)
    clean = re.sub(r"\[insert\s+date[^\]]*\]", deadline_date, clean, flags=re.IGNORECASE)
    clean = re.sub(r"\[insert\s+[^\]]+\]", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\[inserisci\s+[^\]]+\]", "", clean, flags=re.IGNORECASE)
    
    # Rimuovi qualsiasi nota legale / disclaimer dal testo del sollecito
    clean = re.sub(r"(?i)\n*\s*(?:NOTA|NOTE|HINWEIS|AVERTISSEMENT|AVISO)\s*:\s*(?:Questo documento|This document|Dieses Dokument|Ce document|Este documento).*$", "", clean, flags=re.DOTALL)
    # Rimuovi firme fittizie residue in calce (es. Cordiali saluti, The Management, ecc.)
    clean = re.sub(r"(?i)\n*\s*(?:Cordiali saluti|Distinti saluti|Kind regards|Best regards|Mit freundlichen Grüßen|Cordialement|Atentamente|Com os melhores cumprimentos)\s*,?\s*\n+.*$", "", clean, flags=re.DOTALL)
    clean = re.sub(r"(?i)\n*\s*(?:The Management|La Direzione|Die Geschäftsleitung|La Direction|La Dirección|A Direção)\s*$", "", clean)

    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n\s*\n\s*\n+", "\n\n", clean)
    return clean.strip()

def generate_reminder_text(
    invoice: dict,
    billing: dict,
    language: str = "it",
    mode: str = "local",
    api_key: Optional[str] = None,
    classification: Optional[dict] = None,
) -> str:
    lang = language.lower() if language and language.lower() in SUPPORTED_LANGS else "en"

    # Se non è richiesto sollecito (es. saldo zero, nota di credito, già pagata), ritorna stringa vuota
    if (
        billing.get("action") == "NO_REMINDER_NEEDED"
        or (classification and classification.get("action") == "NO_REMINDER_NEEDED")
        or (classification and classification.get("payment_status") in ("PAID", "DISPUTED", "SETTLED", "CREDIT_NOTE"))
    ):
        logger.info("No reminder needed: invoice settled, paid, credit note, or disputed.")
        return ""

    level = billing.get("reminder_level", 1)
    vars_static = _build_vars(invoice, billing, lang, classification)

    # 1. ZUKWEND CORE AI: 100% deterministico local-first (~1s)
    if mode in ("local", "core"):
        logger.info("ZUKWEND CORE AI: instant deterministic reminder generation.")
        raw_text = _render_static(lang, level, vars_static)
        return sanitize_reminder_text(raw_text)

    prompt_path = Path(get_resource_path("prompts/prompt_deducer_ar.md"))
    if not prompt_path.exists():
        logger.warning("prompt_deducer_ar.md mancante. Uso fallback statico.")
        return sanitize_reminder_text(_render_static(lang, level, vars_static))

    invoice_data = {"invoice": invoice, "billing_severity": billing}
    if classification:
        invoice_data["classification"] = classification
    system_prompt = prompt_path.read_text(encoding="utf-8").replace("{{LANGUAGE}}", lang)
    full_prompt = f"{system_prompt}\n\nDATI FATTURA E GRAVITÀ:\n{json.dumps(invoice_data, indent=2, ensure_ascii=False, default=str)}"

    try:
        if mode == "ollama":
            if not is_local_llm_available():
                raise ConnectionError("Ollama non rilevato su localhost:11434. Avvia il server Ollama oppure seleziona ⚡ ZUKWEND CORE AI.")
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "qwen3:8b", "prompt": full_prompt, "stream": False},
                timeout=(3, 45)
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            if "</think>" in text:
                text = text.split("</think>")[-1].strip()
        else:  # cloud
            from engine_dispatcher import dispatch_cloud_prompt, AuthenticationError, CLOUD_AUTH_ERROR_MSG
            if not api_key:
                raise AuthenticationError(CLOUD_AUTH_ERROR_MSG)
            text = dispatch_cloud_prompt(api_key, full_prompt, max_tokens=1024, timeout=(5, 45))

        if len(text) > 30:
            logger.info("Text generated successfully by AI.")
            return sanitize_reminder_text(text)
        else:
            raise ValueError("Text generated by LLM too short")

    except Exception as e:
        if mode in ("ollama", "cloud"):
            # Per Ollama e Cloud non eseguire fallback silenzioso se l'autenticazione o il server falliscono
            raise e
        logger.error(f"LLM deduction error, activating static fallback: {e}")
        return sanitize_reminder_text(_render_static(lang, level, vars_static))

def _build_vars(invoice: dict, billing: dict, language: str, classification: Optional[dict] = None) -> dict:
    raw_amount = invoice.get("amount")
    safe_amount = 0.0 if raw_amount is None else float(raw_amount)

    # Iniezione corretta days_overdue dalla classificazione, billing o fattura
    days_overdue = 0
    if classification and classification.get("days_overdue") is not None:
        days_overdue = classification.get("days_overdue")
    elif billing and billing.get("days_overdue") is not None:
        days_overdue = billing.get("days_overdue")
    elif invoice and invoice.get("days_overdue") is not None:
        days_overdue = invoice.get("days_overdue")

    # Pulizia rigorosa nome cliente da punteggiatura orfana iniziale/finale
    client_name = invoice.get("client_name") or "Valued Customer"
    client_name = re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", str(client_name).strip())
    client_name = re.sub(r"\s+", " ", client_name)

    # Custom branding per mittente
    try:
        from custom_branding import get_branding
        branding = get_branding()
    except Exception:
        branding = {}

    vendor_name = branding.get("company_name") or invoice.get("vendor_name") or "The Management"
    vendor_name = re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", str(vendor_name).strip())
    vendor_name = re.sub(r"\s+", " ", vendor_name)

    # Formattazione importo con separatore migliaia
    formatted_amount = f"{safe_amount:,.2f}"
    currency = invoice.get("currency") or "EUR"

    issue_date_fmt = format_human_date(invoice.get("issue_date"), language)
    due_date_fmt = format_human_date(invoice.get("due_date"), language)

    return {
        "client_name": client_name,
        "vendor_name": vendor_name,
        "invoice_number": invoice.get("invoice_number") or "N/A",
        "issue_date": issue_date_fmt,
        "due_date": due_date_fmt,
        "amount": formatted_amount,
        "currency": currency,
        "days_overdue": str(days_overdue),
        "grace_days": str(billing.get("grace_days") or 5),
        "iban": branding.get("iban", ""),
        "email": branding.get("email", ""),
        "address": branding.get("address", ""),
        "disclaimer": get_legal_disclaimer(language),
    }

def _render_static(language: str, level: int, vars: dict) -> str:
    lang = language.lower() if language and language.lower() in SUPPORTED_LANGS else "en"
    lvl  = level if level in [1, 2, 3] else 1

    template = STATIC_TEMPLATES.get((lang, lvl))
    if not template:
        template = STATIC_TEMPLATES.get(("en", 1), "Reminder for invoice {invoice_number} — {currency} {amount}")

    out = template
    for k, v in vars.items():
        out = out.replace("{" + k + "}", str(v))
    return out