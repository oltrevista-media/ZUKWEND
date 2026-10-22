"""
ZUKWEND — Multilingual Billing Agent
Modulo: i18n_catalog.py
Ruolo: Catalogo centralizzato traduzioni kernel-safe a 6 lingue (IT, EN, DE, FR, ES, PT)
con fallback tassativo su INGLESE (EN) e Anti-Leak Linter / Guardrail.
Versione: 2.1.5-KERNEL-SAFE
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("zukwend.i18n")

SUPPORTED_LANGUAGES = ["en", "it", "de", "fr", "es", "pt"]
DEFAULT_FALLBACK_LANGUAGE = "en"

# ---------------------------------------------------------------------------
# CATALOGO TRADUZIONI CENTRALIZZATO (6 Lingue x Chiavi Simboliche Neutre)
# ---------------------------------------------------------------------------
CATALOG: Dict[str, Dict[str, Dict[str, str]]] = {
    # 1. RATIONALES CLASSIFICAZIONE
    "rationale": {
        "en": {
            "status_declared": "Declared status: {status}",
            "due_date_missing": "Due date not available",
            "due_in_days": "Due in {days} days",
            "due_today_l1": "Due today — notice L1",
            "overdue_days_l1": "Overdue by {days} days — L1",
            "overdue_days_l2": "Overdue by {days} days — L2",
            "overdue_days_l3": "Overdue by {days} days — L3",
        },
        "it": {
            "status_declared": "Stato dichiarato: {status}",
            "due_date_missing": "Data scadenza non disponibile",
            "due_in_days": "Scade tra {days} giorni",
            "due_today_l1": "Scade oggi — sollecito L1",
            "overdue_days_l1": "Scaduta da {days} giorni — L1",
            "overdue_days_l2": "Scaduta da {days} giorni — L2",
            "overdue_days_l3": "Scaduta da {days} giorni — L3",
        },
        "de": {
            "status_declared": "Angegebener Status: {status}",
            "due_date_missing": "Fälligkeitsdatum nicht verfügbar",
            "due_in_days": "Fällig in {days} Tagen",
            "due_today_l1": "Heute fällig — Mahnstufe L1",
            "overdue_days_l1": "Überfällig seit {days} Tagen — L1",
            "overdue_days_l2": "Überfällig seit {days} Tagen — L2",
            "overdue_days_l3": "Überfällig seit {days} Tagen — L3",
        },
        "fr": {
            "status_declared": "Statut déclaré : {status}",
            "due_date_missing": "Date d'échéance non disponible",
            "due_in_days": "Échéance dans {days} jours",
            "due_today_l1": "Échéance aujourd'hui — relance L1",
            "overdue_days_l1": "En retard de {days} jours — L1",
            "overdue_days_l2": "En retard de {days} jours — L2",
            "overdue_days_l3": "En retard de {days} jours — L3",
        },
        "es": {
            "status_declared": "Estado declarado: {status}",
            "due_date_missing": "Fecha de vencimiento no disponible",
            "due_in_days": "Vence en {days} días",
            "due_today_l1": "Vence hoy — reclamación L1",
            "overdue_days_l1": "Vencida hace {days} días — L1",
            "overdue_days_l2": "Vencida hace {days} días — L2",
            "overdue_days_l3": "Vencida hace {days} días — L3",
        },
        "pt": {
            "status_declared": "Estado declarado: {status}",
            "due_date_missing": "Data de vencimento não disponível",
            "due_in_days": "Vence em {days} dias",
            "due_today_l1": "Vence hoje — cobrança L1",
            "overdue_days_l1": "Vencida há {days} dias — L1",
            "overdue_days_l2": "Vencida há {days} dias — L2",
            "overdue_days_l3": "Vencida há {days} dias — L3",
        },
    },

    # 2. COMPLIANCE FLAGS
    "flags": {
        "en": {
            "critical_overdue_bad_debt_risk": "Overdue exceeds critical threshold (>90 days) — bad debt risk",
            "compliance_threshold_exceeded": "Amount exceeds compliance threshold",
            "high_value_kyc_aml": "High value transaction (KYC/AML verification required)",
            "due_date_missing": "Due date missing from document",
            "negative_amount": "Negative invoice amount detected",
            "unsupported_currency": "Unsupported currency code",
        },
        "it": {
            "critical_overdue_bad_debt_risk": "Scaduta oltre soglia critica (>90 giorni) — rischio inesigibilità",
            "compliance_threshold_exceeded": "Importo superiore alla soglia di conformità",
            "high_value_kyc_aml": "Transazione di importo elevato (verifica KYC/AML richiesta)",
            "due_date_missing": "Data scadenza mancante dal documento",
            "negative_amount": "Rilevato importo negativo fattura",
            "unsupported_currency": "Codice valuta non supportato",
        },
        "de": {
            "critical_overdue_bad_debt_risk": "Kritische Überfälligkeit (>90 Tage) — Ausfallrisiko",
            "compliance_threshold_exceeded": "Betrag überschreitet Compliance-Schwellenwert",
            "high_value_kyc_aml": "Transaktion mit hohem Wert (KYC/AML-Prüfung erforderlich)",
            "due_date_missing": "Fälligkeitsdatum im Dokument nicht vorhanden",
            "negative_amount": "Negativer Rechnungsbetrag festgestellt",
            "unsupported_currency": "Nicht unterstützter Währungscode",
        },
        "fr": {
            "critical_overdue_bad_debt_risk": "Retard critique (>90 jours) — risque d'irrécouvrabilité",
            "compliance_threshold_exceeded": "Montant supérieur au seuil de conformité",
            "high_value_kyc_aml": "Transaction de montant élevé (vérification KYC/AML requise)",
            "due_date_missing": "Date d'échéance absente du document",
            "negative_amount": "Montant de facture négatif détecté",
            "unsupported_currency": "Code de devise non pris en charge",
        },
        "es": {
            "critical_overdue_bad_debt_risk": "Vencimiento crítico (>90 días) — riesgo de impago",
            "compliance_threshold_exceeded": "Importe superior al umbral de cumplimiento",
            "high_value_kyc_aml": "Transacción de alto valor (verificación KYC/AML requerida)",
            "due_date_missing": "Fecha de vencimiento no encontrada en el documento",
            "negative_amount": "Importe de factura negativo detectado",
            "unsupported_currency": "Código de moneda no compatible",
        },
        "pt": {
            "critical_overdue_bad_debt_risk": "Atraso crítico (>90 dias) — risco de inadimplência",
            "compliance_threshold_exceeded": "Montante excede o limiar de conformidade",
            "high_value_kyc_aml": "Transação de valor elevado (verificação KYC/AML necessária)",
            "due_date_missing": "Data de vencimento em falta no documento",
            "negative_amount": "Montante de fatura negativo detetado",
            "unsupported_currency": "Código de moeda não suportado",
        },
    },

    # 3. CANALI DI COMUNICAZIONE
    "channels": {
        "en": {
            "email": "Standard Email",
            "certified_email": "Certified / Registered Email",
            "registered_mail": "Formal Notice / Registered Letter",
            "none": "No action required",
        },
        "it": {
            "email": "Email ordinaria",
            "certified_email": "Posta Elettronica Certificata (PEC)",
            "registered_mail": "Raccomandata A/R / Diffida legale",
            "none": "Nessuna azione richiesta",
        },
        "de": {
            "email": "Standard-E-Mail",
            "certified_email": "Zertifizierte E-Mail",
            "registered_mail": "Einschreiben / Formelle Mahnung",
            "none": "Keine Massnahme erforderlich",
        },
        "fr": {
            "email": "E-mail standard",
            "certified_email": "E-mail certifié",
            "registered_mail": "Lettre recommandée / Mise en demeure",
            "none": "Aucune action requise",
        },
        "es": {
            "email": "Correo electrónico estándar",
            "certified_email": "Correo electrónico certificado",
            "registered_mail": "Burofax / Carta certificada con acuse",
            "none": "No se requiere acción",
        },
        "pt": {
            "email": "E-mail padrão",
            "certified_email": "E-mail certificado / registado",
            "registered_mail": "Carta registada com aviso de receção",
            "none": "Nenhuma ação necessária",
        },
    },

    # 4. RACCOMANDAZIONI COMPLIANCE
    "recommendations": {
        "en": {
            "threshold": "Amount exceeds compliance threshold: authorization required.",
            "legal": "Notice level 3: consult legal counsel prior to formal escalation.",
            "overdue_90": "Overdue exceeds 90 days: evaluate debt recovery or bad debt provisioning.",
            "kyc": "High value amount: verify KYC/AML procedures.",
            "none": "No anomalies detected.",
        },
        "it": {
            "threshold": "Importo superiore alla soglia di conformità: richiesta autorizzazione.",
            "legal": "Sollecito livello 3: consultare l'ufficio legale prima di un'azione formale.",
            "overdue_90": "Scaduta da oltre 90 giorni: valutare recupero crediti o svalutazione.",
            "kyc": "Importo elevato: verificare le procedure antiriciclaggio KYC/AML.",
            "none": "Nessuna anomalia rilevata.",
        },
        "de": {
            "threshold": "Betrag überschreitet Compliance-Schwelle: Genehmigung erforderlich.",
            "legal": "Mahnstufe 3: Vor formellen Schritten Rechtsberatung hinzuziehen.",
            "overdue_90": "Über 90 Tage überfällig: Inkassoverfahren oder Wertberichtigung prüfen.",
            "kyc": "Hoher Betrag: KYC/AML-Compliance-Verfahren überprüfen.",
            "none": "Keine Unregelmäßigkeiten festgestellt.",
        },
        "fr": {
            "threshold": "Montant supérieur au seuil de conformité : autorisation requise.",
            "legal": "Relance niveau 3 : consulter le service juridique avant toute procédure formelle.",
            "overdue_90": "Retard supérieur à 90 jours : évaluer le recouvrement ou la provision pour créance douteuse.",
            "kyc": "Montant élevé : vérifier les procédures de conformité KYC/AML.",
            "none": "Aucune anomalie détectée.",
        },
        "es": {
            "threshold": "Importe superior al umbral de cumplimiento: autorización requerida.",
            "legal": "Nivel de reclamación 3: consultar con asesoría jurídica antes de proceder formalmente.",
            "overdue_90": "Vencimiento superior a 90 días: evaluar cobro de deudas o provisión por insolvencia.",
            "kyc": "Importe elevado: verificar procedimientos KYC/AML.",
            "none": "No se detectaron anomalías.",
        },
        "pt": {
            "threshold": "Valor excede o limite de conformidade: autorização necessária.",
            "legal": "Aviso nível 3: consultar o departamento jurídico antes de qualquer ação formal.",
            "overdue_90": "Vencimento superior a 90 dias: avaliar recuperação de crédito ou imparidade.",
            "kyc": "Valor elevado: verificar procedimentos KYC/AML.",
            "none": "Nenhuma anomalia detetada.",
        },
    },
}

# ---------------------------------------------------------------------------
# ACCESSOR CON REGOLE DI FALLBACK TASSATIVE (FALLBACK SU 'en', MAI SU 'it')
# ---------------------------------------------------------------------------
def normalize_lang(language: Optional[str]) -> str:
    """Restituisce il codice lingua a 2 lettere normalizzato, fallback su 'en'."""
    if not language:
        return DEFAULT_FALLBACK_LANGUAGE
    code = str(language).strip().lower()[:2]
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_FALLBACK_LANGUAGE

def get_text(category: str, key: str, language: Optional[str] = None, **kwargs) -> str:
    """
    Recupera una stringa tradotta con fallback tassativo sull'inglese (EN).
    Se la lingua richiesta non contiene la chiave, carica 'en'.
    Se 'en' non la contiene, restituisce la chiave stessa.
    """
    lang = normalize_lang(language)
    cat_dict = CATALOG.get(category, {})

    # Prova la lingua selezionata
    lang_dict = cat_dict.get(lang, {})
    template = lang_dict.get(key)

    # Se assente e lingua != 'en', fallback tassativo su 'en'
    if template is None:
        template = cat_dict.get(DEFAULT_FALLBACK_LANGUAGE, {}).get(key, str(key))

    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception as e:
            logger.warning(f"Formatting error in i18n key '{key}' ({lang}): {e}")
            return template
    return template

def get_rationale(key: str, language: Optional[str] = None, **params) -> str:
    """Helper per formattare la spiegazione analitica (rationale) con fallback EN."""
    return get_text("rationale", key, language, **params)

def get_flag_description(key: str, language: Optional[str] = None) -> str:
    """Helper per la descrizione tradotta di un flag di conformità."""
    return get_text("flags", key, language)

def get_channel_label(key: str, language: Optional[str] = None) -> str:
    """Helper per la descrizione tradotta del canale di sollecito."""
    return get_text("channels", key, language)

# ---------------------------------------------------------------------------
# POST-PROCESSOR GUARDRAIL & ANTI-LEAK LINTER
# ---------------------------------------------------------------------------
ITALIAN_SPY_PATTERNS = [
    (re.compile(r"\bscadut[aoie]\b", re.IGNORECASE), "overdue"),
    (re.compile(r"\binesigibilit[aà]\b", re.IGNORECASE), "bad debt risk"),
    (re.compile(r"\bgiorn[oi]\b", re.IGNORECASE), "days"),
    (re.compile(r"\bfattur[ae]\b", re.IGNORECASE), "invoice"),
    (re.compile(r"\braccomandat[ae]\b", re.IGNORECASE), "registered mail"),
    (re.compile(r"\bdiffida\b", re.IGNORECASE), "formal notice"),
    (re.compile(r"\bsollecit[oi]\b", re.IGNORECASE), "reminder"),
    (re.compile(r"\bimporto\b", re.IGNORECASE), "amount"),
    (re.compile(r"\bdata emissione\b", re.IGNORECASE), "issue date"),
    (re.compile(r"\bdata scadenza\b", re.IGNORECASE), "due date"),
    (re.compile(r"\blivello\b", re.IGNORECASE), "level"),
    (re.compile(r"\bnessuna anomalia\b", re.IGNORECASE), "no anomalies"),
]

def scan_and_sanitize_text(text: str, language: Optional[str] = None) -> tuple[str, List[str]]:
    """
    Ispeziona un testo per verificare la presenza di leak linguistici italiani quando language != 'it'.
    Se rileva parole spia, le sanifica sostituendole con l'equivalente inglese e restituisce la lista di violazioni.
    """
    lang = normalize_lang(language)
    leaks_found = []
    if lang == "it":
        return text, leaks_found

    sanitized = text
    for pattern, replacement in ITALIAN_SPY_PATTERNS:
        matches = pattern.findall(sanitized)
        if matches:
            for m in set(matches):
                leaks_found.append(m)
            sanitized = pattern.sub(replacement, sanitized)

    if leaks_found:
        logger.warning(f"[ANTI-LEAK GUARDRAIL] Detected Italian leak in {lang.upper()} output: {leaks_found}. Sanitized to English equivalents.")

    return sanitized, leaks_found

def sanitize_data_recursively(obj: Any, language: Optional[str] = None, exclude_keys: Optional[set] = None) -> Any:
    """
    Percorre ricorsivamente dizionari e liste sanitizzando i testi generati dal sistema.
    Non altera i dati anagrafici dei clienti (es. indirizzo cliente con 'via roma').
    """
    lang = normalize_lang(language)
    if lang == "it":
        return obj

    if exclude_keys is None:
        exclude_keys = {"client", "client_address", "client_name", "address", "vendor", "vendor_name", "company_name"}

    if isinstance(obj, str):
        sanitized, _ = scan_and_sanitize_text(obj, lang)
        return sanitized
    elif isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            if k in exclude_keys:
                res[k] = v
            else:
                res[k] = sanitize_data_recursively(v, lang, exclude_keys)
        return res
    elif isinstance(obj, list):
        return [sanitize_data_recursively(item, lang, exclude_keys) for item in obj]
    return obj
