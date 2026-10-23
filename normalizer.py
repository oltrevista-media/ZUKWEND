"""
ZUKWEND — Multilingual Billing Agent
Modulo: normalizer.py
Versione: 1.0.1-PATCH (Gate 5)
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger("zukwend.normalizer")

# ------------------------------------------------------------
# Mappe mesi (estesi + abbreviati)
# ------------------------------------------------------------
MONTH_NAMES = {
    "it": {
        "gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,
        "luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12,
        "gen":1,"feb":2,"mar":3,"apr":4,"mag":5,"giu":6,"lug":7,"ago":8,"set":9,"ott":10,"nov":11,"dic":12,
    },
    "en": {
        "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
        "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
        "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
    },
    "fr": {
        "janvier":1,"fevrier":2,"mars":3,"avril":4,"mai":5,"juin":6,
        "juillet":7,"aout":8,"septembre":9,"octobre":10,"novembre":11,"decembre":12,
    },
    "de": {
        "januar":1,"februar":2,"maerz":3,"april":4,"mai":5,"juni":6,
        "juli":7,"august":8,"september":9,"oktober":10,"november":11,"dezember":12,
    },
    "es": {
        "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
        "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12,
    },
    "pt": {
        "janeiro":1,"fevereiro":2,"marco":3,"abril":4,"maio":5,"junho":6,
        "julho":7,"agosto":8,"setembro":9,"outubro":10,"novembro":11,"dezembro":12,
    },
}

# ------------------------------------------------------------
# Valute
# ------------------------------------------------------------
CURRENCY_ALIASES = {
    "eur":"EUR","euro":"EUR","euros":"EUR","€":"EUR",
    "usd":"USD","dollar":"USD","dollars":"USD","$":"USD",
    "gbp":"GBP","pound":"GBP","pounds":"GBP","£":"GBP",
    "brl":"BRL","real":"BRL","reais":"BRL","r$":"BRL",
    "chf":"CHF","franc":"CHF","franchi":"CHF","franco":"CHF",
    "sek":"SEK","nok":"NOK","dkk":"DKK",
    "pln":"PLN","czk":"CZK","huf":"HUF","ron":"RON","try":"TRY",
    "cad":"CAD","aud":"AUD","jpy":"JPY","¥":"JPY","yen":"JPY",
}

# ------------------------------------------------------------
# Indicatori lingua
# ------------------------------------------------------------
LANG_INDICATORS = {
    "it": ["fattura","scadenza","importo","cliente","gentile","spett","pagamento","emissione"],
    "en": ["invoice","due","amount","client","dear","payment","issued","bill"],
    "fr": ["facture","echeance","montant","client","madame","monsieur","paiement","emise"],
    "de": ["rechnung","faellig","betrag","kunde","sehr","geehrte","zahlung","ausgestellt"],
    "es": ["factura","vencimiento","importe","cliente","estimado","pago","emitida"],
    "pt": ["fatura","vencimento","valor","cliente","prezado","pagamento","emitida"],
}

# ------------------------------------------------------------
# normalize()
# ------------------------------------------------------------
def normalize(raw_fields: dict, locale: str = "it") -> dict:
    result = dict(raw_fields)

    raw_text = raw_fields.get("raw_text", "") or ""
    detected_lang = detect_language(raw_text, hint=locale)
    result["detected_language"] = detected_lang

    # Date
    result["issue_date"] = normalize_date(raw_fields.get("issue_date"), locale=detected_lang)
    result["due_date"]   = normalize_date(raw_fields.get("due_date"),   locale=detected_lang)

    # Importo
    if raw_fields.get("amount") is None and raw_fields.get("amount_raw"):
        result["amount"] = normalize_amount(raw_fields["amount_raw"], locale=detected_lang)
    elif isinstance(raw_fields.get("amount"), str):
        result["amount"] = normalize_amount(raw_fields["amount"], locale=detected_lang)
    else:
        result["amount"] = raw_fields.get("amount")

    if result["amount"] is not None:
        result["amount"] = round(float(result["amount"]), 2)

    # Valuta
    curr_res = normalize_currency(
        raw_fields.get("currency") or raw_fields.get("amount_raw", "")
    )
    result["currency"] = curr_res.currency if hasattr(curr_res, "currency") else str(curr_res)
    if result.get("amount") is None and getattr(curr_res, "amount", None) is not None:
        result["amount"] = curr_res.amount

    # Nomi
    if raw_fields.get("client_name"):
        result["client_name"] = normalize_name(raw_fields["client_name"])
    if raw_fields.get("vendor_name"):
        result["vendor_name"] = normalize_name(raw_fields["vendor_name"])

    # Indirizzo cliente
    if raw_fields.get("client_address"):
        result["client_address"] = normalize_address(raw_fields["client_address"])
    elif raw_fields.get("address"):
        result["client_address"] = normalize_address(raw_fields["address"])

    # Numero fattura
    if raw_fields.get("invoice_number"):
        result["invoice_number"] = normalize_invoice_number(raw_fields["invoice_number"])

    # Partita IVA / VAT ID (Strict P.IVA)
    raw_vat = (
        raw_fields.get("client_vat")
        or raw_fields.get("vat_number")
        or raw_fields.get("tax_id")
        or raw_fields.get("piva")
    )
    if raw_vat:
        clean_v = re.sub(r"[\s\-_.]+", "", str(raw_vat).strip().upper())
        result["client_vat"] = clean_v if len(clean_v) >= 5 else None
    else:
        result["client_vat"] = None
    result["vat_number"] = result["client_vat"]

    # Rilevamento Credit Note e preservazione rigorosa importo negativo
    text_corpus = (
        (raw_text or "") + " " +
        str(raw_fields.get("amount_raw") or "") + " " +
        str(raw_fields.get("invoice_number") or "") + " " +
        str(raw_fields.get("payment_status") or "")
    ).lower()

    is_credit_note = False
    for pat in [r"\bcredit\s*note\b", r"\bnota\s*di\s*credito\b", r"\bnota\s*de\s*cr[eé]dito\b", r"\bavoir\b", r"\bgutschrift\b"]:
        if re.search(pat, text_corpus, re.IGNORECASE):
            is_credit_note = True
            break

    if is_credit_note:
        result["payment_status"] = "CREDIT_NOTE"
        if result.get("amount") is not None:
            result["amount"] = -abs(float(result["amount"]))
    elif result.get("amount") is not None and float(result["amount"]) < 0:
        result["payment_status"] = "CREDIT_NOTE"
    elif raw_fields.get("payment_status"):
        result["payment_status"] = raw_fields.get("payment_status")

    result["normalization_locale"] = detected_lang
    result["normalized_at"] = datetime.now().isoformat()
    result["normalization_confidence"] = _compute_confidence(result)

    return result

# ------------------------------------------------------------
# normalize_date()
# ------------------------------------------------------------
def normalize_date(raw: Optional[str], locale: str = "it") -> Optional[str]:
    if not raw:
        return None

    raw = str(raw).strip()

    # ISO or YYYY-MM-DD or anomalous YYYY-DD-MM (with optional whitespace)
    m = re.match(r"^(\d{4})\s*[-/\.]\s*(\d{1,2})\s*[-/\.]\s*(\d{1,2})$", raw)
    if m:
        y, p1, p2 = m.group(1), int(m.group(2)), int(m.group(3))
        if p1 > 12 and p2 <= 12:
            return f"{y}-{str(p2).zfill(2)}-{str(p1).zfill(2)}"
        elif p1 <= 12 and p2 > 12:
            return f"{y}-{str(p1).zfill(2)}-{str(p2).zfill(2)}"
        return f"{y}-{str(p1).zfill(2)}-{str(p2).zfill(2)}"

    # EU numerico (with optional whitespace)
    m = re.match(r"^(\d{1,2})\s*[/\.\-]\s*(\d{1,2})\s*[/\.\-]\s*(\d{4})$", raw)
    if m:
        p1, p2, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if p1 > 12 and p2 <= 12:
            return f"{y}-{str(p2).zfill(2)}-{str(p1).zfill(2)}"
        elif p2 > 12 and p1 <= 12:
            return f"{y}-{str(p1).zfill(2)}-{str(p2).zfill(2)}"
        return f"{y}-{str(p2).zfill(2)}-{str(p1).zfill(2)}"

    # Testuale
    text_lower = raw.lower()
    for lang, months in MONTH_NAMES.items():
        for name, num in months.items():
            if name in text_lower:
                nums = re.findall(r"\d+", raw)
                if len(nums) >= 2:
                    y = [n for n in nums if len(n) == 4][0]
                    d = [n for n in nums if len(n) <= 2][0]
                    return f"{y}-{str(num).zfill(2)}-{d.zfill(2)}"

    # Strftime
    for fmt in ["%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y"]:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except:
            pass

    return None

# ------------------------------------------------------------
# normalize_amount()
# ------------------------------------------------------------
# ------------------------------------------------------------
# normalize_amount()
# ------------------------------------------------------------
def normalize_amount(raw: Optional[str], locale: str = "it") -> Optional[float]:
    if raw is None:
        return None

    # Prova prima con il parser universale di valuta
    res = normalize_currency(raw)
    if res.amount is not None:
        return res.amount

    raw_str = str(raw).strip()
    # 1. Rileva indicatore negativo esplicito (segno meno singolo o parentesi contabili)
    is_neg = False
    if re.search(r"\(\s*[-+]?[^)]*\d+[^)]*\)", raw_str):
        is_neg = True
    elif (
        re.search(r"(?<![-−–])[-−–](?![-−–])\s*(?:[\$€£¥]|EUR|USD|GBP|CHF|BRL)?\s*\d", raw_str)
        or re.search(r"(?:[\$€£¥]|EUR|USD|GBP|CHF|BRL)\s*(?<![-−–])[-−–](?![-−–])\s*\d", raw_str)
        or re.search(r"\d\s*(?<![-−–])[-−–](?![-−–])$", raw_str)
    ):
        is_neg = True

    cleaned = re.sub(r"[€$£¥\sA-Za-z'’`\(\)]", "", raw_str)

    if not cleaned:
        return None

    n_dots   = cleaned.count(".")
    n_commas = cleaned.count(",")

    if n_commas == 1 and n_dots == 0:
        comma_pos = cleaned.index(",")
        after = cleaned[comma_pos+1:]
        if len(after) <= 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    elif n_dots == 1 and n_commas == 0:
        dot_pos = cleaned.index(".")
        after = cleaned[dot_pos+1:]
        if len(after) == 3 and locale in ("it","fr","de","es","pt"):
            cleaned = cleaned.replace(".", "")

    elif n_dots >= 1 and n_commas == 1:
        last_comma = cleaned.rfind(",")
        last_dot   = cleaned.rfind(".")
        if last_comma > last_dot:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    elif n_commas >= 1 and n_dots == 0:
        cleaned = cleaned.replace(",", "").replace(".", "")

    try:
        amt = round(float(cleaned), 2)
        return -abs(amt) if is_neg else amt
    except:
        return None

# ------------------------------------------------------------
# CurrencyResult e normalize_currency()
# ------------------------------------------------------------
class CurrencyResult(tuple):
    def __new__(cls, amount: Optional[float], currency: str, iso_code: str = "EUR"):
        return super().__new__(cls, (amount, currency))

    def __init__(self, amount: Optional[float], currency: str, iso_code: str = "EUR"):
        self._iso = iso_code

    @property
    def amount(self) -> Optional[float]:
        return self[0]

    @property
    def currency(self) -> str:
        return self[1]

    @property
    def iso_code(self) -> str:
        return self._iso

    def __eq__(self, other):
        if isinstance(other, tuple):
            return super().__eq__(other)
        if isinstance(other, (int, float)):
            return self.amount == other
        if isinstance(other, str):
            return self.currency == other or self._iso == other
        return False

    def __getitem__(self, item):
        if isinstance(item, str):
            if item == "amount":
                return self[0]
            if item == "currency":
                return self[1]
            if item == "iso_code":
                return self._iso
            raise KeyError(item)
        return super().__getitem__(item)

    def get(self, key, default=None):
        if key == "amount":
            return self[0]
        if key == "currency":
            return self[1]
        if key == "iso_code":
            return self._iso
        return default

    def to_dict(self):
        return {"amount": self[0], "currency": self[1], "iso_code": self._iso}


def normalize_currency(raw: Optional[str]) -> CurrencyResult:
    """
    Normalizza valuta e importo:
    - Estrae simbolo valuta originale ($, €, £, CHF) o default EUR se assente.
    - Preserva rigorosamente il segno negativo '-' sia anteposto al numero/valuta sia tra parentesi contabili.
    - Conserva il simbolo originale nell'output (.currency), tracciando anche l'ISO (.iso_code).
    - Pulisce e calcola l'importo numerico su formati Anglo-Sassone, Continentale e Svizzero.
    """
    if not raw:
        return CurrencyResult(None, "EUR", "EUR")

    s = str(raw).strip()
    if not s:
        return CurrencyResult(None, "EUR", "EUR")

    # 1. Rileva indicatore negativo esplicito (segno meno singolo o parentesi contabili)
    is_neg = False
    if re.search(r"\(\s*[-+]?[^)]*\d+[^)]*\)", s):
        is_neg = True
    elif (
        re.search(r"(?<![-−–])[-−–](?![-−–])\s*(?:[\$€£¥]|EUR|USD|GBP|CHF|BRL)?\s*\d", s)
        or re.search(r"(?:[\$€£¥]|EUR|USD|GBP|CHF|BRL)\s*(?<![-−–])[-−–](?![-−–])\s*\d", s)
        or re.search(r"\d\s*(?<![-−–])[-−–](?![-−–])$", s)
    ):
        is_neg = True

    curr = "EUR"
    iso = "EUR"
    if "CHF" in s:
        curr = "CHF"
        iso = "CHF"
    elif "R$" in s:
        curr = "R$"
        iso = "BRL"
    elif "$" in s:
        curr = "$"
        iso = "USD"
    elif "€" in s:
        curr = "€"
        iso = "EUR"
    elif "£" in s:
        curr = "£"
        iso = "GBP"
    elif "¥" in s:
        curr = "¥"
        iso = "JPY"
    elif "USD" in s:
        curr = "$"
        iso = "USD"
    elif "EUR" in s or "euro" in s.lower():
        curr = "EUR"
        iso = "EUR"
    elif "GBP" in s:
        curr = "£"
        iso = "GBP"
    elif "BRL" in s:
        curr = "BRL"
        iso = "BRL"
    else:
        # Check aliases
        raw_lower = s.lower()
        for alias, iso_val in CURRENCY_ALIASES.items():
            if alias in raw_lower:
                iso = iso_val
                curr = alias if alias in ("$", "€", "£", "¥", "CHF") else iso_val
                break

    # Pulizia numerica
    num_str = re.sub(
        r"(?i)\b(?:EUR|USD|GBP|CHF|BRL|CAD|AUD|JPY|TOTAL|AMOUNT|SUBTOTAL|VALORE|IMPORTO|SOLDE|NETTO|LORDO|DUE|BALANCE)\b",
        "",
        s,
    )
    num_str = re.sub(r"[\$€£¥]", "", num_str)
    num_str = re.sub(r"['’`]", "", num_str)
    num_str = re.sub(r"(\d)\s+(\d)", r"\1\2", num_str)
    num_str = re.sub(r"[^\d.,]", "", num_str).strip()

    if not num_str:
        return CurrencyResult(None, curr, iso)

    if "," in num_str and "." in num_str:
        if num_str.rfind(".") > num_str.rfind(","):
            num_str = num_str.replace(",", "")
        else:
            num_str = num_str.replace(".", "").replace(",", ".")
    elif "," in num_str:
        parts = num_str.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            num_str = num_str.replace(",", ".")
        else:
            num_str = num_str.replace(",", "")
    elif "." in num_str:
        parts = num_str.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            num_str = num_str.replace(".", "")
        elif len(parts) > 2:
            num_str = num_str.replace(".", "")

    try:
        amt = round(float(num_str), 2)
        if is_neg and amt is not None:
            amt = -abs(amt)
    except Exception:
        amt = None

    return CurrencyResult(amt, curr, iso)


def _extract_amount_and_currency(text: str):
    """Estrae importo e valuta preservando segno negativo e Credit Note."""
    is_credit_note = False
    for pat in [r"\bcredit\s*note\b", r"\bnota\s*di\s*credito\b", r"\bnota\s*de\s*cr[eé]dito\b", r"\bavoir\b", r"\bgutschrift\b"]:
        if re.search(pat, text, re.IGNORECASE):
            is_credit_note = True
            break

    amount_patterns = [
        r"(?:[-−–]\s*)?(?:EUR|€|USD|\$|GBP|£|BRL|R\$|CHF|JPY|¥)\s*\(?\s*[-−–]?\s*[\d\.,'’`\s]+\)?",
        r"\(?\s*[-−–]?\s*[\d\.,'’`\s]+\)?\s*(?:EUR|€|USD|\$|GBP|£|BRL|R\$|CHF|JPY|¥)",
        r"(?:totale|total|amount|balance\s*due|montant|betrag|importe|valor)\s*[:\s|]\s*([^\n\r]+)",
        r"\(?\s*[-−–]\s*[\d\.,'’`\s]+\)?",
    ]

    for line in text.split("\n"):
        line_clean = line.strip()
        if re.search(
            r"(?:total\s*amount|totale\s*fattura|balance\s*due|amount\s*due|total|totale|montant|betrag|importe|valor)\b",
            line_clean,
            re.IGNORECASE,
        ):
            res = normalize_currency(line_clean)
            if res.amount is not None:
                amt = -abs(res.amount) if is_credit_note else res.amount
                return amt, res.currency, line_clean

    for pattern in amount_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in reversed(matches):
                res = normalize_currency(match)
                if res.amount is not None:
                    amt = -abs(res.amount) if is_credit_note else res.amount
                    return amt, res.currency, str(match).strip()

    return None, "EUR", None

# ------------------------------------------------------------
# detect_language()
# ------------------------------------------------------------
def detect_language(text: str, hint: str = "it") -> str:
    if not text or len(text.strip()) < 20:
        return hint

    text_lower = text.lower()
    scores = {lang: 0 for lang in LANG_INDICATORS}

    for lang, kws in LANG_INDICATORS.items():
        for kw in kws:
            if kw in text_lower:
                scores[lang] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else hint

# ------------------------------------------------------------
# clean_layout_tokens() & normalize_address()
# ------------------------------------------------------------
def clean_layout_tokens(raw: Optional[str]) -> Optional[str]:
    """
    Rimuove token spuri di intestazione layout (es. Invoice, Facture, Rechnung, Page, Fattura)
    in coda a stringhe (es. 'London, UK Invoice' -> 'London, UK').
    """
    if not raw:
        return None
    s = str(raw).strip()
    pattern = r"(?i)\s*[\-_|/:]*\s*\b(?:invoice|facture|rechnung|page|fattura|fatura)\b.*$"
    s = re.sub(pattern, "", s)
    s = re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else None

def normalize_address(raw: Optional[str]) -> Optional[str]:
    """
    Normalizza l'indirizzo applicando il trimming finale sui token spuri di intestazione layout (es. Invoice).
    Esempio: 'London, UK Invoice' -> 'London, UK'.
    """
    if not raw:
        return None
    cleaned = clean_layout_tokens(raw)
    if not cleaned:
        return None
    cleaned = re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", cleaned)
    return cleaned.strip() if cleaned else None

# ------------------------------------------------------------
# normalize_name()
# ------------------------------------------------------------
def normalize_name(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    # Trimming preliminare token spuri di layout
    cleaned = clean_layout_tokens(raw)
    if not cleaned:
        return None
    # Rimuovi caratteri di punteggiatura orfani iniziali/finali (due punti ':', virgole ',', etc.)
    cleaned = re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", cleaned.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)[:120]

    siglas = {
        "srl": "Srl", "s.r.l.": "S.r.l.", "spa": "SpA", "s.p.a.": "S.p.A.",
        "ltd": "Ltd", "ltd.": "Ltd.", "gmbh": "GmbH",
        "bv": "BV", "sa": "SA", "sas": "SAS", "snc": "SNC",
        "llc": "LLC", "inc": "Inc", "inc.": "Inc."
    }

    words = cleaned.split()
    out = []
    for w in words:
        lw = w.lower()
        if lw in siglas:
            out.append(siglas[lw])
        else:
            out.append(w.capitalize() if w.islower() else w)
    result = " ".join(out)
    result = clean_layout_tokens(result)
    return re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", result.strip()) if result else None

# ------------------------------------------------------------
# normalize_invoice_number()
# ------------------------------------------------------------
def normalize_invoice_number(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    return re.sub(r"\s+", "", raw.strip()).upper()[:50]

# ------------------------------------------------------------
# _compute_confidence()
# ------------------------------------------------------------
def _compute_confidence(n: dict) -> float:
    required = ["invoice_number","due_date","amount","currency"]
    present = sum(1 for f in required if n.get(f))

    optional = ["issue_date","client_name","vendor_name"]
    opt = sum(1 for f in optional if n.get(f))

    score = (present/len(required))*0.8 + (opt/len(optional))*0.2
    return round(score, 2)
