"""
ZUKWEND — Multilingual Billing Agent
Modulo: parser.py
Ruolo: Document Parser — Estrazione Ibrida (LLM Cognitivo + Regex Fallback)
Versione: 3.0.0 (Safe AI Edition)
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import json
import logging
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from resource_utils import get_resource_path, is_local_llm_available
except ImportError:  # pragma: no cover - esecuzione isolata del modulo
    def get_resource_path(relative_path: str) -> str:
        return str(Path(__file__).parent / relative_path)

    def is_local_llm_available(*_args, **_kwargs) -> bool:
        return True

logger = logging.getLogger("zukwend.parser")

# ---------------------------------------------------------------------------
# Import librerie con fallback
# ---------------------------------------------------------------------------
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber non disponibile — uso PyPDF2 come primario")

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 non disponibile")

try:
    import pytesseract
    from PIL import Image
    import fitz
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.info("OCR non disponibile")

# ---------------------------------------------------------------------------
# Costanti per Fallback Regex (Antigravity Original)
# ---------------------------------------------------------------------------
DATE_PATTERNS = [
    (r"\b(\d{4}[-/]\d{2}[-/]\d{2})\b", "%Y-%m-%d"),
    (r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})\b", None),
    (r"\b(\w+ \d{1,2},\s*\d{4})\b", None),
    (r"\b(\d{1,2}\.\s*\w+\s*\d{4})\b", None),
]

INVOICE_NUMBER_PATTERNS = [
    r"(?:fattura|invoice|facture|rechnung|factura|fatura)\s*(?:n\.|n°|nr\.|no\.|num\.|number|numero|#|n|nr|no)?\s*[:\s]?\s*([A-Za-z0-9\-_/]+)",
    r"(?:n\.|n°|nr\.|no\.)\s*([A-Za-z0-9\-_/]+)",
    r"\b(INV[-/][A-Za-z0-9\-_/]+)\b",
    r"\b(FT[-/][A-Za-z0-9\-_/]+)\b",
]

AMOUNT_PATTERNS = [
    r"(?:EUR|€|USD|\$|GBP|£|BRL|R\$|CHF|JPY|¥)\s*([\d\.,'’`\s]+)",
    r"([\d\.,'’`\s]+)\s*(?:EUR|€|USD|\$|GBP|£|BRL|R\$|CHF|JPY|¥)",
    r"(?:totale|total|amount|balance\s*due|montant|betrag|importe|valor)\s*[:\s|]\s*([^\n\r]+)",
]

DUE_DATE_KEYWORDS = {
    "it": ["scadenza", "scade", "pagare entro"],
    "en": ["due date", "due", "pay by"],
}

ISSUE_DATE_KEYWORDS = {
    "it": ["data emissione", "data fattura", "emessa il"],
    "en": ["invoice date", "date of issue", "issued on"],
}

# ---------------------------------------------------------------------------
# Estrazione Testo (Originale)
# ---------------------------------------------------------------------------
def extract_text(pdf_path: str, use_ocr: bool = False) -> str:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File non trovato: {pdf_path}")

    text = ""
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(str(path)) as pdf:
                text = "\n".join([page.extract_text() or "" for page in pdf.pages]).strip()
            if text: return text
        except Exception as e: logger.warning(f"pdfplumber failed: {e}")

    if PYPDF2_AVAILABLE and not text:
        try:
            with open(str(path), "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join([page.extract_text() or "" for page in reader.pages]).strip()
            if text: return text
        except Exception as e: logger.warning(f"PyPDF2 failed: {e}")

    if use_ocr and OCR_AVAILABLE and not text:
        try:
            import io
            doc = fitz.open(str(path))
            all_text = []
            for page_num in range(len(doc)):
                pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                all_text.append(pytesseract.image_to_string(img, lang="ita+eng"))
            doc.close()
            text = "\n".join(all_text)
            if text: return text
        except Exception as e: logger.warning(f"OCR failed: {e}")

    if not text:
        raise ValueError(f"Unable to extract text from {path.name}.")
    return text

# ---------------------------------------------------------------------------
# MOTORE COGNITIVO IBRIDO: extract_fields()
# ---------------------------------------------------------------------------
def extract_fields(raw_text: str, use_ocr: bool = False, mode: str = "local", api_key: str = None) -> dict:
    if not raw_text or len(raw_text.strip()) < 10:
        return {"requires_manual_input": True, "error": "insufficient text"}

    # MODALITÀ 1: ZUKWEND CORE AI (mode == "local" o "core") — 100% Deterministico e Locale (~1s)
    if mode in ("local", "core"):
        logger.info("Executing ZUKWEND CORE AI proprietary deterministic extraction.")
        return _fallback_regex_extraction(raw_text)

    # MODALITÀ 2: OLLAMA AI POWER-UP (mode == "ollama")
    if mode == "ollama":
        if not is_local_llm_available():
            raise ConnectionError("Ollama non rilevato su localhost:11434. Avvia il server Ollama oppure seleziona ⚡ ZUKWEND CORE AI.")
        prompt_path = Path(get_resource_path("prompts/prompt_parser_ar.md"))
        if prompt_path.exists():
            try:
                system_prompt = prompt_path.read_text(encoding="utf-8")
                full_prompt = f"{system_prompt}\n\nTESTO DELLA FATTURA:\n{raw_text}"
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "qwen3:8b", "prompt": full_prompt, "stream": False, "format": "json"},
                    timeout=(3, 60)
                )
                resp.raise_for_status()
                response_text = resp.json().get("response", "")
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    if data.get("invoice_number") and data.get("amount") is not None:
                        data["requires_manual_input"] = False
                        data["extraction_timestamp"] = datetime.now().isoformat()
                        data["extraction_method"] = "Ollama Local LLM"
                        logger.info("Extraction completed via Ollama Local LLM.")
                        return data
            except Exception as e:
                logger.warning(f"Ollama extraction error ({e}), using fallback.")
        return _fallback_regex_extraction(raw_text)

    # MODALITÀ 3: CLOUD BYOC (mode == "cloud")
    if mode == "cloud":
        prompt_path = Path(get_resource_path("prompts/prompt_parser_ar.md"))
        if prompt_path.exists() and api_key:
            try:
                system_prompt = prompt_path.read_text(encoding="utf-8")
                full_prompt = f"{system_prompt}\n\nTESTO DELLA FATTURA:\n{raw_text}"
                headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
                resp = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json={"model": "claude-3-5-haiku-20241022", "max_tokens": 1024, "messages": [{"role": "user", "content": full_prompt}]},
                    timeout=(5, 60)
                )
                resp.raise_for_status()
                response_text = resp.json()["content"][0]["text"]
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    if data.get("invoice_number") and data.get("amount") is not None:
                        data["requires_manual_input"] = False
                        data["extraction_timestamp"] = datetime.now().isoformat()
                        data["extraction_method"] = "Cloud BYOC LLM"
                        logger.info("Extraction completed via Cloud LLM.")
                        return data
            except Exception as e:
                logger.warning(f"Cloud LLM extraction error ({e}), using fallback.")
        return _fallback_regex_extraction(raw_text)

    # Fallback Deterministico
    return _fallback_regex_extraction(raw_text)

# ---------------------------------------------------------------------------
# Regex Fallback Engine
# ---------------------------------------------------------------------------
def _fallback_regex_extraction(raw_text: str) -> dict:
    text_lower = raw_text.lower()
    amount, currency, amount_raw = _extract_amount_and_currency(raw_text)
    
    fields = {
        "invoice_number": _extract_invoice_number(raw_text),
        "issue_date": _extract_issue_date(raw_text, text_lower),
        "due_date": _extract_due_date(raw_text, text_lower),
        "amount": amount,
        "amount_raw": amount_raw,
        "currency": currency or "EUR",
        "client_name": _extract_client_name(raw_text, text_lower),
        "client_address": _extract_client_address(raw_text, text_lower),
        "vendor_name": _extract_vendor_name(raw_text, text_lower),
        "payment_terms": _extract_payment_terms(text_lower),
        "extraction_timestamp": datetime.now().isoformat(),
        "extraction_method": "Regex_Fallback",
        "requires_manual_input": False,
    }

    missing = [k for k in ["invoice_number", "due_date", "amount"] if not fields.get(k)]
    if missing:
        fields["missing_fields"] = missing
        fields["requires_manual_input"] = len(missing) >= 2
    return fields

def _extract_invoice_number(text: str) -> Optional[str]:
    for pattern in INVOICE_NUMBER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and len(match.group(1).strip()) >= 3: return match.group(1).strip()
    return None

def _extract_issue_date(text: str, text_lower: str) -> Optional[str]:
    for lang_keywords in ISSUE_DATE_KEYWORDS.values():
        for kw in lang_keywords:
            idx = text_lower.find(kw)
            if idx != -1:
                date = _find_first_date(text[idx: idx + 100])
                if date: return date
    return _find_first_date(text)

def _extract_due_date(text: str, text_lower: str) -> Optional[str]:
    for lang_keywords in DUE_DATE_KEYWORDS.values():
        for kw in lang_keywords:
            idx = text_lower.find(kw)
            if idx != -1:
                date = _find_first_date(text[idx: idx + 100])
                if date: return date
    return None

def _find_first_date(text: str) -> Optional[str]:
    for pattern, _ in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match: return match.group(1)
    return None

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


def normalize_currency(raw_val) -> CurrencyResult:
    """
    Universal Currency Parser:
    - Estrae il simbolo valuta originale ($, €, £, CHF) o imposta EUR di default se assente.
    - Pulisce la stringa numerica: gestisce formato Anglo-Sassone ("18,450.00" -> 18450.00),
      Continentale ("18.450,00" -> 18450.00) e Svizzero ("18'450.00" -> 18450.00).
    - Ritorna CurrencyResult(amount, currency) compatibile con tuple unpacking e accesso ad attributi.
    """
    if raw_val is None:
        return CurrencyResult(None, "EUR", "EUR")

    s = str(raw_val).strip()
    if not s:
        return CurrencyResult(None, "EUR", "EUR")

    # 1. Estrazione valuta: conserva simbolo originale ($, €, £, CHF)
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

    # 2. Pulizia stringa numerica
    num_str = re.sub(
        r"(?i)\b(?:EUR|USD|GBP|CHF|BRL|CAD|AUD|JPY|TOTAL|AMOUNT|SUBTOTAL|VALORE|IMPORTO|SOLDE|NETTO|LORDO|DUE|BALANCE)\b",
        "",
        s,
    )
    num_str = re.sub(r"[\$€£¥]", "", num_str)
    # Rimuovi separatore migliaia svizzero (apostrofi ', ’, `)
    num_str = re.sub(r"['’`]", "", num_str)
    # Rimuovi spazi tra cifre
    num_str = re.sub(r"(\d)\s+(\d)", r"\1\2", num_str)
    num_str = re.sub(r"[^\d.,]", "", num_str).strip()

    if not num_str:
        return CurrencyResult(None, curr, iso)

    # 3. Gestione separatori decimali e migliaia
    if "," in num_str and "." in num_str:
        if num_str.rfind(".") > num_str.rfind(","):
            # Anglo-Sassone: 18,450.00 -> 18450.00
            num_str = num_str.replace(",", "")
        else:
            # Continentale: 18.450,00 -> 18450.00
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
    except Exception:
        amt = None

    return CurrencyResult(amt, curr, iso)


def _extract_amount_and_currency(text: str):
    # 1. Cerca prima su righe con indicazione esplicita di totale
    for line in text.split("\n"):
        line_clean = line.strip()
        if re.search(
            r"(?:total\s*amount|totale\s*fattura|balance\s*due|amount\s*due|total|totale|montant|betrag|importe|valor)\b",
            line_clean,
            re.IGNORECASE,
        ):
            res = normalize_currency(line_clean)
            if res.amount is not None:
                curr = res.currency if res.currency != "EUR" or "EUR" in line_clean else _extract_currency_symbol(text)
                return res.amount, curr, line_clean

    # 2. Cerca tramite AMOUNT_PATTERNS
    for pattern in AMOUNT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in reversed(matches):
                res = normalize_currency(match)
                if res.amount is not None:
                    curr = res.currency if res.currency != "EUR" or "EUR" in str(match) else _extract_currency_symbol(text)
                    return res.amount, curr, str(match).strip()

    return None, "EUR", None


def _parse_amount(raw: str) -> Optional[float]:
    if not raw:
        return None
    return normalize_currency(raw).amount


def _extract_currency_symbol(text: str) -> str:
    if not text:
        return "EUR"
    return normalize_currency(text).currency


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


def _extract_client_name(text: str, text_lower: str) -> Optional[str]:
    keywords = [
        "spett.le:", "spett.le", "spettabile:", "spettabile", "intestata a:", "intestata a",
        "bill to:", "bill to", "billed to:", "billed to", "client:", "client",
        "customer:", "customer", "sold to:", "sold to", "a:", "fatturare a:"
    ]
    for keyword in keywords:
        idx = text_lower.find(keyword)
        if idx != -1:
            segment = text[idx + len(keyword): idx + len(keyword) + 120]
            for line in segment.split("\n"):
                cleaned = re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", line.strip())
                cleaned = re.sub(r"\s+", " ", cleaned)
                if cleaned and len(cleaned) > 3 and not re.match(r"^(?:inv|fattura|date|p\.iva|vat|tax)\b", cleaned, re.I):
                    cleaned = clean_layout_tokens(cleaned)
                    if cleaned:
                        return cleaned[:80]
    return None


def _extract_client_address(text: str, text_lower: str) -> Optional[str]:
    keywords = [
        "bill to:", "bill to", "billed to:", "billed to", "client:", "client",
        "customer:", "customer", "sold to:", "sold to", "spett.le:", "spett.le",
        "spettabile:", "spettabile", "intestata a:", "intestata a", "a:", "fatturare a:"
    ]
    for keyword in keywords:
        idx = text_lower.find(keyword)
        if idx != -1:
            segment = text[idx + len(keyword): idx + len(keyword) + 200]
            lines = [l.strip() for l in segment.split("\n") if l.strip()]
            found_name = False
            for line in lines:
                cleaned = re.sub(r"^[\s:,\-;|]+|[\s:,\-;|]+$", "", line.strip())
                cleaned = re.sub(r"\s+", " ", cleaned)
                if not cleaned or len(cleaned) <= 3:
                    continue
                if re.match(r"^(?:inv|fattura|date|p\.iva|vat|tax)\b", cleaned, re.I):
                    continue
                if not found_name:
                    found_name = True
                    continue
                cleaned_addr = clean_layout_tokens(cleaned)
                if cleaned_addr:
                    return cleaned_addr[:120]
    return None

def _extract_vendor_name(text: str, text_lower: str) -> Optional[str]:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:5]:
        if len(line) > 5 and not re.match(r"^\d", line): return line[:80]
    return None

def _extract_payment_terms(text_lower: str) -> Optional[str]:
    for pattern in [r"(?:pagamento|payment)\s*[:\s]?\s*(.{5,50}?)(?:\n|$)", r"(\d+\s*giorni|days)"]:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match: return match.group(1).strip()[:100]
    return None

# ---------------------------------------------------------------------------
# Entry point unificato
# ---------------------------------------------------------------------------
def parse_invoice_from_path(pdf_path: str, use_ocr: bool = False, mode: str = "local", api_key: str = None) -> dict:
    try:
        raw_text = extract_text(pdf_path, use_ocr=use_ocr)
        fields = extract_fields(raw_text, use_ocr=use_ocr, mode=mode, api_key=api_key)
        fields["parsing_method"] = "pdfplumber" if PDFPLUMBER_AVAILABLE else "PyPDF2"
        fields["ocr_used"] = use_ocr and OCR_AVAILABLE
        return fields
    except Exception as e:
        logger.error(f"parse_invoice_from_path error: {e}")
        return {"requires_manual_input": True, "error": str(e)}

if __name__ == "__main__":
    import argparse, sys
    cli = argparse.ArgumentParser(description="ZUKWEND Parser AI (Ibrido)")
    cli.add_argument("pdf", help="Percorso al PDF")
    cli.add_argument("--ocr", action="store_true", help="Abilita OCR")
    cli.add_argument("--mode", default="local", choices=["local", "cloud"])
    cli.add_argument("--api-key", default=None)
    cli.add_argument("--text-only", action="store_true")
    args = cli.parse_args()
    logging.basicConfig(level=logging.INFO)

    if args.text_only:
        try: print(extract_text(args.pdf, use_ocr=args.ocr))
        except Exception as e:
            print(f"ERRORE: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        result = parse_invoice_from_path(args.pdf, use_ocr=args.ocr, mode=args.mode, api_key=args.api_key)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if not result.get("requires_manual_input") else 1)