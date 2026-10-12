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
    r"(?:fattura|invoice|facture|rechnung|factura|fatura)\s*[n\.\°#]?\s*[:\s]?\s*([A-Za-z0-9\-_/]+)",
    r"(?:n\.|n°|nr\.|no\.)\s*([A-Za-z0-9\-_/]+)",
    r"\b(INV[-/]\d+[-/]?\d*)\b",
    r"\b(FT[-/]\d+[-/]?\d*)\b",
]

AMOUNT_PATTERNS = [
    r"(?:EUR|€|USD|\$|GBP|£|BRL|R\$|CHF|JPY|¥)\s*([\d\.]+,\d{2})",
    r"([\d\.]+,\d{2})\s*(?:EUR|€|USD|\$|GBP|£|BRL|R\$|CHF|JPY|¥)",
    r"(?:EUR|€|USD|\$|GBP|£|CHF|JPY|¥)\s*([\d,]+\.\d{2})",
    r"([\d,]+\.\d{2})\s*(?:EUR|€|USD|\$|GBP|£|CHF|JPY|¥)",
    r"(?:totale|total|montant|betrag|importe|valor)\s*[:\s]?\s*([\d\.,]+)",
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
        except Exception as e: logger.warning(f"pdfplumber fallito: {e}")

    if PYPDF2_AVAILABLE and not text:
        try:
            with open(str(path), "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join([page.extract_text() or "" for page in reader.pages]).strip()
            if text: return text
        except Exception as e: logger.warning(f"PyPDF2 fallito: {e}")

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
        except Exception as e: logger.warning(f"OCR fallito: {e}")

    if not text:
        raise ValueError(f"Impossibile estrarre testo da {path.name}.")
    return text

# ---------------------------------------------------------------------------
# MOTORE COGNITIVO IBRIDO: extract_fields()
# ---------------------------------------------------------------------------
def extract_fields(raw_text: str, use_ocr: bool = False, mode: str = "local", api_key: str = None) -> dict:
    if not raw_text or len(raw_text.strip()) < 10:
        return {"requires_manual_input": True, "error": "testo insufficiente"}

    # TENTATIVO 1: Estrazione Cognitiva (LLM)
    prompt_path = Path(__file__).parent / "prompts" / "prompt_parser_ar.md"
    if prompt_path.exists():
        try:
            system_prompt = prompt_path.read_text(encoding="utf-8")
            full_prompt = f"{system_prompt}\n\nTESTO DELLA FATTURA:\n{raw_text}"

            if mode == "local":
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "qwen3:8b", "prompt": full_prompt, "stream": False, "format": "json"},
                    timeout=60
                )
                resp.raise_for_status()
                response_text = resp.json().get("response", "")
            else:
                headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
                resp = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json={"model": "claude-3-5-haiku-20241022", "max_tokens": 1024, "messages": [{"role": "user", "content": full_prompt}]},
                    timeout=60
                )
                resp.raise_for_status()
                response_text = resp.json()["content"][0]["text"]

            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                
                # Validazione minima di sicurezza
                if data.get("invoice_number") and data.get("amount") is not None:
                    data["requires_manual_input"] = False
                    data["extraction_timestamp"] = datetime.now().isoformat()
                    data["extraction_method"] = f"LLM ({mode})"
                    logger.info("Estrazione completata via LLM.")
                    return data
                
        except Exception as e:
            logger.warning(f"LLM fallito ({e}), attivazione Fallback Regex.")

    # TENTATIVO 2: Fallback Deterministico (Regex Originali)
    logger.info("Esecuzione estrazione Regex di emergenza.")
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

def _extract_amount_and_currency(text: str):
    for pattern in AMOUNT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            amount_raw = matches[-1]
            amount_float = _parse_amount(amount_raw)
            if amount_float is not None:
                return amount_float, _extract_currency_symbol(text), amount_raw
    return None, None, None

def _parse_amount(raw: str) -> Optional[float]:
    if not raw: return None
    cleaned = re.sub(r"[^\d.,]", "", raw.strip())
    if not cleaned: return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."): cleaned = cleaned.replace(".", "").replace(",", ".")
        else: cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2: cleaned = cleaned.replace(",", ".")
        else: cleaned = cleaned.replace(",", "")
    try: return round(float(cleaned), 2)
    except: return None

def _extract_currency_symbol(text: str) -> Optional[str]:
    for code in ["EUR", "USD", "GBP", "CHF", "JPY", "BRL"]:
        if code in text: return code
    if "€" in text: return "EUR"
    if "$" in text: return "USD"
    if "£" in text: return "GBP"
    if "¥" in text: return "JPY"
    if "CHF" in text: return "CHF"
    if "R$" in text: return "BRL"
    return "EUR"

def _extract_client_name(text: str, text_lower: str) -> Optional[str]:
    for keyword in ["spett.le", "spettabile", "intestata a", "bill to", "client:", "a:"]:
        idx = text_lower.find(keyword)
        if idx != -1:
            for line in text[idx + len(keyword): idx + len(keyword) + 80].split("\n"):
                if line.strip() and len(line.strip()) > 3: return line.strip()[:80]
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