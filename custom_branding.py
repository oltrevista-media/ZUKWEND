"""
ZUKWEND — Custom Branding Configuration & Manager
Modulo: custom_branding.py
Ruolo: Gestione e persistenza dei dati mittente aziendali per carta intestata:
- Ragione Sociale (company_name)
- Indirizzo (address)
- IBAN (iban)
- Email (email)
- Logo aziendale PNG/JPG (logo_path)
- Watch Directory (watch_folder)

Persistenza: .zukwend/config.json
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

DEFAULT_BRANDING = {
    "company_name": "",
    "address": "",
    "iban": "",
    "email": "",
    "logo_path": "",
    "watch_folder": "",
    "watch_enabled": False,
}

def get_branding_config_paths():
    """Restituisce le posizioni candidate per .zukwend/config.json."""
    candidates = []
    
    # 1. Directory utente corrente (~/.zukwend/config.json)
    try:
        user_dir = Path.home() / ".zukwend"
        candidates.append(user_dir / "config.json")
    except Exception:
        pass

    # 2. Cartella locale del repository / applicazione (C:/OLTREVISTA_AI/.zukwend/config.json)
    app_root = Path(__file__).resolve().parent
    candidates.append(app_root / ".zukwend" / "config.json")
    candidates.append(app_root.parent / ".zukwend" / "config.json")
    
    return candidates

def get_branding() -> Dict[str, Any]:
    """Carica la configurazione di branding salvata, con fallback su default."""
    cfg = dict(DEFAULT_BRANDING)
    for p in get_branding_config_paths():
        try:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # Se i dati sono sotto la chiave 'branding', estraili
                    if "branding" in data and isinstance(data["branding"], dict):
                        cfg.update(data["branding"])
                    else:
                        cfg.update({k: v for k, v in data.items() if k in DEFAULT_BRANDING})
                break
        except Exception:
            continue
    return cfg

def save_branding(data: Dict[str, Any]) -> bool:
    """Salva la configurazione di branding su .zukwend/config.json."""
    current = get_branding()
    current.update({k: str(v).strip() if isinstance(v, str) else v for k, v in data.items() if k in DEFAULT_BRANDING})
    
    saved = False
    for p in get_branding_config_paths():
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            # Leggi eventuale config esistente per non sovrascrivere altre chiavi
            existing = {}
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = {}
            
            existing["branding"] = current
            # Aggiorna anche a livello root per comodità
            for k in DEFAULT_BRANDING:
                existing[k] = current[k]

            with open(p, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            saved = True
        except Exception:
            continue

    return saved
