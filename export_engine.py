"""
ZUKWEND — Multilingual Billing Agent
Modulo: export_engine.py
Ruolo: Engine export multi-formato, batch export, audit log, struttura cartelle
Versione: 2.1.3
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import json
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from i18n_catalog import get_aging_bucket

try:
    from resource_utils import get_output_dir, get_writable_dir
except ImportError:  # pragma: no cover - esecuzione isolata del modulo
    def get_output_dir() -> str:
        folder = os.path.abspath("output")
        os.makedirs(folder, exist_ok=True)
        return folder

    def get_writable_dir(preferred: Path, fallback_name: str) -> Path:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred

logger = logging.getLogger("zukwend.export_engine")

_TS_SUFFIX_RE = re.compile(r"_\d{8}_\d{6}(?:_\d+)?$")

def _is_lock_error(exc: BaseException) -> bool:
    """True per PermissionError / WinError 5 / WinError 32 / qualsiasi OSError di scrittura."""
    return isinstance(exc, (PermissionError, OSError))

def _get_unique_fallback_path(target_path: Path) -> Path:
    """
    Genera un nome file univoco con timestamp in caso di file bloccato o PermissionError/WinError 5.
    Formato: report_AR_INV123_YYYYMMDD_HHMMSS.pdf (un eventuale timestamp finale viene sostituito).
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = _TS_SUFFIX_RE.sub("", target_path.stem)
    ext = target_path.suffix
    parent = target_path.parent
    parent.mkdir(parents=True, exist_ok=True)

    alt_path = parent / f"{stem}_{ts}{ext}"
    counter = 1
    while alt_path.exists() or alt_path == target_path:
        alt_path = parent / f"{stem}_{ts}_{counter}{ext}"
        counter += 1
    return alt_path

# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------
SUPPORTED_FORMATS = {"pdf", "docx", "json", "html", "xlsx"}

# ---------------------------------------------------------------------------
# Funzione principale: export()
# ---------------------------------------------------------------------------
def export(
    report: dict,
    output_dir: Optional[str] = None,
    organize_by_date: bool = True,
) -> list:
    """
    Finalizza e organizza i file generati dal report_generator.

    Args:
        report: dict output di report_generator.generate()
                Deve contenere: {'paths': {'pdf': ..., 'json': ...}, ...}
        output_dir: cartella destinazione finale (default: ./output/)
        organize_by_date: se True, organizza in sottocartelle YYYY-MM-DD/

    Returns:
        Lista di percorsi file esportati (str)
    """
    exported_paths = []
    errors = []

    if not report or not report.get("paths"):
        logger.warning("export(): no files to export (report or report.paths empty)")
        return []

    # Cartella output principale con creazione automatica preventiva
    outputFolder = get_output_dir()
    out_root = Path(output_dir) if output_dir else Path(outputFolder)
    out_root.mkdir(parents=True, exist_ok=True)

    # Sottocartella per data (opzionale)
    if organize_by_date:
        date_folder = out_root / datetime.now().strftime("%Y-%m-%d")
        date_folder.mkdir(parents=True, exist_ok=True)
        dest_dir = date_folder
    else:
        dest_dir = out_root

    # Percorsi file sorgente dal report
    source_paths = report.get("paths", {})
    base_name    = report.get("base_name", "report_unknown")

    if not source_paths:
        logger.warning("export(): no files to export (report.paths empty)")
        return []

    # Copia / sposta file nella destinazione finale
    for fmt, src_path in source_paths.items():
        if not src_path:
            continue
        src = Path(src_path)
        if not src.exists():
            logger.warning(f"Source file not found: {src}")
            errors.append(f"not_found:{src}")
            continue
        # Se e gia nella cartella dest, non spostare
        dest = dest_dir / src.name
        if src.resolve() != dest.resolve():
            try:
                shutil.copy2(str(src), str(dest))
                logger.info(f"Export {fmt.upper()}: {src.name} -> {dest}")
                try:
                    src.unlink()
                except Exception:
                    pass
            except (PermissionError, OSError) as e:
                if _is_lock_error(e):
                    alt_dest = _get_unique_fallback_path(dest)
                    logger.warning(
                        f"[LOCK_RECOVERY] Export destination '{dest.name}' locked ({e}). "
                        f"Saving with unique timestamp to '{alt_dest.name}'..."
                    )
                    try:
                        shutil.copy2(str(src), str(alt_dest))
                        dest = alt_dest
                        logger.info(f"Export {fmt.upper()} (recovery): {src.name} -> {dest}")
                        try:
                            src.unlink()
                        except Exception:
                            pass
                    except Exception as e2:
                        logger.error(
                            f"[LOCK_ERROR] Locked file recovery failed ({e2}). "
                            f"Pipeline continues."
                        )
                        errors.append(f"copy_error_locked:{fmt}:{e2}")
                        dest = src  # usa percorso originale
                else:
                    logger.error(f"Copy error {fmt}: {e}")
                    errors.append(f"copy_error:{fmt}:{e}")
                    dest = src
            except Exception as e:
                logger.error(f"Copy error {fmt}: {e}")
                errors.append(f"copy_error:{fmt}:{e}")
                dest = src  # usa percorso originale

        report.setdefault("paths", {})[fmt] = str(dest)
        exported_paths.append(str(dest))

    report["output_dir"] = str(dest_dir)

    # Post-Processor Anti-Leak Guardrail su tutti i file esportati
    lang = (report.get("language") or report.get("report_data", {}).get("language") or "").lower()
    if lang and lang != "it":
        from i18n_catalog import scan_and_sanitize_text
        for p_str in list(exported_paths):
            p_file = Path(p_str)
            if p_file.suffix.lower() == ".json":
                try:
                    raw_j = p_file.read_text(encoding="utf-8")
                    clean_j, leaks = scan_and_sanitize_text(raw_j, lang)
                    if leaks:
                        logger.warning(f"[ANTI-LEAK GUARDRAIL] Leak intercettato in {p_file.name}: {leaks}. Sanificato.")
                        p_file.write_text(clean_j, encoding="utf-8")
                except Exception as ex_leak:
                    logger.warning(f"Errore linter anti-leak su {p_file.name}: {ex_leak}")

    # Scrivi audit log export
    _write_export_audit_log(dest_dir, base_name, exported_paths, errors, report)

    logger.info(f"Export completed: {len(exported_paths)} files | {len(errors)} errors")
    return exported_paths


