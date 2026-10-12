"""
ZUKWEND — Multilingual Billing Agent
Modulo: billing_logic.py
Ruolo: Calcolo scadenze, giorni di ritardo, stato fattura, prossima escalation
Versione: 1.0.0
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger("zukwend.billing_logic")

STATUS_PENDING   = "PENDING"
STATUS_OVERDUE   = "OVERDUE"
STATUS_PAID      = "PAID"
STATUS_DISPUTED  = "DISPUTED"
STATUS_UNKNOWN   = "UNKNOWN"

RISK_NONE   = "NONE"
RISK_LOW    = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH   = "HIGH"

LEVEL_0 = 0
LEVEL_1 = 1
LEVEL_2 = 2
LEVEL_3 = 3

CRITICAL_OVERDUE_DAYS = 90


def _parse_date(raw: Optional[str]) -> Optional[date]:
    """Parsa date ISO o EU."""
    if not raw:
        return None

    raw = str(raw).strip()

    # ISO con T
    try:
        if "T" in raw:
            return datetime.fromisoformat(raw).date()
    except:
        pass

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except:
            continue

    logger.warning(f"billing_logic: impossibile parsare data '{raw}'")
    return None


def calculate_billing_logic(invoice: dict, reference_date: Optional[date] = None) -> dict:
    """
    Calcola giorni di ritardo, stato fattura, rischio, livello sollecito e prossima escalation.

    Args:
        invoice: dict fattura normalizzata
        reference_date: data di riferimento (default: oggi)

    Returns:
        dict con:
            days_overdue, status, risk_level, reminder_level,
            next_escalation_date, amount, currency, due_date
    """

    today = reference_date or date.today()

    amount  = invoice.get("amount")
    currency = invoice.get("currency", "EUR")
    due_raw = invoice.get("due_date")
    payment_hint = (invoice.get("payment_status") or "").upper()

    # Stato dichiarato (paid/disputed)
    if payment_hint in (STATUS_PAID, STATUS_DISPUTED):
        return {
            "days_overdue": 0,
            "status": payment_hint,
            "risk_level": RISK_NONE,
            "reminder_level": LEVEL_0,
            "next_escalation_date": None,
            "amount": amount,
            "currency": currency,
            "due_date": due_raw,
            "note": "Stato dichiarato dal documento",
        }

    # Parse scadenza
    due_date = _parse_date(due_raw)
    if due_date is None:
        return {
            "days_overdue": 0,
            "status": STATUS_UNKNOWN,
            "risk_level": RISK_NONE,
            "reminder_level": LEVEL_0,
            "next_escalation_date": None,
            "amount": amount,
            "currency": currency,
            "due_date": None,
            "note": "Data scadenza non parsabile",
        }

    # Calcolo ritardo
    days_overdue = (today - due_date).days

    # Stato
    if days_overdue < 0:
        status = STATUS_PENDING
        risk = RISK_NONE
        level = LEVEL_0
        next_esc = due_date.isoformat()
        note = f"Scade tra {abs(days_overdue)} giorni"
    elif days_overdue == 0:
        status = STATUS_OVERDUE
        risk = RISK_LOW
        level = LEVEL_1
        next_esc = (today + timedelta(days=15)).isoformat()
        note = "Scade oggi — avvio L1"
    elif 1 <= days_overdue <= 15:
        status = STATUS_OVERDUE
        risk = RISK_LOW
        level = LEVEL_1
        next_esc = (today + timedelta(days=15 - days_overdue)).isoformat()
        note = f"Scaduta da {days_overdue} giorni — L1"
    elif 16 <= days_overdue <= 30:
        status = STATUS_OVERDUE
        risk = RISK_MEDIUM
        level = LEVEL_2
        next_esc = (today + timedelta(days=30 - days_overdue)).isoformat()
        note = f"Scaduta da {days_overdue} giorni — L2"
    else:
        status = STATUS_OVERDUE
        risk = RISK_HIGH
        level = LEVEL_3
        next_esc = None
        note = f"Scaduta da {days_overdue} giorni — L3"

    return {
        "days_overdue": days_overdue,
        "status": status,
        "risk_level": risk,
        "reminder_level": level,
        "next_escalation_date": next_esc,
        "amount": amount,
        "currency": currency,
        "due_date": due_raw,
        "note": note,
    }
