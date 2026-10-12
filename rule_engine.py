"""
ZUKWEND — Multilingual Billing Agent
Modulo: rule_engine.py
Ruolo: Regole AR centralizzate — rischio, sollecito, escalation, compliance
Versione: 1.0.0
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import logging
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger("zukwend.rule_engine")

# ------------------------------------------------------------
# Costanti AR
# ------------------------------------------------------------
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
COMPLIANCE_THRESHOLD  = 10_000.0
HIGH_VALUE_THRESHOLD  = 50_000.0


# ------------------------------------------------------------
# Rischio
# ------------------------------------------------------------
def compute_risk(days_overdue: Optional[int]) -> str:
    """Determina livello rischio AR."""
    if days_overdue is None:
        return RISK_NONE
    if days_overdue < 0:
        return RISK_NONE
    if 0 <= days_overdue <= 15:
        return RISK_LOW
    if 16 <= days_overdue <= 30:
        return RISK_MEDIUM
    return RISK_HIGH


# ------------------------------------------------------------
# Livello sollecito
# ------------------------------------------------------------
def compute_reminder_level(days_overdue: Optional[int]) -> int:
    """Determina livello sollecito L1/L2/L3."""
    if days_overdue is None or days_overdue < 0:
        return LEVEL_0
    if 0 <= days_overdue <= 15:
        return LEVEL_1
    if 16 <= days_overdue <= 30:
        return LEVEL_2
    return LEVEL_3


# ------------------------------------------------------------
# Prossima escalation
# ------------------------------------------------------------
def compute_next_escalation(days_overdue: Optional[int], reference: Optional[date] = None) -> Optional[str]:
    """Calcola data prossima escalation."""
    today = reference or date.today()

    if days_overdue is None or days_overdue < 0:
        return None

    if 0 <= days_overdue <= 15:
        return (today + timedelta(days=max(0, 15 - days_overdue))).isoformat()

    if 16 <= days_overdue <= 30:
        return (today + timedelta(days=max(0, 30 - days_overdue))).isoformat()

    return None


# ------------------------------------------------------------
# Compliance
# ------------------------------------------------------------
def compute_compliance_flags(amount: Optional[float], days_overdue: Optional[int]) -> list:
    """Genera flag compliance KYC/AML e rischio inesigibilità."""
    flags = []

    if amount and float(amount) > HIGH_VALUE_THRESHOLD:
        flags.append("high_value_kyc_aml")

    if amount and float(amount) > COMPLIANCE_THRESHOLD:
        flags.append("compliance_threshold_exceeded")

    if days_overdue and days_overdue > CRITICAL_OVERDUE_DAYS:
        flags.append("critical_overdue_risk_inesigibilita")

    return flags


# ------------------------------------------------------------
# Stato fattura
# ------------------------------------------------------------
def compute_status(payment_hint: str, days_overdue: Optional[int]) -> str:
    """Determina stato fattura."""
    hint = (payment_hint or "").upper()

    if hint in (STATUS_PAID, STATUS_DISPUTED):
        return hint

    if days_overdue is None:
        return STATUS_UNKNOWN

    if days_overdue < 0:
        return STATUS_PENDING

    return STATUS_OVERDUE


# ------------------------------------------------------------
# Regola completa AR (entry point)
# ------------------------------------------------------------
def evaluate(invoice: dict, reference_date: Optional[date] = None) -> dict:
    """
    Applica tutte le regole AR in modo deterministico.
    Usato da classifier, deducer, billing_logic, workflow_engine.
    """

    today = reference_date or date.today()

    amount        = invoice.get("amount")
    currency      = invoice.get("currency", "EUR")
    due_date_raw  = invoice.get("due_date")
    payment_hint  = invoice.get("payment_status", "")

    # Calcolo giorni ritardo
    days_overdue = None
    try:
        from datetime import datetime
        if due_date_raw:
            d = datetime.fromisoformat(due_date_raw).date()
            days_overdue = (today - d).days
    except Exception:
        days_overdue = None

    status = compute_status(payment_hint, days_overdue)
    risk   = compute_risk(days_overdue)
    level  = compute_reminder_level(days_overdue)
    next_esc = compute_next_escalation(days_overdue, today)
    flags = compute_compliance_flags(amount, days_overdue)

    return {
        "days_overdue": days_overdue,
        "status": status,
        "risk_level": risk,
        "reminder_level": level,
        "next_escalation_date": next_esc,
        "compliance_flags": flags,
        "amount": amount,
        "currency": currency,
        "due_date": due_date_raw,
    }