# ---------------------------------------------------------------------------
# Batch export
# ---------------------------------------------------------------------------
def export_batch(
    reports: list,
    output_dir: Optional[str] = None,
    include_aging_summary: bool = True,
) -> dict:
    """
    Esegue l'export di una lista di report (batch di fatture).

    Args:
        reports: lista di dict output di report_generator.generate()
        output_dir: cartella output principale
        include_aging_summary: genera aging_summary JSON + log

    Returns:
        dict con 'all_paths', 'batch_dir', 'aging_summary_path', 'errors'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outputFolder = get_output_dir()
    out_root = Path(output_dir) if output_dir else Path(outputFolder)
    batch_dir = out_root / f"batch_{timestamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    all_paths = []
    all_errors = []
    batch_meta = []

    logger.info(f"Batch export: {len(reports)} report -> {batch_dir}")

    for i, report in enumerate(reports):
        try:
            paths = export(report, output_dir=str(batch_dir), organize_by_date=False)
            all_paths.extend(paths)
            batch_meta.append({
                "index": i,
                "invoice_number": _get_invoice_number_from_report(report),
                "paths": paths,
                "exported_at": datetime.now().isoformat(),
            })
        except Exception as e:
            logger.error(f"Batch export errore report {i}: {e}")
            all_errors.append({"index": i, "error": str(e)})

    # Aging summary
    aging_path = None
    if include_aging_summary:
        try:
            aging_path = _generate_aging_summary(reports, batch_dir, timestamp)
            all_paths.append(str(aging_path))
        except Exception as e:
            logger.error(f"Aging summary errore: {e}")
            all_errors.append({"step": "aging_summary", "error": str(e)})

    # Batch log
    log_path = batch_dir / f"batch_log_{timestamp}.txt"
    _write_batch_log(log_path, batch_meta, all_errors, timestamp)

    logger.info(
        f"Batch completato: {len(all_paths)} file | dir={batch_dir} | errori={len(all_errors)}"
    )
    return {
        "all_paths":           all_paths,
        "batch_dir":           str(batch_dir),
        "aging_summary_path":  str(aging_path) if aging_path else None,
        "batch_log_path":      str(log_path),
        "total_reports":       len(reports),
        "successful_exports":  len(batch_meta),
        "errors":              all_errors,
    }


# ---------------------------------------------------------------------------
# Aging summary
# ---------------------------------------------------------------------------
def _generate_aging_summary(reports: list, dest_dir: Path, timestamp: str) -> Path:
    """Genera il file aging_summary JSON da una lista di report."""
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_invoices": len(reports),
        "by_level": {
            "L0": {"count": 0, "total_amount": 0.0, "invoices": []},
            "L1": {"count": 0, "total_amount": 0.0, "invoices": []},
            "L2": {"count": 0, "total_amount": 0.0, "invoices": []},
            "L3": {"count": 0, "total_amount": 0.0, "invoices": []},
        },
        "by_bucket": {
            "Current / Not Due": {"count": 0, "total_amount": 0.0, "invoices": []},
            "0-30 Days": {"count": 0, "total_amount": 0.0, "invoices": []},
            "31-60 Days": {"count": 0, "total_amount": 0.0, "invoices": []},
            "61-90 Days": {"count": 0, "total_amount": 0.0, "invoices": []},
            "90+ Days (Critical)": {"count": 0, "total_amount": 0.0, "invoices": []},
        },
        "total_overdue_amount": 0.0,
        "currency": "EUR",
        "compliance_flags_total": 0,
    }

    for report in reports:
        # Cerca dati dal report (struttura report_generator.generate())
        report_data_path = _find_json_path(report)
        if report_data_path:
            try:
                with open(report_data_path, encoding="utf-8") as f:
                    rdata = json.load(f)
                inv    = rdata.get("invoice", {})
                clf    = rdata.get("classification", {})
                level  = clf.get("reminder_level", 0)
                amount = float(inv.get("amount", 0.0) or 0.0)
                currency = inv.get("currency", "EUR")
                summary["currency"] = currency
                key = f"L{level}" if level in [0,1,2,3] else "L0"
                summary["by_level"][key]["count"] += 1
                summary["by_level"][key]["total_amount"] += amount
                summary["by_level"][key]["invoices"].append(inv.get("number", "N/A"))

                # Aging bucket breakdown
                b_key = clf.get("aging_bucket") or get_aging_bucket(clf.get("days_overdue", 0))
                if b_key not in summary["by_bucket"]:
                    b_key = "Current / Not Due"
                summary["by_bucket"][b_key]["count"] += 1
                summary["by_bucket"][b_key]["total_amount"] += amount
                summary["by_bucket"][b_key]["invoices"].append(inv.get("number", "N/A"))

                if level > 0:
                    summary["total_overdue_amount"] += amount
                if clf.get("compliance_flag"):
                    summary["compliance_flags_total"] += 1
            except Exception as e:
                logger.warning(f"Aging summary: errore lettura report JSON: {e}")

    # Arrotonda
    for k in summary["by_level"]:
        summary["by_level"][k]["total_amount"] = round(summary["by_level"][k]["total_amount"], 2)
    for k in summary["by_bucket"]:
        summary["by_bucket"][k]["total_amount"] = round(summary["by_bucket"][k]["total_amount"], 2)
    summary["total_overdue_amount"] = round(summary["total_overdue_amount"], 2)

    path = dest_dir / f"aging_summary_{timestamp}.json"
    target_path = path
    try:
        target_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    except (PermissionError, OSError) as e:
        if _is_lock_error(e):
            target_path = _get_unique_fallback_path(path)
            logger.warning(f"[LOCK_RECOVERY] Aging summary bloccato ({e}). Scrittura su: '{target_path.name}'")
            target_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            raise e
    logger.info(f"Aging summary: {target_path}")
    return target_path


def _find_json_path(report: dict) -> Optional[str]:
    """Estrae il percorso JSON da un report dict."""
    paths = report.get("paths", {})
    return paths.get("json") or paths.get("JSON")


def _get_invoice_number_from_report(report: dict) -> str:
    """Estrae il numero fattura dal nome base del report."""
    base = report.get("base_name", "")
    parts = base.replace("report_AR_", "").split("_")
    return parts[0] if parts else "N/A"


# ---------------------------------------------------------------------------
# Audit log export
# ---------------------------------------------------------------------------
def _write_export_audit_log(
    dest_dir: Path,
    base_name: str,
    exported_paths: list,
    errors: list,
    report: dict,
) -> None:
    """Scrive il log di audit per ogni operazione di export."""
    try:
        log_dir = get_writable_dir(Path(os.path.abspath("logs")), "logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"zukwend_audit_{datetime.now().strftime('%Y%m%d')}.log"

        entry_lines = [
            f"[{datetime.now().isoformat()}] [EXPORT] [INFO]",
            f"  Base:    {base_name}",
            f"  Dir:     {os.path.normpath(str(dest_dir))}",
            f"  Files:   {', '.join(os.path.normpath(p) for p in exported_paths) if exported_paths else 'none'}",
            f"  Errors:  {errors}",
            f"  External: NO",
            "",
        ]
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n".join(entry_lines))
    except (PermissionError, OSError) as e:
        logger.warning(f"Audit log non scrivibile o bloccato ({e}). La pipeline continua.")
    except Exception as e:
        logger.warning(f"Errore scrittura audit log: {e}")


def _write_batch_log(log_path: Path, batch_meta: list, errors: list, timestamp: str) -> None:
    """Scrive il log batch testuale."""
    lines = [
        f"ZUKWEND — Batch Export Log",
        f"Timestamp: {timestamp}",
        f"Totale report: {len(batch_meta)}",
        f"Errori: {len(errors)}",
        "=" * 60,
    ]
    for meta in batch_meta:
        lines.append(
            f"[{meta['index']:03d}] {meta.get('invoice_number','N/A')} -> {meta.get('paths', [])}"
        )
    if errors:
        lines.append("=" * 60)
        lines.append("ERRORI:")
        for err in errors:
            lines.append(f"  {err}")
    lines.append("=" * 60)
    lines.append("Nessun dato inviato esternamente. Offline-First.")
    
    target_path = log_path
    try:
        target_path.write_text("\n".join(lines), encoding="utf-8")
    except (PermissionError, OSError) as e:
        if _is_lock_error(e):
            target_path = _get_unique_fallback_path(log_path)
            logger.warning(f"[LOCK_RECOVERY] Batch log bloccato ({e}). Scrittura su '{target_path.name}'")
            target_path.write_text("\n".join(lines), encoding="utf-8")
        else:
            raise e
    logger.info(f"Batch log: {target_path}")


# ---------------------------------------------------------------------------
# ensure_output_structure(): crea la struttura cartelle ZUKWEND
# ---------------------------------------------------------------------------
def ensure_output_structure(base_dir: Optional[str] = None) -> dict:
    """
    Crea/verifica la struttura cartelle output di ZUKWEND.

    Returns:
        dict con i percorsi delle cartelle create
    """
    outputFolder = get_output_dir()
    root = Path(base_dir) if base_dir else Path(outputFolder)
    folders = {
        "root":        root,
        "reports":     root / "reports",
        "batch":       root / "batch",
        "logs":        root / "logs",
        "temp":        root / "temp",
    }
    for name, folder in folders.items():
        folder.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Cartella verificata: {folder}")

    logger.info(f"Struttura output verificata in: {root}")
    return {k: str(v) for k, v in folders.items()}


# ---------------------------------------------------------------------------
# validate_export(): verifica integrità file esportati
# ---------------------------------------------------------------------------
def validate_export(paths: list) -> dict:
    """
    Verifica che i file esportati esistano e abbiano dimensione > 0.

    Args:
        paths: lista percorsi file da verificare

    Returns:
        dict con 'valid', 'invalid', 'all_ok'
    """
    valid   = []
    invalid = []
    for p in paths:
        path = Path(p)
        if path.exists() and path.stat().st_size > 0:
            valid.append(str(path))
        else:
            invalid.append(str(path))
            logger.warning(f"File non valido o vuoto: {p}")

    result = {"valid": valid, "invalid": invalid, "all_ok": len(invalid) == 0}
    logger.info(f"Validation: {len(valid)} OK | {len(invalid)} KO")
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, sys
    logging.basicConfig(level=logging.INFO)
    cli = argparse.ArgumentParser(description="ZUKWEND Export Engine")
    cli.add_argument("--mode", choices=["single","batch","validate","structure"], default="structure")
    cli.add_argument("--output", default="output")
    args = cli.parse_args()

    if args.mode == "structure":
        result = ensure_output_structure(args.output)
        print(json.dumps(result, indent=2))
    elif args.mode == "validate":
        # Elenca file nella cartella output e valida
        out = Path(args.output)
        all_files = [str(f) for f in out.rglob("*") if f.is_file()]
        result = validate_export(all_files)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Modalita '{args.mode}' richiede dati report da pipeline. Usa workflow_engine.py.")
        sys.exit(1)
