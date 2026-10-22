"""
ZUKWEND — Multilingual Billing Agent
Modulo: classifier.py
Versione: 1.0.1-PATCH (Gate 5)
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from i18n_catalog import get_rationale, normalize_lang

logger = logging.getLogger("zukwend.classifier")

# ------------------------------------------------------------
# Costanti classificazione
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

DEFAULT_COMPLIANCE_THRESHOLD = 10_000.0
HIGH_VALUE_THRESHOLD         = 50_000.0
CRITICAL_OVERDUE_DAYS        = 90

SUPPORTED_CURRENCIES = {
    "EUR","USD","GBP","BRL","CHF","SEK","NOK","DKK",
    "PLN","CZK","HUF","RON","TRY","CAD","AUD","JPY",
    "$","€","£","¥","R$"
}

# ------------------------------------------------------------
# Parse date (ISO, EU, US)
# ------------------------------------------------------------
def _parse_date(raw: Optional[str]) -> Optional[date]:
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
        "%Y-%d-%m",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%Y/%d/%m",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except:
            continue

    logger.warning(f"Impossibile parsare data: '{raw}'")
    return None

# ------------------------------------------------------------
# classify()
# ------------------------------------------------------------
def classify(
    invoice: dict,
    compliance_threshold: float = DEFAULT_COMPLIANCE_THRESHOLD,
    reference_date: Optional[date] = None,
    language: Optional[str] = None,
) -> dict:

    today = reference_date or date.today()
    errors = []

    # Campi
    due_date_raw  = invoice.get("due_date")
    amount        = invoice.get("amount")
    currency      = invoice.get("currency", "EUR")
    payment_hint  = (invoice.get("payment_status") or "").upper()
    invoice_number = invoice.get("invoice_number", "N/A")
    lang = normalize_lang(language or invoice.get("detected_language") or invoice.get("normalization_locale") or "en")

    # Validazioni base
    if amount is not None and amount < 0:
        errors.append("negative_amount")

    if currency not in SUPPORTED_CURRENCIES:
        errors.append("unsupported_currency")

    # Stato dichiarato
    if payment_hint in (STATUS_PAID, STATUS_DISPUTED):
        rationale_key = "status_declared"
        rationale_params = {"status": payment_hint}
        rationale = get_rationale(rationale_key, lang, **rationale_params)
        return _build_result(
            payment_status=payment_hint,
            days_overdue=0,
            risk_level=RISK_NONE,
            reminder_level=LEVEL_0,
            compliance_flag=False,
            flags=[],
            rationale_key=rationale_key,
            rationale_params=rationale_params,
            rationale=rationale,
            next_escalation=None,
            amount=amount,
            currency=currency,
            errors=errors,
        )

    # Parse scadenza
    due_date = _parse_date(due_date_raw)
    if due_date is None:
        errors.append("due_date_not_parsable")
        rationale_key = "due_date_missing"
        rationale_params = {}
        rationale = get_rationale(rationale_key, lang)
        return _build_result(
            payment_status=STATUS_UNKNOWN,
            days_overdue=0,
            risk_level=RISK_NONE,
            reminder_level=LEVEL_0,
            compliance_flag=_check_compliance_threshold(amount, compliance_threshold),
            flags=["due_date_missing"] + _check_extra_flags(amount, 0, language=lang),
            rationale_key=rationale_key,
            rationale_params=rationale_params,
            rationale=rationale,
            next_escalation=None,
            amount=amount,
            currency=currency,
            errors=errors,
        )

    # Calcolo ritardo
    days_overdue = (today - due_date).days

    # Stato
    if days_overdue < 0:
        payment_status = STATUS_PENDING
        risk_level     = RISK_NONE
        reminder_level = LEVEL_0
        rationale_key  = "due_in_days"
        rationale_params = {"days": abs(days_overdue)}
        rationale      = get_rationale(rationale_key, lang, **rationale_params)
        next_escalation = due_date.isoformat()

    elif days_overdue == 0:
        payment_status = STATUS_OVERDUE
        risk_level     = RISK_LOW
        reminder_level = LEVEL_1
        rationale_key  = "due_today_l1"
        rationale_params = {}
        rationale      = get_rationale(rationale_key, lang)
        next_escalation = (today + timedelta(days=15)).isoformat()

    elif 1 <= days_overdue <= 15:
        payment_status = STATUS_OVERDUE
        risk_level     = RISK_LOW
        reminder_level = LEVEL_1
        rationale_key  = "overdue_days_l1"
        rationale_params = {"days": days_overdue}
        rationale      = get_rationale(rationale_key, lang, **rationale_params)
        next_escalation = (today + timedelta(days=15 - days_overdue)).isoformat()

    elif 16 <= days_overdue <= 30:
        payment_status = STATUS_OVERDUE
        risk_level     = RISK_MEDIUM
        reminder_level = LEVEL_2
        rationale_key  = "overdue_days_l2"
        rationale_params = {"days": days_overdue}
        rationale      = get_rationale(rationale_key, lang, **rationale_params)
        next_escalation = (today + timedelta(days=30 - days_overdue)).isoformat()

    else:
        payment_status = STATUS_OVERDUE
        risk_level     = RISK_HIGH
        reminder_level = LEVEL_3
        rationale_key  = "overdue_days_l3"
        rationale_params = {"days": days_overdue}
        rationale      = get_rationale(rationale_key, lang, **rationale_params)
        next_escalation = None

    # Compliance
    compliance_flag = _check_compliance_threshold(amount, compliance_threshold)

    # Extra flags (Canonical English neutral keys)
    flags = _check_extra_flags(amount, days_overdue, language=lang)
    if compliance_flag:
        flags.append("compliance_threshold_exceeded")

    return _build_result(
        payment_status=payment_status,
        days_overdue=days_overdue,
        risk_level=risk_level,
        reminder_level=reminder_level,
        compliance_flag=compliance_flag,
        flags=flags,
        rationale_key=rationale_key,
        rationale_params=rationale_params,
        rationale=rationale,
        next_escalation=next_escalation,
        amount=amount,
        currency=currency,
        errors=errors,
    )

# ------------------------------------------------------------
# build result
# ------------------------------------------------------------
def _build_result(
    payment_status: str,
    days_overdue: int,
    risk_level: str,
    reminder_level: int,
    compliance_flag: bool,
    flags: list,
    rationale_key: str,
    rationale_params: dict,
    rationale: str,
    next_escalation: Optional[str],
    amount: Optional[float],
    currency: str,
    errors: Optional[list] = None,
) -> dict:
    return {
        "payment_status": payment_status,
        "days_overdue": days_overdue,
        "risk_level": risk_level,
        "reminder_level": reminder_level,
        "compliance_flag": compliance_flag,
        "flags": flags,
        "rationale_key": rationale_key,
        "rationale_params": rationale_params,
        "classification_rationale": rationale,
        "next_escalation_date": next_escalation,
        "amount": amount,
        "currency": currency,
        "classified_at": datetime.now().isoformat(),
        "errors": errors or [],
    }

# ------------------------------------------------------------
# compliance threshold
# ------------------------------------------------------------
def _check_compliance_threshold(amount: Optional[float], threshold: float) -> bool:
    if amount is None:
        return False
    return float(amount) > threshold

# ------------------------------------------------------------
# extra flags (Canonical Neutral Keys)
# ------------------------------------------------------------
def _check_extra_flags(amount: Optional[float], days_overdue: int, language: str = "en") -> list:
    flags = []
    if amount and float(amount) > HIGH_VALUE_THRESHOLD:
        flags.append("high_value_kyc_aml")
    if days_overdue > CRITICAL_OVERDUE_DAYS:
        flags.append("critical_overdue_bad_debt_risk")
    return flags

# ------------------------------------------------------------
# batch classify
# ------------------------------------------------------------
def classify_batch(
    invoices: list,
    compliance_threshold: float = DEFAULT_COMPLIANCE_THRESHOLD,
    reference_date: Optional[date] = None,
) -> list:
    results = []
    for i, invoice in enumerate(invoices):
        try:
            result = classify(invoice, compliance_threshold, reference_date)
            result["batch_index"] = i
            result["invoice_number"] = invoice.get("invoice_number", f"IDX-{i}")
            results.append(result)
        except Exception as e:
            logger.error(f"Error classifying invoice {i}: {e}")
            results.append({
                "batch_index": i,
                "invoice_number": invoice.get("invoice_number", f"IDX-{i}"),
                "payment_status": STATUS_UNKNOWN,
                "error": str(e),
            })
    return results

# ------------------------------------------------------------
# aging summary
# ------------------------------------------------------------
def compute_aging_summary(classifications: list, currency: str = "EUR") -> dict:
    summary = {
        "total_invoices": len(classifications),
        "currency": currency,
        "by_level": {
            "L0": {"count": 0, "amount": 0.0},
            "L1": {"count": 0, "amount": 0.0},
            "L2": {"count": 0, "amount": 0.0},
            "L3": {"count": 0, "amount": 0.0},
        },
        "total_overdue_amount": 0.0,
        "compliance_flags_count": 0,
        "generated_at": datetime.now().isoformat(),
    }

    for c in classifications:
        level = c.get("reminder_level", 0)
        amount = c.get("amount", 0.0) or 0.0
        key = f"L{level}" if level in [0,1,2,3] else "L0"

        summary["by_level"][key]["count"] += 1
        summary["by_level"][key]["amount"] += float(amount)

        if level > 0:
            summary["total_overdue_amount"] += float(amount)

        if c.get("compliance_flag"):
            summary["compliance_flags_count"] += 1

    for k in summary["by_level"]:
        summary["by_level"][k]["amount"] = round(summary["by_level"][k]["amount"], 2)

    summary["total_overdue_amount"] = round(summary["total_overdue_amount"], 2)

    return summary
