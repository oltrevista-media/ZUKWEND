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

from i18n_catalog import normalize_lang, get_text, get_channel_label, get_legal_disclaimer

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
        "Gentile {client_name},\n\n"
        "La fattura n. {invoice_number}, emessa il {issue_date}, "
        "per {currency} {amount}, è scaduta il {due_date}.\n\n"
        "La invitiamo a procedere al pagamento entro {grace_days} giorni lavorativi.\n\n"
        "Cordiali saluti,\n{vendor_name}"
    ),
    ("it", 2): (
        "Gentile {client_name},\n\n"
        "La fattura n. {invoice_number} ({currency} {amount}), scaduta il {due_date}, "
        "risulta ancora non saldata da {days_overdue} giorni.\n\n"
        "La invitiamo a saldare entro {grace_days} giorni per evitare ulteriori azioni.\n\n"
        "Distinti saluti,\n{vendor_name}"
    ),
    ("it", 3): (
        "DIFFIDA FORMALE\n\n"
        "{client_name},\n\n"
        "La diffidiamo a saldare la fattura n. {invoice_number} "
        "({currency} {amount}), scaduta il {due_date} ({days_overdue} giorni fa), "
        "entro {grace_days} giorni, pena il ricorso alle vie legali.\n\n"
        "{vendor_name}\n\n"
        "{disclaimer}"
    ),
    # ENGLISH
    ("en", 1): (
        "Dear {client_name},\n\n"
        "Invoice no. {invoice_number} for {currency} {amount} (due {due_date}) remains unpaid.\n\n"
        "We kindly ask you to arrange payment within {grace_days} business days.\n\n"
        "Kind regards,\n{vendor_name}"
    ),
    ("en", 2): (
        "Dear {client_name},\n\n"
        "Despite our previous notice, invoice no. {invoice_number} ({currency} {amount}) "
        "due on {due_date} is overdue by {days_overdue} days.\n\n"
        "Please settle within {grace_days} days to prevent further escalation.\n\n"
        "Best regards,\n{vendor_name}"
    ),
    ("en", 3): (
        "FORMAL COLLECTION NOTICE\n\n"
        "{client_name},\n\n"
        "You are formally required to settle invoice no. {invoice_number} "
        "({currency} {amount}), overdue by {days_overdue} days, within {grace_days} days. "
        "Failure to comply will result in immediate legal action.\n\n"
        "{vendor_name}\n\n"
        "{disclaimer}"
    ),
    # DEUTSCH
    ("de", 1): (
        "Sehr geehrte(r) {client_name},\n\n"
        "die Rechnung Nr. {invoice_number} über {currency} {amount} (Fälligkeit: {due_date}) "
        "ist noch offen.\n\n"
        "Bitte überweisen Sie den Betrag innerhalb von {grace_days} Werktagen.\n\n"
        "Mit freundlichen Grüßen,\n{vendor_name}"
    ),
    ("de", 2): (
        "Sehr geehrte(r) {client_name},\n\n"
        "trotz Mahnung ist die Rechnung Nr. {invoice_number} über {currency} {amount} "
        "seit {days_overdue} Tagen überfällig.\n\n"
        "Bitte begleichen Sie die Forderung innerhalb von {grace_days} Tagen.\n\n"
        "Mit freundlichen Grüßen,\n{vendor_name}"
    ),
    ("de", 3): (
        "LETZTE MAHNUNG / DIFFIDA\n\n"
        "{client_name},\n\n"
        "Sie werden aufgefordert, die Rechnung Nr. {invoice_number} ({currency} {amount}) "
        "binnen {grace_days} Tagen zu begleichen. Andernfalls werden unverzüglich rechtliche Schritte eingeleitet.\n\n"
        "{vendor_name}\n\n"
        "{disclaimer}"
    ),
    # FRANÇAIS
    ("fr", 1): (
        "Bonjour {client_name},\n\n"
        "La facture n° {invoice_number} d'un montant de {currency} {amount} "
        "(échéance le {due_date}) demeure impayée.\n\n"
        "Merci de procéder au règlement sous {grace_days} jours ouvrés.\n\n"
        "Cordialement,\n{vendor_name}"
    ),
    ("fr", 2): (
        "Bonjour {client_name},\n\n"
        "Sauf erreur, la facture n° {invoice_number} ({currency} {amount}) "
        "est en retard de {days_overdue} jours.\n\n"
        "Merci de régulariser la situation sous {grace_days} jours.\n\n"
        "Cordialement,\n{vendor_name}"
    ),
    ("fr", 3): (
        "MISE EN DEMEURE FORMELLE\n\n"
        "{client_name},\n\n"
        "Nous vous mettons en demeure de régler la facture n° {invoice_number} "
        "({currency} {amount}) sous {grace_days} jours. À défaut, une procédure contentieuse sera engagée.\n\n"
        "{vendor_name}\n\n"
        "{disclaimer}"
    ),
    # ESPAÑOL
    ("es", 1): (
        "Estimado/a {client_name},\n\n"
        "La factura n.° {invoice_number} por importe de {currency} {amount} "
        "(vencimiento el {due_date}) se encuentra pendiente de pago.\n\n"
        "Le rogamos efectúe el abono en un plazo de {grace_days} días hábiles.\n\n"
        "Atentamente,\n{vendor_name}"
    ),
    ("es", 2): (
        "Estimado/a {client_name},\n\n"
        "A pesar de nuestros avisos, la factura n.° {invoice_number} ({currency} {amount}) "
        "acumula {days_overdue} días de retraso.\n\n"
        "Rogamos regularice la situación en {grace_days} días.\n\n"
        "Saludos cordiales,\n{vendor_name}"
    ),
    ("es", 3): (
        "REQUERIMIENTO FORMAL DE PAGO\n\n"
        "{client_name},\n\n"
        "Le requerimos formalmente el pago de la factura n.° {invoice_number} "
        "({currency} {amount}) en el plazo improrrogable de {grace_days} días, bajo apercibimiento de acciones legales.\n\n"
        "{vendor_name}\n\n"
        "{disclaimer}"
    ),
    # PORTUGUÊS
    ("pt", 1): (
        "Prezado(a) {client_name},\n\n"
        "A fatura n.º {invoice_number} no valor de {currency} {amount} "
        "(com vencimento a {due_date}) permanece em aberto.\n\n"
        "Solicitamos a regularização no prazo de {grace_days} dias úteis.\n\n"
        "Com os melhores cumprimentos,\n{vendor_name}"
    ),
    ("pt", 2): (
        "Prezado(a) {client_name},\n\n"
        "Apesar dos contactos anteriores, a fatura n.º {invoice_number} ({currency} {amount}) "
        "encontra-se vencida há {days_overdue} dias.\n\n"
        "Pedimos a liquidação no prazo de {grace_days} dias para evitar procedimentos adicionais.\n\n"
        "Atenciosamente,\n{vendor_name}"
    ),
    ("pt", 3): (
        "NOTIFICAÇÃO FORMAL DE COBRANÇA\n\n"
        "{client_name},\n\n"
        "Fica pela presente notificado a liquidar a fatura n.º {invoice_number} "
        "({currency} {amount}) no prazo de {grace_days} dias, sob pena de recurso imediato às vias judiciais.\n\n"
        "{vendor_name}\n\n"
        "{disclaimer}"
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
    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n\s*\n\s*\n", "\n\n", clean)
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
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": "claude-3-5-haiku-20241022", 
                    "max_tokens": 1024, 
                    "messages": [{"role": "user", "content": full_prompt}]
                },
                timeout=(5, 45)
            )
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"].strip()

        if len(text) > 30:
            logger.info("Text generated successfully by AI.")
            return sanitize_reminder_text(text)
        else:
            raise ValueError("Text generated by LLM too short")

    except Exception as e:
        if mode == "ollama":
            # Per Ollama non eseguire fallback silenzioso se il server non risponde
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

    return {
        "client_name": client_name,
        "vendor_name": vendor_name,
        "invoice_number": invoice.get("invoice_number") or "N/A",
        "issue_date": invoice.get("issue_date") or "N/A",
        "due_date": invoice.get("due_date") or "N/A",
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