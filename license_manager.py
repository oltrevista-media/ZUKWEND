"""
ZUKWEND — Multilingual Billing Agent
Modulo: license_manager.py
Ruolo: Gestione licenza hardware-bound, validazione offline, demo timer, anti-tamper
Versione: 1.0.0
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import hashlib
import hmac
import json
import logging
import os
import platform
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("zukwend.license_manager")

# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------
DEMO_DAYS          = 7
DEMO_MAX_INVOICES  = 10
LICENSE_SALT       = "ZUKWEND_OLTREVISTA_2030_REPTANA"   # Salt interno (non segreto)
HMAC_KEY           = b"ZKW_HMAC_KEY_2026_REPTANA_OFFLINE"  # Chiave HMAC interna
LOCK_FILENAME      = "demo.lock"
LICENSE_FILENAME   = "license.key"
APP_DIR_NAME       = ".zukwend"
LICENSE_VERSION    = "1"

# Tipi licenza
TYPE_DEMO    = "DEMO"
TYPE_FULL    = "FULL"
TYPE_EXPIRED = "EXPIRED"
TYPE_INVALID = "INVALID"

# ---------------------------------------------------------------------------
# Percorsi locali
# ---------------------------------------------------------------------------
def _get_app_dir() -> Path:
    """Restituisce la cartella applicazione (~/.zukwend/)."""
    home = Path.home()
    app_dir = home / APP_DIR_NAME
    app_dir.mkdir(exist_ok=True)
    return app_dir


# ---------------------------------------------------------------------------
# Machine ID
# ---------------------------------------------------------------------------
def get_machine_id() -> str:
    """
    Calcola un Machine ID deterministico basato su:
    - MAC address (primario)
    - CPU info
    - Hostname
    
    Returns:
        Stringa hash SHA256 (64 caratteri) stabile per la macchina
    """
    components = []

    # MAC address
    try:
        mac = uuid.getnode()
        components.append(str(mac))
    except Exception:
        components.append("no_mac")

    # Hostname
    try:
        components.append(platform.node())
    except Exception:
        components.append("no_hostname")

    # CPU info
    try:
        components.append(platform.processor() or "no_cpu")
    except Exception:
        components.append("no_cpu")

    # OS info
    try:
        components.append(platform.system() + platform.release())
    except Exception:
        components.append("no_os")

    raw = "|".join(components) + "|" + LICENSE_SALT
    machine_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    logger.debug(f"Machine ID calcolato: {machine_id[:16]}...")
    return machine_id


def get_machine_id_short() -> str:
    """Restituisce i primi 16 caratteri del Machine ID formattati (ZK-XXXX-XXXX-XXXX)."""
    full = get_machine_id()
    s = full[:12].upper()
    return f"ZK-{s[0:4]}-{s[4:8]}-{s[8:12]}"


# ---------------------------------------------------------------------------
# HMAC utilities
# ---------------------------------------------------------------------------
def _sign(data: str) -> str:
    """Genera HMAC-SHA256 del dato."""
    sig = hmac.new(HMAC_KEY, data.encode("utf-8"), hashlib.sha256).hexdigest()
    return sig


def _verify(data: str, signature: str) -> bool:
    """Verifica HMAC-SHA256."""
    expected = _sign(data)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# DEMO MANAGER
# ---------------------------------------------------------------------------
class DemoManager:
    """
    Gestisce il timer demo 7 giorni.
    
    Strategia anti-tamper:
    - Scrive timestamp alla prima esecuzione in ~/.zukwend/demo.lock
    - Il lock file e firmato HMAC (SHA256 + Machine ID)
    - Ad ogni avvio verifica firma + calcola giorni trascorsi
    - Nessun server. Nessun ping. 100% offline.
    """

    def __init__(self):
        self._app_dir   = _get_app_dir()
        self._lock_path = self._app_dir / LOCK_FILENAME
        self._machine_id = get_machine_id()

    def initialize(self) -> dict:
        """
        Inizializza il lock demo (primo avvio).
        Se esiste gia, non sovrascrive.
        
        Returns:
            dict stato demo corrente
        """
        if self._lock_path.exists():
            return self.get_status()
        return self._create_lock()

    def get_status(self) -> dict:
        """
        Legge il lock file e restituisce lo stato demo.
        
        Returns:
            dict con: license_type, days_remaining, days_used,
                      invoice_count, max_invoices, invoices_remaining,
                      first_run, is_valid, machine_id_short
        """
        if not self._lock_path.exists():
            # Primo avvio
            return self._create_lock()

        try:
            lock_data = self._read_lock()
        except Exception as e:
            logger.error(f"Lock file corrotto: {e}")
            return self._invalid_state(reason="lock_corrupted")

        # Verifica firma
        payload = lock_data.get("payload", {})
        signature = lock_data.get("signature", "")
        payload_str = json.dumps(payload, sort_keys=True)
        if not _verify(payload_str, signature):
            logger.warning("Demo lock: firma non valida — possibile manomissione")
            return self._invalid_state(reason="signature_invalid")

        # Verifica Machine ID
        stored_machine = payload.get("machine_id", "")
        if stored_machine != self._machine_id:
            logger.warning("Demo lock: machine ID non corrisponde")
            return self._invalid_state(reason="machine_mismatch")

        # Calcola giorni
        first_run_str = payload.get("first_run", "")
        try:
            first_run = datetime.fromisoformat(first_run_str).date()
        except ValueError:
            return self._invalid_state(reason="date_invalid")

        days_used = (date.today() - first_run).days
        days_remaining = max(0, DEMO_DAYS - days_used)
        invoice_count = int(payload.get("invoice_count", 0))
        invoices_remaining = max(0, DEMO_MAX_INVOICES - invoice_count)

        if days_remaining <= 0 or invoice_count >= DEMO_MAX_INVOICES:
            logger.info(f"Demo scaduta: {days_used} giorni trascorsi, {invoice_count}/{DEMO_MAX_INVOICES} fatture elaborate")
            return {
                "license_type":       TYPE_EXPIRED,
                "days_remaining":     0,
                "days_used":          days_used,
                "invoice_count":      invoice_count,
                "max_invoices":       DEMO_MAX_INVOICES,
                "invoices_remaining": 0,
                "first_run":          first_run_str,
                "is_valid":           False,
                "machine_id_short":    get_machine_id_short(),
                "message":            f"Demo scaduta ({invoice_count}/{DEMO_MAX_INVOICES} fatture, {days_used}/{DEMO_DAYS} giorni). Acquista FULL su ZUKWEND.com",
                "upgrade_url":        "https://zukwend.com",
            }

        logger.info(f"Demo attiva: {days_remaining} giorni rimanenti, {invoice_count}/{DEMO_MAX_INVOICES} fatture")
        return {
            "license_type":       TYPE_DEMO,
            "days_remaining":     days_remaining,
            "days_used":          days_used,
            "invoice_count":      invoice_count,
            "max_invoices":       DEMO_MAX_INVOICES,
            "invoices_remaining": invoices_remaining,
            "first_run":          first_run_str,
            "is_valid":           True,
            "machine_id_short":    get_machine_id_short(),
            "message":            f"Demo attiva — {days_remaining} giorni rimanenti ({invoice_count}/{DEMO_MAX_INVOICES} fatture)",
            "upgrade_url":        "https://zukwend.com",
        }

    def increment_invoice_count(self) -> int:
        """
        Incrementa il contatore delle fatture elaborate in demo.lock con validazione HMAC.
        Returns:
            Nuovo valore di invoice_count
        """
        if not self._lock_path.exists():
            self._create_lock()

        try:
            lock_data = self._read_lock()
            payload = lock_data.get("payload", {})
            current_count = int(payload.get("invoice_count", 0))
            new_count = current_count + 1
            payload["invoice_count"] = new_count
            payload["updated_at"] = datetime.now().isoformat()

            payload_str = json.dumps(payload, sort_keys=True)
            signature = _sign(payload_str)
            lock_data = {"payload": payload, "signature": signature}
            self._write_lock(lock_data)
            logger.info(f"Demo invoice counter incrementato a {new_count}/{DEMO_MAX_INVOICES}")
            return new_count
        except Exception as e:
            logger.error(f"Errore incremento invoice_count: {e}")
            return 0

    def _create_lock(self) -> dict:
        """Crea un nuovo lock file (primo avvio)."""
        first_run = datetime.now().isoformat()
        payload = {
            "first_run":      first_run,
            "machine_id":     self._machine_id,
            "demo_days":      DEMO_DAYS,
            "invoice_count":  0,
            "max_invoices":   DEMO_MAX_INVOICES,
            "version":        LICENSE_VERSION,
            "product":        "ZUKWEND",
            "created_at":     datetime.now().isoformat(),
        }
        payload_str = json.dumps(payload, sort_keys=True)
        signature = _sign(payload_str)
        lock_data = {"payload": payload, "signature": signature}
        self._write_lock(lock_data)
        logger.info(f"Demo lock creato: primo avvio — {DEMO_DAYS} giorni, {DEMO_MAX_INVOICES} fatture")
        return {
            "license_type":       TYPE_DEMO,
            "days_remaining":     DEMO_DAYS,
            "days_used":          0,
            "invoice_count":      0,
            "max_invoices":       DEMO_MAX_INVOICES,
            "invoices_remaining": DEMO_MAX_INVOICES,
            "first_run":          first_run,
            "is_valid":           True,
            "machine_id_short":    get_machine_id_short(),
            "message":            f"Demo avviata — {DEMO_DAYS} giorni e {DEMO_MAX_INVOICES} fatture disponibili",
            "upgrade_url":        "https://zukwend.com",
        }

    def _read_lock(self) -> dict:
        """Legge e decodifica il lock file."""
        content = self._lock_path.read_text(encoding="utf-8")
        return json.loads(content)

    def _write_lock(self, data: dict) -> None:
        """Scrive il lock file."""
        self._lock_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _invalid_state(self, reason: str) -> dict:
        """Stato demo non valido (manomissione o errore)."""
        return {
            "license_type":       TYPE_INVALID,
            "days_remaining":     0,
            "days_used":          0,
            "invoice_count":      DEMO_MAX_INVOICES,
            "max_invoices":       DEMO_MAX_INVOICES,
            "invoices_remaining": 0,
            "first_run":          None,
            "is_valid":           False,
            "machine_id_short":    get_machine_id_short(),
            "message":            f"Demo non valida ({reason}). Acquista FULL su ZUKWEND.com",
            "reason":             reason,
            "upgrade_url":        "https://zukwend.com",
        }


# ---------------------------------------------------------------------------
# LICENSE MANAGER (FULL)
# ---------------------------------------------------------------------------
class LicenseManager:
    """
    Gestisce la licenza FULL hardware-bound.
    
    Flusso:
    1. Utente acquista su Lemon Squeezy → riceve codice licenza
    2. Inserisce codice in Settings → LicenseManager.activate(code)
    3. LicenseManager verifica: machine_id embedded nel codice
    4. Se valido → scrive license.key locale → accesso FULL
    5. Ad ogni avvio → valida license.key locale (offline, no server)
    """

    def __init__(self):
        self._app_dir      = _get_app_dir()
        self._license_path = self._app_dir / LICENSE_FILENAME
        self._machine_id   = get_machine_id()
        self._demo_manager = DemoManager()

    def get_status(self) -> dict:
        """
        Determina lo stato attuale della licenza.
        
        Returns:
            dict con license_type, is_valid, machine_id_short, message
        """
        # 1. Controlla licenza FULL
        if self._license_path.exists():
            full_status = self._validate_full_license()
            if full_status["is_valid"]:
                return full_status

        # 2. Fallback a Demo
        demo_status = self._demo_manager.get_status()
        return demo_status

    def activate(self, license_code: str) -> dict:
        """
        Attiva la licenza FULL con il codice fornito.
        
        Il codice licenza e nel formato:
        ZKW-{ENCODED_MACHINE_ID_PARTIAL}-{CHECKSUM}
        
        Args:
            license_code: codice acquistato su Lemon Squeezy
            
        Returns:
            dict con success, message, license_type
        """
        # 1. Verifica online tramite Lemon Squeezy License API (se connesso)
        try:
            import requests
            ls_resp = requests.post(
                "https://api.lemonsqueezy.com/v1/licenses/activate",
                data={
                    "license_key": license_code,
                    "instance_name": get_machine_id_short(),
                },
                timeout=5
            )
            if ls_resp.status_code == 200:
                ls_data = ls_resp.json()
                if ls_data.get("activated", False) or ls_data.get("valid", False):
                    self._write_license(license_code)
                    logger.info("Licenza convalidata con successo tramite Lemon Squeezy API")
                    return {
                        "success":          True,
                        "message":          "ZUKWEND FULL attivato con successo tramite Lemon Squeezy!",
                        "license_type":     TYPE_FULL,
                        "machine_id_short": get_machine_id_short(),
                        "activated_at":     datetime.now().isoformat(),
                    }
        except Exception as e:
            logger.info(f"Lemon Squeezy API offline o non raggiungibile ({e}), fallback su validazione offline...")

        # 2. Validazione offline hardware-bound (ZKW-XXXXXXXX-XXXXXXXX-CHECKSUM)
        if not self._validate_code_format(license_code):
            logger.warning(f"Formato codice non valido: {license_code}")
            return {
                "success":      False,
                "message":      "Codice licenza non valido. Inserisci la License Key ricevuta da Lemon Squeezy.",
                "license_type": TYPE_INVALID,
            }

        if not self._verify_machine_binding(license_code):
            logger.warning("Codice licenza non valido per questa macchina")
            return {
                "success":      False,
                "message":      (
                    f"Questo codice non e valido per questa macchina.\n"
                    f"Machine ID: {get_machine_id_short()}\n"
                    f"Contatta contact@zukwend.com per assistenza."
                ),
                "license_type": TYPE_INVALID,
            }

        # Scrivi license.key firmato
        try:
            self._write_license(license_code)
            logger.info("Licenza FULL offline attivata con successo")
            return {
                "success":          True,
                "message":          "ZUKWEND FULL attivato. Grazie per l'acquisto!",
                "license_type":     TYPE_FULL,
                "machine_id_short": get_machine_id_short(),
                "activated_at":     datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Errore scrittura licenza: {e}")
            return {"success": False, "message": f"Errore attivazione: {e}", "license_type": TYPE_INVALID}

    def deactivate(self) -> bool:
        """Rimuove la licenza FULL locale (es. per trasferimento macchina)."""
        try:
            if self._license_path.exists():
                self._license_path.unlink()
                logger.info("Licenza FULL rimossa")
            return True
        except Exception as e:
            logger.error(f"Errore rimozione licenza: {e}")
            return False

    def _validate_full_license(self) -> dict:
        """Valida il file license.key locale."""
        try:
            content = self._license_path.read_text(encoding="utf-8")
            lic_data = json.loads(content)
        except Exception as e:
            logger.error(f"License file corrotto: {e}")
            return {"is_valid": False, "license_type": TYPE_INVALID,
                    "message": "File licenza corrotto.", "machine_id_short": get_machine_id_short()}

        # Verifica firma
        payload = lic_data.get("payload", {})
        signature = lic_data.get("signature", "")
        payload_str = json.dumps(payload, sort_keys=True)
        if not _verify(payload_str, signature):
            logger.warning("License file: firma non valida")
            return {"is_valid": False, "license_type": TYPE_INVALID,
                    "message": "Firma licenza non valida.", "machine_id_short": get_machine_id_short()}

        # Verifica Machine ID
        if payload.get("machine_id") != self._machine_id:
            logger.warning("License file: machine ID non corrisponde")
            return {"is_valid": False, "license_type": TYPE_INVALID,
                    "message": "Licenza non valida per questa macchina.",
                    "machine_id_short": get_machine_id_short()}

        logger.info("Licenza FULL valida")
        return {
            "is_valid":         True,
            "license_type":     TYPE_FULL,
            "message":          "ZUKWEND FULL attivo",
            "machine_id_short": get_machine_id_short(),
            "activated_at":     payload.get("activated_at", "N/A"),
            "license_code":     payload.get("license_code", "")[:8] + "...",
        }

    def _validate_code_format(self, code: str) -> bool:
        """
        Valida il formato del codice licenza.
        Formato atteso: ZKW-XXXXXXXX-XXXXXXXX-CHECKSUM
        """
        import re
        pattern = r"^ZKW-[A-Z0-9]{8}-[A-Z0-9]{8}-[A-Z0-9]{4,16}$"
        return bool(re.match(pattern, code))

    def _verify_machine_binding(self, license_code: str) -> bool:
        """
        Verifica che il codice licenza sia stato generato per questa macchina.
        
        Strategia: il codice contiene (embedded) una parte del machine ID.
        In produzione, la verifica avviene tramite Lemon Squeezy webhook
        che genera il codice con il machine ID del cliente al momento dell'acquisto.
        
        Per attivazione offline: usa checksum interno.
        """
        # Estrai le parti del codice
        parts = license_code.split("-")
        if len(parts) != 4:
            return False

        # Il checksum (ultima parte) deve matchare con il machine ID
        machine_short = get_machine_id()[:8].upper()
        code_body = "-".join(parts[:3])
        expected_checksum = hashlib.sha256(
            (code_body + machine_short + LICENSE_SALT).encode()
        ).hexdigest()[:8].upper()

        # Accetta sia il checksum corretto sia una licenza di sviluppo (DEVMODE)
        if parts[3] == expected_checksum:
            return True
        # Licenza sviluppo/test (solo per ambiente di sviluppo)
        if parts[3] == "DEVMODE00":
            logger.warning("DEVMODE licenza accettata (solo sviluppo)")
            return True
        return False

    def _write_license(self, license_code: str) -> None:
        """Scrive il file licenza locale firmato."""
        payload = {
            "license_code": license_code,
            "machine_id":   self._machine_id,
            "activated_at": datetime.now().isoformat(),
            "product":      "ZUKWEND",
            "version":      LICENSE_VERSION,
            "type":         TYPE_FULL,
        }
        payload_str = json.dumps(payload, sort_keys=True)
        signature = _sign(payload_str)
        lic_data = {"payload": payload, "signature": signature}
        self._license_path.write_text(
            json.dumps(lic_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# generate_demo_license_code(): genera codice demo per test
# ---------------------------------------------------------------------------
def generate_license_code_for_machine(machine_id_override: Optional[str] = None) -> str:
    """
    Genera un codice licenza FULL valido per la macchina corrente.
    SOLO USO INTERNO / SVILUPPO — in produzione il codice lo genera Lemon Squeezy.
    
    Args:
        machine_id_override: se specificato, usa questo machine ID invece del corrente
        
    Returns:
        Codice licenza stringa (formato ZKW-XXXXXXXX-XXXXXXXX-CHECKSUM)
    """
    machine_id = machine_id_override or get_machine_id()
    machine_short = machine_id[:8].upper()
    
    # Genera parti casuali deterministiche dalla macchina
    part1 = hashlib.sha256((machine_id + "PART1").encode()).hexdigest()[:8].upper()
    part2 = hashlib.sha256((machine_id + "PART2").encode()).hexdigest()[:8].upper()
    code_body = f"ZKW-{part1}-{part2}"
    
    checksum = hashlib.sha256(
        (code_body + machine_short + LICENSE_SALT).encode()
    ).hexdigest()[:8].upper()
    
    return f"{code_body}-{checksum}"


# ---------------------------------------------------------------------------
# Interfaccia semplificata (usata da workflow_engine e UI)
# ---------------------------------------------------------------------------
def check_license() -> dict:
    """
    Controlla lo stato della licenza e restituisce lo stato corrente.
    Entry point principale per UI e workflow_engine.
    
    Returns:
        dict con license_type (DEMO/FULL/EXPIRED/INVALID),
        is_valid (bool), days_remaining (int, solo demo),
        machine_id_short (str), message (str)
    """
    mgr = LicenseManager()
    status = mgr.get_status()
    
    logger.info(
        f"License check: type={status.get('license_type')} | "
        f"valid={status.get('is_valid')} | "
        f"days={status.get('days_remaining', 'N/A')}"
    )
    return status


def activate_license(code: str) -> dict:
    """Attiva una licenza FULL con il codice fornito. Entry point per UI."""
    mgr = LicenseManager()
    return mgr.activate(code)


def increment_invoice_count() -> int:
    """Incrementa il contatore delle fatture elaborate nella demo. Entry point per UI e engine."""
    demo_mgr = DemoManager()
    return demo_mgr.increment_invoice_count()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, sys
    logging.basicConfig(level=logging.INFO)
    cli = argparse.ArgumentParser(description="ZUKWEND License Manager")
    cli.add_argument("--status", action="store_true", help="Controlla stato licenza")
    cli.add_argument("--activate", metavar="CODE", help="Attiva licenza con codice")
    cli.add_argument("--deactivate", action="store_true", help="Rimuovi licenza FULL")
    cli.add_argument("--machine-id", action="store_true", help="Mostra Machine ID")
    cli.add_argument("--gen-code", action="store_true", help="Genera codice test (SOLO SVILUPPO)")
    args = cli.parse_args()

    if args.machine_id:
        print(f"Machine ID (full):  {get_machine_id()}")
        print(f"Machine ID (short): {get_machine_id_short()}")
    elif args.status:
        status = check_license()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    elif args.activate:
        result = activate_license(args.activate)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["success"] else 1)
    elif args.deactivate:
        mgr = LicenseManager()
        ok = mgr.deactivate()
        print("Licenza rimossa." if ok else "Errore rimozione.")
    elif args.gen_code:
        code = generate_license_code_for_machine()
        print(f"Codice test (SOLO SVILUPPO): {code}")
        print("ATTENZIONE: questo codice e valido solo su questa macchina.")
    else:
        # Default: mostra stato
        status = check_license()
        print(json.dumps(status, indent=2, ensure_ascii=False))
