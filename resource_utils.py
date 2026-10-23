"""
ZUKWEND — Multilingual Billing Agent
Modulo: resource_utils.py
Ruolo: Risoluzione percorsi risorse (PyInstaller-safe) e cartelle di scrittura.
Versione: 2.1.4-ENTERPRISE
REPTANA MODE | OLTREVISTA 2030 | Offline-First

Regole:
- Le RISORSE di sola lettura (prompts/, zukwend_config.json di default, assets) vengono
  risolte tramite get_resource_path(): sys._MEIPASS quando l'app e' "frozen" (PyInstaller),
  cartella del sorgente altrimenti.
- Le SCRITTURE (report PDF/DOCX, log, configurazione utente) NON avvengono MAI dentro
  sys._MEIPASS (directory temporanea / _internal): vedi get_output_dir() e get_user_data_dir().
"""

import logging
import os
import sys
import tempfile
from pathlib import Path

APP_VERSION = "2.1.6"
APP_VERSION_FULL = "2.1.6.0"

logger = logging.getLogger("zukwend.resource_utils")


def is_frozen() -> bool:
    """True se l'applicazione gira come eseguibile PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def get_resource_path(relative_path: str) -> str:
    """
    Restituisce il percorso assoluto di una risorsa interna (sola lettura).

    - Eseguibile PyInstaller: base = sys._MEIPASS
    - Sviluppo: base = cartella di questo file
    """
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *str(relative_path).replace("\\", "/").split("/"))


def get_app_dir() -> Path:
    """Cartella dell'applicazione (accanto all'.exe se frozen, altrimenti dei sorgenti)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def is_local_llm_available(host: str = "127.0.0.1", port: int = 11434, timeout: float = 0.5) -> bool:
    """
    Probe TCP sul motore LLM locale (Ollama). Solo loopback, nessun traffico di rete esterno.
    Permette il fallback immediato al Local Engine (Tier 1) senza attese di timeout.
    """
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _is_inside_meipass(path: str) -> bool:
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return False
    try:
        p = os.path.normcase(os.path.abspath(path))
        m = os.path.normcase(os.path.abspath(meipass))
        return os.path.commonpath([p, m]) == m
    except ValueError:  # drive diversi su Windows
        return False


def _is_writable_dir(folder: str) -> bool:
    """Verifica reale di scrivibilita' (os.access non e' affidabile su Windows)."""
    try:
        os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, f".zukwend_write_test_{os.getpid()}")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def get_user_data_dir() -> Path:
    """
    Cartella dati utente scrivibile (%LOCALAPPDATA%\\ZUKWEND su Windows).
    Usata per log e configurazione quando la cartella applicazione non e' scrivibile
    (es. installazione in C:\\Program Files).
    """
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    folder = Path(base) / "ZUKWEND"
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        folder = Path(tempfile.gettempdir()) / "ZUKWEND"
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_writable_dir(preferred: Path, fallback_name: str) -> Path:
    """Restituisce `preferred` se scrivibile, altrimenti <user_data_dir>/<fallback_name>."""
    if not _is_inside_meipass(str(preferred)) and _is_writable_dir(str(preferred)):
        return preferred
    alt = get_user_data_dir() / fallback_name
    alt.mkdir(parents=True, exist_ok=True)
    logger.warning(f"Cartella '{preferred}' non scrivibile: uso '{alt}'")
    return alt


def get_output_dir() -> str:
    """
    Cartella di output dei report: SEMPRE os.getcwd()/output (assoluta), creata se manca.
    Mai dentro sys._MEIPASS. Fallback (cartella non scrivibile o interna al bundle):
    <cartella .exe>/output e, in ultima istanza, %LOCALAPPDATA%\\ZUKWEND\\output.
    """
    primary = os.path.abspath("output")  # == os.path.join(os.getcwd(), "output")
    if not _is_inside_meipass(primary) and _is_writable_dir(primary):
        return primary

    secondary = str(get_app_dir() / "output")
    if not _is_inside_meipass(secondary) and _is_writable_dir(secondary):
        logger.warning(f"Output '{primary}' non utilizzabile: uso '{secondary}'")
        return secondary

    tertiary = str(get_user_data_dir() / "output")
    os.makedirs(tertiary, exist_ok=True)
    logger.warning(f"Output '{primary}' non utilizzabile: uso '{tertiary}'")
    return tertiary
