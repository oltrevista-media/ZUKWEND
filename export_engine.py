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
from typing import Optional, Union, List
from i18n_catalog import get_aging_bucket, format_human_date

try:
    from normalizer import normalize_currency_iso
except ImportError:
    def normalize_currency_iso(c: str) -> str:
        s = str(c or "").strip()
        m = {"€": "EUR", "$": "USD", "£": "GBP", "¥": "JPY", "R$": "BRL"}
        return m.get(s, s.upper() or "EUR")

try:
    from classifier import slugify_folder_name, group_invoices_by_client
except ImportError:
    def slugify_folder_name(name: str, max_length: int = 40) -> str:
        clean = re.sub(r'[/\\:*?"<>|&]+', '_', str(name or "UNKNOWN"))
        return re.sub(r'[\s_]+', '_', clean).strip('._ ')[:max_length]

    def group_invoices_by_client(invoices: list) -> dict:
        groups = {}
        for inv_item in invoices:
            if isinstance(inv_item, dict) and "invoice" in inv_item:
                inv = inv_item["invoice"]
            elif isinstance(inv_item, dict) and "data" in inv_item and isinstance(inv_item["data"], dict):
                inv = inv_item["data"].get("invoice", {})
            elif isinstance(inv_item, dict):
                inv = inv_item
            else:
                inv = {}

            c_vat = (inv.get("client_vat") or inv.get("vat_number") or "").strip()
            c_name = (inv.get("client") or inv.get("client_name") or "CLIENT").strip()
            inv_num = (inv.get("number") or inv.get("invoice_number") or "INV").strip()

            has_valid_vat = bool(c_vat and c_vat.upper() not in ("N/A", "NONE", "") and sum(c.isdigit() for c in c_vat) >= 5)

            if has_valid_vat:
                key = f"VAT_{c_vat.upper()}"
                folder_slug = slugify_folder_name(f"{c_name}_{c_vat}", 40)
            else:
                key = f"ISOLATED_{slugify_folder_name(c_name, 22)}_{slugify_folder_name(inv_num, 17)}"
                folder_slug = f"{slugify_folder_name(c_name, 22)}_{slugify_folder_name(inv_num, 17)}"

            if key not in groups:
                groups[key] = {
                    "client_name": c_name,
                    "vat": c_vat if has_valid_vat else None,
                    "folder_slug": folder_slug,
                    "invoices": []
                }
            groups[key]["invoices"].append(inv_item)
        return groups

try:
    from report_generator import generate_consolidated_statement_pdf, generate_consolidated_reminder_email
except ImportError:
    generate_consolidated_statement_pdf = None
    generate_consolidated_reminder_email = None

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

def _load_export_config() -> dict:
    """Carica le impostazioni di configurazione dossier_mode e generate_individual_archive."""
    cfg = {"dossier_mode": True, "generate_individual_archive": True}
    try:
        from resource_utils import get_user_data_dir
        for p in [Path("zukwend_config.json"), get_user_data_dir() / "zukwend_config.json"]:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    if isinstance(c, dict):
                        cfg.update(c)
    except Exception as e:
        logger.debug(f"Config load: {e}")
    return cfg


