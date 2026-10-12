"""
ZUKWEND — Multilingual Billing Agent
Modulo: error_handler.py
Ruolo: Gestione errori centralizzata per pipeline AR
Versione: 1.0.0
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import logging
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger("zukwend.error_handler")

# ------------------------------------------------------------
# Categorie errori
# ------------------------------------------------------------
ERROR_CATEGORIES = {
    "PARSER",
    "NORMALIZER",
    "CLASSIFIER",
    "DEDUCER",
    "REPORT",
    "EXPORT",
    "LICENSE",
    "WORKFLOW",
}

# ------------------------------------------------------------
# ErrorHandler (entry point)
# ------------------------------------------------------------
class ErrorHandler:
    """
    Gestore errori REPTANA:
    - nessun side-effect globale
    - logging locale
    - output strutturato per workflow_engine
    """

    def __init__(self):
        self.timestamp = datetime.now().isoformat()

    def handle(self, error: Exception, category: str, context: Optional[Dict] = None) -> dict:
        """
        Gestisce un errore e restituisce un dict strutturato.

        Args:
            error: eccezione originale
            category: categoria (PARSER, NORMALIZER, CLASSIFIER, ...)
            context: dict opzionale con dati utili

        Returns:
            dict con:
                category, message, type, timestamp, context, recoverable
        """

        cat = category.upper().strip()
        if cat not in ERROR_CATEGORIES:
            cat = "WORKFLOW"

        message = str(error).strip() or "Errore sconosciuto"
        error_type = error.__class__.__name__

        # Logging locale (senza side-effects)
        logger.error(f"[{cat}] {error_type}: {message}")

        # Regole REPTANA per recuperabilità
        recoverable = self._is_recoverable(cat)

        return {
            "category": cat,
            "message": message,
            "type": error_type,
            "timestamp": self.timestamp,
            "context": context or {},
            "recoverable": recoverable,
        }

    # ------------------------------------------------------------
    # Regole recuperabilità (REPTANA)
    # ------------------------------------------------------------
    def _is_recoverable(self, category: str) -> bool:
        """
        Determina se l'errore è recuperabile.
        REPTANA RULE:
        - PARSER → NO (file corrotto / OCR fallito)
        - NORMALIZER → SI (fallback deterministico)
        - CLASSIFIER → SI (fallback UNKNOWN)
        - DEDUCER → SI (fallback template statico)
        - REPORT → NO (PDF/DOCX non generabili)
        - EXPORT → SI (fallback percorso originale)
        - LICENSE → NO (anti-tamper)
        - WORKFLOW → SI (retry step)
        """
        if category == "PARSER":
            return False
        if category == "REPORT":
            return False
        if category == "LICENSE":
            return False
        return True


# ------------------------------------------------------------
# Funzione helper (usata da workflow_engine)
# ------------------------------------------------------------
def handle_error(error: Exception, category: str, context: Optional[Dict] = None) -> dict:
    """
    Wrapper semplificato per workflow_engine.
    """
    handler = ErrorHandler()
    return handler.handle(error, category, context)
