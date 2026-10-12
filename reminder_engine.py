"""
ZUKWEND — Multilingual Billing Agent
Modulo: reminder_engine.py
Ruolo: Motore di generazione reminder AR (L1/L2/L3)
Versione: 1.0.0
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger("zukwend.reminder_engine")

# ------------------------------------------------------------
# Template statici (IT / EN)
# ------------------------------------------------------------
TEMPLATES = {
    ("it", 1): (
        "Gentile {client_name},\n\n"
        "La fattura n. {invoice_number} per {currency} {amount} è scaduta il {due_date}.\n"
        "La invitiamo cortesemente a procedere al pagamento entro {grace_days} giorni.\n\n"
        "Cordiali saluti,\n{vendor_name}"
    ),
    ("it", 2): (
        "Gentile {client_name},\n\n"
        "La fattura n. {invoice_number} ({currency} {amount}), scaduta il {due_date}, "
        "risulta ancora non saldata da {days_overdue} giorni.\n"
        "La invitiamo a saldare entro {grace_days} giorni.\n\n"
        "Distinti saluti,\n{vendor_name}"
    ),
    ("it", 3): (
        "DIFFIDA FORMALE\n\n"
        "{client_name},\n\n"
        "La diffidiamo a saldare la fattura n. {invoice_number} ({currency} {amount}), "
        "scaduta il {due_date} ({days_overdue} giorni fa), entro {grace_days} giorni.\n\n"
        "{vendor_name}"
    ),

    ("en", 1): (
        "Dear {client_name},\n\n"
        "Invoice {invoice_number} for {currency} {amount} was due on {due_date}.\n"
        "Please arrange payment within {grace_days} business days.\n\n"
        "Kind regards,\n{vendor_name}"
    ),
    ("en", 2): (
        "Dear {client_name},\n\n"
        "Invoice {invoice_number} ({currency} {amount}), due on {due_date}, "
        "is still outstanding after {days_overdue} days.\n"
        "Please settle within {grace_days} days.\n\n"
        "Best regards,\n{vendor_name}"
    ),
    ("en", 3): (
        "FORMAL NOTICE\n\n"
        "Dear {client_name},\n\n"
        "We formally request payment for invoice {invoice_number} ({currency} {amount}), "
        "due on {due_date} ({days_overdue} days overdue), within {grace_days} days.\n\n"
        "{vendor_name}"
    ),
}

SUPPORTED_LANGS = ["it", "en"]


# ------------------------------------------------------------
# ReminderEngine
# ------------------------------------------------------------
class ReminderEngine:
    """
    Motore REPTANA per generazione reminder:
    - nessuna dipendenza esterna
    - nessun side-effect
    - output deterministico
    - multi-lingua
    """

    def __init__(self):
        self.timestamp = datetime.now().isoformat()

    def build_reminder(self, invoice: Dict, rules: Dict) -> Dict:
        """
        Genera reminder strutturato.

        Args:
            invoice: dict fattura normalizzata
            rules: dict output rule_engine.evaluate()

        Returns:
            dict con:
                language, level, text, vars, timestamp
        """

        lang = invoice.get("language", "it")
        if lang not in SUPPORTED_LANGS:
            lang = "en"

        level = rules.get("reminder_level", 1)
        template = TEMPLATES.get((lang, level))

        if not template:
            template = "Reminder for invoice {invoice_number} — {currency} {amount}"

        vars = self._build_vars(invoice, rules)
        text = self._render(template, vars)

        logger.info(f"ReminderEngine: generato L{level} | lang={lang}")

        return {
            "language": lang,
            "level": level,
            "text": text,
            "vars": vars,
            "timestamp": self.timestamp,
        }

    # ------------------------------------------------------------
    # Variabili template
    # ------------------------------------------------------------
    def _build_vars(self, invoice: Dict, rules: Dict) -> Dict:
        return {
            "client_name": invoice.get("client_name", "Cliente"),
            "vendor_name": invoice.get("vendor_name", ""),
            "invoice_number": invoice.get("invoice_number", "N/A"),
            "issue_date": invoice.get("issue_date", "N/A"),
            "due_date": invoice.get("due_date", "N/A"),
            "amount": f"{float(invoice.get('amount', 0.0)):.2f}",
            "currency": invoice.get("currency", "EUR"),
            "days_overdue": str(rules.get("days_overdue", 0)),
            "grace_days": str(self._grace_days(rules.get("reminder_level", 1))),
        }

    # ------------------------------------------------------------
    # Grace days
    # ------------------------------------------------------------
    def _grace_days(self, level: int) -> int:
        if level == 1:
            return 5
        if level == 2:
            return 3
        if level == 3:
            return 7
        return 5

    # ------------------------------------------------------------
    # Rendering template
    # ------------------------------------------------------------
    def _render(self, template: str, vars: Dict) -> str:
        out = template
        for k, v in vars.items():
            out = out.replace("{" + k + "}", str(v))
        return out


# ------------------------------------------------------------
# Helper per workflow_engine
# ------------------------------------------------------------
def build_reminder(invoice: Dict, rules: Dict) -> Dict:
    engine = ReminderEngine()
    return engine.build_reminder(invoice, rules)
