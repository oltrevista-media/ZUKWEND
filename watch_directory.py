"""
ZUKWEND — Watch Directory Background Daemon
Modulo: watch_directory.py
Ruolo: Monitoraggio autonomo di cartelle locali o di rete (es. C:/Fatture_In_Arrivo/)
ed elaborazione automatica in background delle nuove fatture PDF in arrivo.
Versione: 2.1.5
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Callable, Set

logger = logging.getLogger("zukwend.watch_directory")

class DirectoryWatcher:
    def __init__(
        self,
        watch_folder: str,
        language: str = "it",
        mode: str = "local",
        api_key: Optional[str] = None,
        callback: Optional[Callable[[str, bool, str], None]] = None,
        poll_interval_s: float = 3.0,
    ):
        self.watch_folder = Path(watch_folder)
        self.language = language
        self.mode = mode
        self.api_key = api_key
        self.callback = callback
        self.poll_interval_s = poll_interval_s
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._processed_files: Set[str] = set()

    def start(self) -> bool:
        """Avvia il monitoraggio in un thread background daemon."""
        if self._running:
            logger.info("Watch directory daemon già in esecuzione.")
            return True
        
        if not self.watch_folder.exists():
            try:
                self.watch_folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Impossibile creare cartella di monitoraggio: {e}")
                return False

        # Inizializza con i file già presenti (per non rielaborarli tutti all'avvio)
        try:
            for p in self.watch_folder.glob("*.pdf"):
                self._processed_files.add(str(p.resolve()))
        except Exception:
            pass

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ZukwendWatchDaemon")
        self._thread.start()
        logger.info(f"Watch daemon avviato sulla cartella: {self.watch_folder}")
        return True

    def stop(self):
        """Ferma il monitoraggio."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Watch daemon arrestato.")

    def is_running(self) -> bool:
        return self._running and (self._thread.is_alive() if self._thread else False)

    def _run_loop(self):
        while self._running:
            try:
                if self.watch_folder.exists():
                    for item in self.watch_folder.iterdir():
                        if not self._running:
                            break
                        if item.is_file() and item.suffix.lower() == ".pdf":
                            fpath = str(item.resolve())
                            if fpath not in self._processed_files:
                                # Attendi che il file sia completamente scritto
                                if self._wait_file_ready(item):
                                    self._process_file(item)
                                    self._processed_files.add(fpath)
            except Exception as e:
                logger.error(f"Errore ciclo watch directory: {e}")

            time.sleep(self.poll_interval_s)

    def _wait_file_ready(self, path: Path, max_wait: float = 5.0) -> bool:
        """Verifica che il file sia completamente scritto e leggibile prima dell'elaborazione."""
        start = time.time()
        last_size = -1
        while time.time() - start < max_wait:
            try:
                size = path.stat().st_size
                if size > 0 and size == last_size:
                    # File stabile e non più in scrittura
                    with open(path, "rb") as test_f:
                        test_f.read(16)
                    return True
                last_size = size
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def _process_file(self, pdf_path: Path):
        logger.info(f"[WATCH] Rilevata nuova fattura: {pdf_path.name}. Avvio elaborazione...")
        try:
            from workflow_engine import run_pipeline
            res = run_pipeline(
                pdf_path=str(pdf_path),
                language=self.language,
                mode=self.mode,
                api_key=self.api_key,
                formats=["pdf", "xlsx", "json"],
                is_demo=False
            )
            success = res.success
            msg = f"Fattura {pdf_path.name} elaborata con successo." if success else f"Fattura {pdf_path.name} elaborata con errori."
            logger.info(f"[WATCH] {msg}")
            if self.callback:
                try:
                    self.callback(str(pdf_path), success, msg)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"[WATCH] Errore elaborazione {pdf_path.name}: {e}")
            if self.callback:
                try:
                    self.callback(str(pdf_path), False, str(e))
                except Exception:
                    pass

# Singleton watcher per la GUI
_active_watcher: Optional[DirectoryWatcher] = None

def get_active_watcher() -> Optional[DirectoryWatcher]:
    global _active_watcher
    return _active_watcher

def start_global_watcher(folder: str, language: str = "it", mode: str = "local", api_key: Optional[str] = None, callback: Optional[Callable] = None) -> bool:
    global _active_watcher
    if _active_watcher and _active_watcher.is_running():
        _active_watcher.stop()
    _active_watcher = DirectoryWatcher(
        watch_folder=folder,
        language=language,
        mode=mode,
        api_key=api_key,
        callback=callback
    )
    return _active_watcher.start()

def stop_global_watcher():
    global _active_watcher
    if _active_watcher:
        _active_watcher.stop()
        _active_watcher = None