def _generate_master_excel(reports_or_invoices: list, dest_path: Path) -> Path:
    """
    Genera MASTER_SUMMARY_AGING_YYYYMMDD.xlsx contenente:
    - Foglio 1: "AR Aging Analysis"
    - Foglio 2: "ERP_Ingestion" con date ISO YYYY-MM-DD rigorose
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "AR Aging Analysis"
    ws.views.sheetView[0].showGridLines = True

    brand_fill = PatternFill(start_color="FF6B00", end_color="FF6B00", fill_type="solid")
    dark_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    gray_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    subtotal_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_normal = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    # 1. Header Banner
    ws.merge_cells("A1:L1")
    tcell = ws["A1"]
    tcell.value = "ZUKWEND — Master Accounts Receivable Aging Summary"
    tcell.font = font_title
    tcell.fill = brand_fill
    tcell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # 2. Table Headers
    headers = [
        "INVOICE #", "CLIENT NAME", "CLIENT VAT / TAX ID", "ISSUE DATE", "DUE DATE",
        "DAYS OVERDUE", "AGING BUCKET", "STATUS", "RISK LEVEL", "REMINDER LEVEL",
        "AMOUNT", "CURRENCY"
    ]
    for c_idx, h_text in enumerate(headers, start=1):
        c = ws.cell(row=3, column=c_idx, value=h_text)
        c.font = font_header
        c.fill = dark_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border
    ws.row_dimensions[3].height = 24

    records = []
    for item in reports_or_invoices:
        rdata = None
        if isinstance(item, dict) and "data" in item:
            rdata = item["data"]
        elif isinstance(item, dict) and "invoice" in item:
            rdata = item
        elif isinstance(item, dict) and ("paths" in item or "json" in item.get("paths", {})):
            jpath = item.get("paths", {}).get("json")
            if jpath and Path(jpath).exists():
                try:
                    with open(jpath, "r", encoding="utf-8") as f:
                        rdata = json.load(f)
                except Exception:
                    pass
        elif isinstance(item, dict):
            rdata = item

        if not rdata:
            continue

        inv = rdata.get("invoice", {})
        clf = rdata.get("classification", {})
        bill = rdata.get("billing", {})
        audit = rdata.get("audit", {})

        amt = float(inv.get("amount") or 0.0)
        curr = normalize_currency_iso(inv.get("currency") or "EUR")
        days_od = int(clf.get("days_overdue") or 0)
        bucket = clf.get("aging_bucket") or get_aging_bucket(days_od)
        lang = str(rdata.get("language") or "en").lower()[:2]

        iss_raw = str(inv.get("issue_date_iso") or inv.get("issue_date") or "N/A")
        due_raw = str(inv.get("due_date_iso") or inv.get("due_date") or "N/A")
        iss_human = format_human_date(inv.get("issue_date") or iss_raw, lang) if iss_raw != "N/A" else "N/A"
        due_human = format_human_date(inv.get("due_date") or due_raw, lang) if due_raw != "N/A" else "N/A"

        records.append({
            "number": str(inv.get("number") or inv.get("invoice_number") or "N/A"),
            "client": str(inv.get("client") or inv.get("client_name") or "Client"),
            "client_address": str(inv.get("client_address") or inv.get("address") or ""),
            "client_vat": str(inv.get("client_vat") or inv.get("vat_number") or "N/A"),
            "issue_date_human": iss_human,
            "due_date_human": due_human,
            "issue_date_iso": iss_raw,
            "due_date_iso": due_raw,
            "days_overdue": days_od,
            "aging_bucket": bucket,
            "status": str(clf.get("payment_status") or clf.get("payment_status_raw") or "OVERDUE"),
            "risk": str(clf.get("risk_level_label") or clf.get("risk_level_raw") or "MEDIUM"),
            "rem_level": int(clf.get("reminder_level") or 0),
            "amount": amt,
            "currency": curr,
            "action": str(bill.get("action") or "SEND_REMINDER"),
            "processed_at": str(audit.get("processed_at") or datetime.now().strftime("%Y-%m-%d %H:%M")),
        })

    subtotals_by_curr = {}
    current_row = 4
    for rec in records:
        c = rec["currency"]
        subtotals_by_curr[c] = round(subtotals_by_curr.get(c, 0.0) + rec["amount"], 2)

        row_vals = [
            rec["number"], rec["client"], rec["client_vat"], rec["issue_date_human"], rec["due_date_human"],
            rec["days_overdue"], rec["aging_bucket"], rec["status"], rec["risk"], rec["rem_level"],
            rec["amount"], rec["currency"]
        ]
        for c_idx, val in enumerate(row_vals, start=1):
            cell = ws.cell(row=current_row, column=c_idx, value=val)
            cell.font = font_normal
            cell.border = thin_border
            if c_idx == 11:
                cell.number_format = "#,##0.00"
                cell.alignment = Alignment(horizontal="right")
            elif c_idx in (4, 5, 6, 10, 12):
                cell.alignment = Alignment(horizontal="center")
        current_row += 1

    # Righe subtotali separati per valuta (MAI sommare algebricamente valute diverse)
    for curr, tot in subtotals_by_curr.items():
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=10)
        lbl_cell = ws.cell(row=current_row, column=1, value=f"Total Overdue ({curr}):")
        lbl_cell.font = font_bold
        lbl_cell.alignment = Alignment(horizontal="right")
        lbl_cell.fill = subtotal_fill

        amt_cell = ws.cell(row=current_row, column=11, value=tot)
        amt_cell.font = font_bold
        amt_cell.number_format = "#,##0.00"
        amt_cell.fill = subtotal_fill
        amt_cell.border = thin_border

        curr_cell = ws.cell(row=current_row, column=12, value=curr)
        curr_cell.font = font_bold
        curr_cell.alignment = Alignment(horizontal="center")
        curr_cell.fill = subtotal_fill
        curr_cell.border = thin_border
        current_row += 1

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # 3. Sheet 2: "ERP_Ingestion" (Strict ISO Dates)
    ws_erp = wb.create_sheet(title="ERP_Ingestion")
    ws_erp.views.sheetView[0].showGridLines = True
    erp_headers = [
        "INVOICE_ID", "CLIENT_NAME", "CLIENT_ADDRESS", "CLIENT_VAT", "ISSUE_DATE",
        "DUE_DATE", "CURRENCY", "AMOUNT", "PAYMENT_STATUS", "DAYS_OVERDUE",
        "AGING_BUCKET", "RISK_LEVEL", "REMINDER_LEVEL", "RECOMMENDED_ACTION", "EXPORT_TIMESTAMP"
    ]
    for c_idx, h_text in enumerate(erp_headers, start=1):
        c = ws_erp.cell(row=1, column=c_idx, value=h_text)
        c.font = font_header
        c.fill = dark_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border
    ws_erp.row_dimensions[1].height = 24

    for r_idx, rec in enumerate(records, start=2):
        row_vals = [
            rec["number"], rec["client"], rec["client_address"], rec["client_vat"],
            rec["issue_date_iso"], rec["due_date_iso"], rec["currency"], rec["amount"],
            rec["status"], rec["days_overdue"], rec["aging_bucket"], rec["risk"],
            rec["rem_level"], rec["action"], rec["processed_at"]
        ]
        for c_idx, val in enumerate(row_vals, start=1):
            cell = ws_erp.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_normal
            cell.border = thin_border
            if c_idx == 8:
                cell.number_format = "#,##0.00"

    for col in ws_erp.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws_erp.column_dimensions[col_letter].width = max(max_len + 3, 12)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    target = dest_path
    try:
        wb.save(target)
    except (PermissionError, OSError) as e:
        if _is_lock_error(e):
            target = _get_unique_fallback_path(dest_path)
            logger.warning(f"[LOCK_RECOVERY] Master Excel locked ({e}). Saving to: {target.name}")
            wb.save(target)
        else:
            raise e
    logger.info(f"Master Excel generated: {target}")
    return target


def _generate_master_json(reports_or_invoices: list, dest_path: Path) -> Path:
    """Genera master_erp_ingestion_YYYYMMDD.json con payload unico di batch."""
    records = []
    subtotals = {}
    for item in reports_or_invoices:
        rdata = None
        if isinstance(item, dict) and "data" in item:
            rdata = item["data"]
        elif isinstance(item, dict) and "invoice" in item:
            rdata = item
        elif isinstance(item, dict) and ("paths" in item or "json" in item.get("paths", {})):
            jpath = item.get("paths", {}).get("json")
            if jpath and Path(jpath).exists():
                try:
                    with open(jpath, "r", encoding="utf-8") as f:
                        rdata = json.load(f)
                except Exception:
                    pass
        elif isinstance(item, dict):
            rdata = item

        if not rdata:
            continue

        inv = rdata.get("invoice", {})
        clf = rdata.get("classification", {})
        bill = rdata.get("billing", {})
        audit = rdata.get("audit", {})

        amt = float(inv.get("amount") or 0.0)
        curr = normalize_currency_iso(inv.get("currency") or "EUR")
        subtotals[curr] = round(subtotals.get(curr, 0.0) + amt, 2)

        records.append({
            "invoice_id": str(inv.get("number") or inv.get("invoice_number") or "N/A"),
            "client_name": str(inv.get("client") or inv.get("client_name") or "Client"),
            "client_address": str(inv.get("client_address") or inv.get("address") or ""),
            "client_vat": str(inv.get("client_vat") or inv.get("vat_number") or ""),
            "issue_date": str(inv.get("issue_date_iso") or inv.get("issue_date") or "N/A"),
            "due_date": str(inv.get("due_date_iso") or inv.get("due_date") or "N/A"),
            "currency": curr,
            "amount": amt,
            "payment_status": str(clf.get("payment_status") or clf.get("payment_status_raw") or "OVERDUE"),
            "days_overdue": int(clf.get("days_overdue") or 0),
            "aging_bucket": clf.get("aging_bucket") or get_aging_bucket(int(clf.get("days_overdue") or 0)),
            "risk_level": str(clf.get("risk_level_label") or clf.get("risk_level_raw") or "MEDIUM"),
            "reminder_level": int(clf.get("reminder_level") or 0),
            "recommended_action": str(bill.get("action") or "SEND_REMINDER"),
            "export_timestamp": str(audit.get("processed_at") or datetime.now().isoformat()),
        })

    payload = {
        "batch_generated_at": datetime.now().isoformat(),
        "software": "ZUKWEND",
        "version": "2.1.6",
        "total_invoices": len(records),
        "currencies": sorted(list(subtotals.keys())),
        "subtotals_by_currency": subtotals,
        "invoices": records,
    }

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    target = dest_path
    try:
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except (PermissionError, OSError) as e:
        if _is_lock_error(e):
            target = _get_unique_fallback_path(dest_path)
            logger.warning(f"[LOCK_RECOVERY] Master JSON locked ({e}). Saving to: {target.name}")
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            raise e
    logger.info(f"Master JSON generated: {target}")
    return target


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
    Supporta Dossier Mode (v2.1.6):
      - output/CLIENTS/{CLIENT_SLUG_VAT}/{YYYY-MM-DD}/
      - STATEMENT_OF_ACCOUNT_CONSOLIDATED.pdf
      - REMINDER_EMAIL_CONSOLIDATED.txt
      - Individual_Invoices_Archive/
      - MASTER_SUMMARY_AGING_YYYYMMDD.xlsx (root)
      - master_erp_ingestion_YYYYMMDD.json (root)
    """
    exported_paths = []
    errors = []

    if not report or not report.get("paths"):
        logger.warning("export(): no files to export (report or report.paths empty)")
        return []

    cfg = _load_export_config()
    dossier_mode = cfg.get("dossier_mode", True)
    individual_archive = cfg.get("generate_individual_archive", True)

    outputFolder = get_output_dir()
    out_root = Path(output_dir) if output_dir else Path(outputFolder)
    out_root.mkdir(parents=True, exist_ok=True)

    today_iso = datetime.now().strftime("%Y-%m-%d")
    today_compact = datetime.now().strftime("%Y%m%d")
    base_name = report.get("base_name", "report_unknown")
    source_paths = dict(report.get("paths", {}))

    if dossier_mode:
        # Recupera dati report
        rdata = report.get("data")
        if not rdata:
            jpath = report.get("paths", {}).get("json")
            if jpath and Path(jpath).exists():
                try:
                    with open(jpath, "r", encoding="utf-8") as f:
                        rdata = json.load(f)
                except Exception:
                    pass
        if not rdata:
            rdata = report

        # Raggruppamento Strict P.IVA
        groups = group_invoices_by_client([rdata])
        client_group = list(groups.values())[0]
        client_folder_slug = client_group["folder_slug"]

        client_root = out_root / "CLIENTS" / client_folder_slug
        session_dir = client_root / today_iso
        session_dir.mkdir(parents=True, exist_ok=True)

        if individual_archive:
            archive_dir = session_dir / "Individual_Invoices_Archive"
        else:
            archive_dir = session_dir
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Sposta singoli trittici in Individual_Invoices_Archive/
        for fmt, src_path in source_paths.items():
            if not src_path:
                continue
            src = Path(src_path)
            if not src.exists():
                continue
            dest = archive_dir / src.name
            if src.resolve() != dest.resolve():
                try:
                    shutil.copy2(str(src), str(dest))
                    try:
                        src.unlink()
                    except Exception:
                        pass
                except (PermissionError, OSError) as e:
                    if _is_lock_error(e):
                        alt_dest = _get_unique_fallback_path(dest)
                        try:
                            shutil.copy2(str(src), str(alt_dest))
                            dest = alt_dest
                            try:
                                src.unlink()
                            except Exception:
                                pass
                        except Exception as e2:
                            errors.append(f"copy_error_locked:{fmt}:{e2}")
                            dest = src
                    else:
                        errors.append(f"copy_error:{fmt}:{e}")
                        dest = src
            report.setdefault("paths", {})[fmt] = str(dest)
            exported_paths.append(str(dest))

        report["output_dir"] = str(session_dir)

        # Raccoglie tutte le fatture archiviate per questo cliente in data odierna
        client_session_invoices = []
        for jf in archive_dir.glob("*.json"):
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    inv_d = json.load(f)
                    if isinstance(inv_d, dict) and ("invoice" in inv_d or "number" in inv_d):
                        client_session_invoices.append(inv_d)
            except Exception:
                pass
        if not client_session_invoices:
            client_session_invoices = [rdata]

        # Genera STATEMENT_OF_ACCOUNT_CONSOLIDATED.pdf e REMINDER_EMAIL_CONSOLIDATED.txt
        lang = (report.get("language") or rdata.get("language") or "en")
        is_demo = bool(rdata.get("is_demo", False))

        if generate_consolidated_statement_pdf:
            stmt_pdf = session_dir / "STATEMENT_OF_ACCOUNT_CONSOLIDATED.pdf"
            try:
                generate_consolidated_statement_pdf(
                    client_group, client_session_invoices, stmt_pdf, language=lang, is_demo=is_demo
                )
                exported_paths.append(str(stmt_pdf))
                report["consolidated_statement_path"] = str(stmt_pdf)
            except Exception as e_pdf:
                logger.error(f"Error generating consolidated statement PDF: {e_pdf}")
                errors.append(f"consolidated_pdf_error:{e_pdf}")

        if generate_consolidated_reminder_email:
            rem_email = session_dir / "REMINDER_EMAIL_CONSOLIDATED.txt"
            try:
                generate_consolidated_reminder_email(
                    client_group, client_session_invoices, rem_email, language=lang
                )
                exported_paths.append(str(rem_email))
                report["consolidated_email_path"] = str(rem_email)
            except Exception as e_em:
                logger.error(f"Error generating consolidated reminder email: {e_em}")
                errors.append(f"consolidated_email_error:{e_em}")

        # Aggiorna Master Excel e Master JSON nella radice di output/
        master_excel_path = out_root / f"MASTER_SUMMARY_AGING_{today_compact}.xlsx"
        master_json_path = out_root / f"master_erp_ingestion_{today_compact}.json"

        all_day_invoices = []
        clients_base = out_root / "CLIENTS"
        if clients_base.exists():
            for c_dir in clients_base.glob("*"):
                day_s = c_dir / today_iso
                arch_s = day_s / "Individual_Invoices_Archive"
                search_dirs = [arch_s, day_s]
                for s_dir in search_dirs:
                    if s_dir.exists():
                        for jf in s_dir.glob("*.json"):
                            try:
                                with open(jf, "r", encoding="utf-8") as f:
                                    d_inv = json.load(f)
                                    if isinstance(d_inv, dict) and ("invoice" in d_inv or "number" in d_inv):
                                        all_day_invoices.append(d_inv)
                            except Exception:
                                pass
        if not all_day_invoices:
            all_day_invoices = [rdata]

        try:
            _generate_master_excel(all_day_invoices, master_excel_path)
            exported_paths.append(str(master_excel_path))
            report["master_excel_path"] = str(master_excel_path)
        except Exception as e_mx:
            logger.error(f"Error generating master excel: {e_mx}")
            errors.append(f"master_excel_error:{e_mx}")

        try:
            _generate_master_json(all_day_invoices, master_json_path)
            exported_paths.append(str(master_json_path))
            report["master_json_path"] = str(master_json_path)
        except Exception as e_mj:
            logger.error(f"Error generating master json: {e_mj}")
            errors.append(f"master_json_error:{e_mj}")

        _write_export_audit_log(session_dir, base_name, exported_paths, errors, report)
        logger.info(f"Dossier export completed: {len(exported_paths)} files | {session_dir}")
        return exported_paths

    else:
        # Modalità classica non dossier
        if organize_by_date:
            date_folder = out_root / today_iso
            date_folder.mkdir(parents=True, exist_ok=True)
            dest_dir = date_folder
        else:
            dest_dir = out_root

        for fmt, src_path in source_paths.items():
            if not src_path:
                continue
            src = Path(src_path)
            if not src.exists():
                logger.warning(f"Source file not found: {src}")
                errors.append(f"not_found:{src}")
                continue
            dest = dest_dir / src.name
            if src.resolve() != dest.resolve():
                try:
                    shutil.copy2(str(src), str(dest))
                    try:
                        src.unlink()
                    except Exception:
                        pass
                except (PermissionError, OSError) as e:
                    if _is_lock_error(e):
                        alt_dest = _get_unique_fallback_path(dest)
                        try:
                            shutil.copy2(str(src), str(alt_dest))
                            dest = alt_dest
                            try:
                                src.unlink()
                            except Exception:
                                pass
                        except Exception as e2:
                            errors.append(f"copy_error_locked:{fmt}:{e2}")
                            dest = src
                    else:
                        errors.append(f"copy_error:{fmt}:{e}")
                        dest = src
            report.setdefault("paths", {})[fmt] = str(dest)
            exported_paths.append(str(dest))

        report["output_dir"] = str(dest_dir)
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
    Supporta dossier_mode raggruppando per cliente con Strict P.IVA.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outputFolder = get_output_dir()
    out_root = Path(output_dir) if output_dir else Path(outputFolder)

    cfg = _load_export_config()
    dossier_mode = cfg.get("dossier_mode", True)

    all_paths = []
    all_errors = []
    batch_meta = []

    logger.info(f"Batch export: {len(reports)} report -> {out_root} (dossier_mode={dossier_mode})")

    for i, report in enumerate(reports):
        try:
            paths = export(report, output_dir=str(out_root), organize_by_date=True)
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
            aging_path = _generate_aging_summary(reports, out_root, timestamp)
            all_paths.append(str(aging_path))
        except Exception as e:
            logger.error(f"Aging summary errore: {e}")
            all_errors.append({"step": "aging_summary", "error": str(e)})

    log_path = out_root / f"batch_log_{timestamp}.txt"
    _write_batch_log(log_path, batch_meta, all_errors, timestamp)

    return {
        "all_paths":           all_paths,
        "batch_dir":           str(out_root),
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
