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

logger = logging.getLogger("zukwend.deducer")

TEMPLATE_DIR = Path(__file__).parent.parent / "billing" / "templates"

LEVEL_CHANNELS = {
    1: "email",
    2: "email_raccomandata",
    3: "raccomandata_ar_pec",
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

    if payment_status in ("PAID", "DISPUTED") or reminder_level == 0:
        return {
            "action": "NO_ACTION",
            "recommended_channel": "none",
            "template_key": None,
            "reminder_level": 0,
            "grace_days": 0,
            "next_escalation_days": 0,
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
        "language": lang,
        "deduced_at": datetime.now().isoformat(),
    }

def check_compliance(invoice: dict, classification: dict) -> dict:
    flags = list(classification.get("flags", []))
    recommendations = []
    reminder_level = classification.get("reminder_level", 0)
    compliance_flag = classification.get("compliance_flag", False)

    clean_recs = {
        "it": "Nessuna anomalia rilevata.",
        "en": "No anomalies detected.",
        "de": "Keine Unregelmäßigkeiten festgestellt.",
        "fr": "Aucune anomalie détectée.",
        "es": "No se detectaron anomalías.",
        "pt": "Nenhuma anomalia detetada.",
    }

    lang = invoice.get("detected_language", "en")
    if lang not in clean_recs:
        lang = "en"

    if compliance_flag:
        recommendations.append("Importo superiore alla soglia: verifica autorizzazione.")
    if "high_value_kyc_aml" in flags:
        recommendations.append("Importo elevato: verifica procedure KYC/AML.")
    if reminder_level >= 3:
        recommendations.append("Livello 3: consultare un legale prima della diffida.")
    if "critical_overdue_risk_inesigibilita" in flags:
        recommendations.append("Oltre 90 giorni: valutare recupero crediti o accantonamento.")
    if not recommendations:
        recommendations.append(clean_recs.get(lang, clean_recs["en"]))

    return {
        "compliance_flag": compliance_flag,
        "flags": flags,
        "recommendations": recommendations,
        "disclaimer": DISCLAIMER_BY_LANG.get(lang, DISCLAIMER_BY_LANG["en"]),
        "checked_at": datetime.now().isoformat(),
    }

def generate_reminder_text(
    invoice: dict,
    billing: dict,
    language: str = "it",
    mode: str = "local",
    api_key: Optional[str] = None,
) -> str:
    lang = language.lower() if language and language.lower() in SUPPORTED_LANGS else "en"
    level = billing.get("reminder_level", 1)
    vars_static = _build_vars(invoice, billing, lang)

    prompt_path = Path(__file__).parent / "prompts" / "prompt_deducer_ar.md"
    if not prompt_path.exists():
        logger.warning("prompt_deducer_ar.md mancante. Uso fallback statico.")
        return _render_static(lang, level, vars_static)

    system_prompt = prompt_path.read_text(encoding="utf-8").replace("{{LANGUAGE}}", lang)
    invoice_data = {"invoice": invoice, "billing_severity": billing}
    full_prompt = f"{system_prompt}\n\nDATI FATTURA E GRAVITÀ:\n{json.dumps(invoice_data, indent=2)}"

    try:
        if mode == "local":
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "qwen3:8b", "prompt": full_prompt, "stream": False},
                timeout=45
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            if "</think>" in text:
                text = text.split("</think>")[-1].strip()
        else:
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": "claude-3-5-haiku-20241022", 
                    "max_tokens": 1024, 
                    "messages": [{"role": "user", "content": full_prompt}]
                },
                timeout=45
            )
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"].strip()

        if len(text) > 30:
            logger.info("Testo generato con successo dall'AI.")
            return text
        else:
            raise ValueError("Testo generato troppo corto dall'LLM")

    except Exception as e:
        logger.error(f"Errore LLM deduzione, attivazione fallback statico: {e}")
        return _render_static(lang, level, vars_static)

def _build_vars(invoice: dict, billing: dict, language: str) -> dict:
    raw_amount = invoice.get("amount")
    safe_amount = 0.0 if raw_amount is None else float(raw_amount)
    
    return {
        "client_name": invoice.get("client_name") or "Valued Customer",
        "vendor_name": invoice.get("vendor_name") or "The Management",
        "invoice_number": invoice.get("invoice_number") or "N/A",
        "issue_date": invoice.get("issue_date") or "N/A",
        "due_date": invoice.get("due_date") or "N/A",
        "amount": f"{safe_amount:.2f}",
        "currency": invoice.get("currency") or "EUR",
        "days_overdue": str(invoice.get("days_overdue") or billing.get("days_overdue") or 0),
        "grace_days": str(billing.get("grace_days") or 5),
        "disclaimer": DISCLAIMER_BY_LANG.get(language, DISCLAIMER_BY_LANG["en"]),
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