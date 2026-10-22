"""
ZUKWEND — Multilingual Billing Agent
Module: gui_launcher.py
Role: Professional Windows 11 Dark-Mode Interface with Real-Time Progress & Logs
Version: 1.0.3-ENTERPRISE
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import os
import sys
import json
import queue
import logging
import subprocess
import threading
import webbrowser
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

from license_manager import check_license, activate_license, increment_invoice_count, get_machine_id_short
from resource_utils import get_resource_path, get_user_data_dir, get_output_dir

# Explicit internal & PDF library imports for PyInstaller bundling
import workflow_engine
import parser
import normalizer
import classifier
import deducer
import report_generator
import export_engine
import pdfplumber
import PyPDF2
import pypdf

logger = logging.getLogger("zukwend.gui")

LEMON_CHECKOUT_URL = "https://oltrevista.lemonsqueezy.com/checkout/buy/191492c7-087e-4e04-8c78-2de2a1dcfda6"

# Configurazione: default di sola lettura nel bundle (sys._MEIPASS) + file utente scrivibile.
CONFIG_FILENAME = "zukwend_config.json"
DEFAULT_CONFIG = {"mode": "local", "api_key": "", "lang": "en"}
BUNDLED_CONFIG_FILE = Path(get_resource_path(CONFIG_FILENAME))

def _user_config_file() -> Path:
    return get_user_data_dir() / CONFIG_FILENAME

def load_user_config():
    cfg = dict(DEFAULT_CONFIG)
    for candidate in (BUNDLED_CONFIG_FILE, _user_config_file()):  # l'utente sovrascrive il default
        try:
            if candidate.exists():
                with open(candidate, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    cfg.update(loaded)
        except Exception as e:
            logger.warning(f"Config '{candidate}' not readable: {e}")
    return cfg

def save_user_config(cfg):
    try:
        with open(_user_config_file(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Config could not be saved: {e}")

def safe_check_license() -> dict:
    """safe check_license(): an I/O error on license must never crash GUI startup."""
    try:
        return check_license()
    except Exception as e:
        logger.error(f"License check failed: {e}")
        return {
            "license_type": "INVALID",
            "is_valid": False,
            "invoice_count": 0,
            "max_invoices": 10,
            "days_remaining": 0,
            "message": f"License check unavailable: {e}",
        }

def ensure_output_folder() -> str:
    path = get_output_dir()
    os.makedirs(path, exist_ok=True)
    return path

def launch_gui_launcher():
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    cfg = load_user_config()

    root = ctk.CTk()
    root.title("ZUKWEND Billing Agent")
    root.geometry("640x760")
    root.resizable(False, False)

    try:
        ensure_output_folder()
    except Exception as e:
        logger.error(f"Unable to create output folder: {e}")

    # Thread-safe UI queue
    ui_queue = queue.Queue()

    def post_ui(fn, *args):
        ui_queue.put((fn, args))

    def drain_ui_queue():
        try:
            while True:
                fn, args = ui_queue.get_nowait()
                try:
                    fn(*args)
                except Exception:
                    logger.exception("Error in UI callback")
        except queue.Empty:
            pass
        try:
            root.after(50, drain_ui_queue)
        except Exception:
            pass  # finestra chiusa

    def _tk_exception_hook(exc_type, exc_value, exc_tb):
        logger.error("Eccezione non gestita nella GUI", exc_info=(exc_type, exc_value, exc_tb))

    root.report_callback_exception = _tk_exception_hook
    root.after(50, drain_ui_queue)

    lbl_title = ctk.CTkLabel(
        root, 
        text="ZUKWEND Billing Agent", 
        font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
    )
    lbl_title.pack(pady=(14, 2))

    lbl_sub = ctk.CTkLabel(
        root, 
        text="Autonomous Document Deductive Engine — Privacy-First", 
        font=ctk.CTkFont(family="Segoe UI", size=12), 
        text_color="#9E9E9E"
    )
    lbl_sub.pack(pady=(0, 8))

    # --- License Header Status Bar ---
    frame_license_header = ctk.CTkFrame(root, fg_color="transparent")
    frame_license_header.pack(fill="x", padx=20, pady=(0, 10))

    badge_license = ctk.CTkLabel(
        frame_license_header,
        text="",
        font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        corner_radius=6,
        padx=10,
        pady=4
    )
    badge_license.pack(side="left")

    btn_activate_license = ctk.CTkButton(
        frame_license_header,
        text="🔑 Activate License",
        width=120,
        height=28,
        font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        fg_color="#D97706",
        hover_color="#B45309"
    )

    btn_buy_full = ctk.CTkButton(
        frame_license_header,
        text="🚀 Buy FULL",
        width=120,
        height=28,
        command=lambda: webbrowser.open(LEMON_CHECKOUT_URL),
        font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        fg_color="#2563EB",
        hover_color="#1D4ED8"
    )

    # State tracking
    current_lic_status = {"data": safe_check_license()}

    def refresh_license_ui():
        lic = safe_check_license()
        current_lic_status["data"] = lic
        lic_type = lic.get("license_type", "DEMO")
        inv_count = lic.get("invoice_count", 0)
        max_inv = lic.get("max_invoices", 10)
        days_rem = lic.get("days_remaining", 0)

        # Unpack elements
        btn_activate_license.pack_forget()
        btn_buy_full.pack_forget()

        if lic_type == "FULL":
            badge_license.configure(
                text="🟢 ZUKWEND FULL — License Active",
                text_color="#10B981",
                fg_color="#064E3B"
            )
            if "btn_run" in locals() or "btn_run" in globals():
                btn_run.configure(state="normal")
        elif lic_type == "EXPIRED":
            badge_license.configure(
                text=f"🔴 LICENSE EXPIRED ({inv_count}/{max_inv} invoices or 7 days)",
                text_color="#EF4444",
                fg_color="#450A0A"
            )
            btn_buy_full.pack(side="right", padx=(6, 0))
            btn_activate_license.pack(side="right")
            if "btn_run" in locals() or "btn_run" in globals():
                btn_run.configure(state="disabled")
        else:  # DEMO
            badge_license.configure(
                text=f"🟡 EVALUATION ({inv_count}/{max_inv} invoices | {days_rem} days remaining)",
                text_color="#F59E0B",
                fg_color="#451A03"
            )
            btn_buy_full.pack(side="right", padx=(6, 0))
            btn_activate_license.pack(side="right")
            if "btn_run" in locals() or "btn_run" in globals():
                btn_run.configure(state="normal")

    def open_activation_dialog():
        dialog = ctk.CTkToplevel(root)
        dialog.title("Activate ZUKWEND FULL License")
        dialog.geometry("520x330")
        dialog.resizable(False, False)
        dialog.transient(root)
        dialog.grab_set()

        lbl_modal_title = ctk.CTkLabel(
            dialog,
            text="Activate your ZUKWEND FULL License",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        )
        lbl_modal_title.pack(pady=(20, 4))

        lbl_modal_sub = ctk.CTkLabel(
            dialog,
            text=f"Enter the License Key received after purchasing on Lemon Squeezy.\nAssociated Machine ID: {get_machine_id_short()}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#9CA3AF",
            justify="center"
        )
        lbl_modal_sub.pack(pady=(0, 16))

        entry_license_key = ctk.CTkEntry(
            dialog,
            placeholder_text="Paste your License Key here...",
            width=440,
            height=38,
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        entry_license_key.pack(pady=(0, 12))

        lbl_act_msg = ctk.CTkLabel(
            dialog,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#F59E0B"
        )
        lbl_act_msg.pack(pady=(0, 10))

        def execute_activation():
            key = entry_license_key.get().strip()
            if not key:
                lbl_act_msg.configure(text="Please enter a valid license key.", text_color="#EF4444")
                return

            btn_verify.configure(state="disabled", text="Verifying...")
            lbl_act_msg.configure(text="Validating license (online Lemon Squeezy / offline HWID)...", text_color="#F59E0B")

            def finish_activation(res: dict):
                try:
                    if res.get("success", False):
                        lbl_act_msg.configure(text="License activated successfully! Restarting interface...", text_color="#10B981")
                        refresh_license_ui()
                        messagebox.showinfo("License Activated", res.get("message", "ZUKWEND FULL successfully activated!"))
                        dialog.destroy()
                    else:
                        btn_verify.configure(state="normal", text="Verify & Activate")
                        lbl_act_msg.configure(text=res.get("message", "Invalid license key."), text_color="#EF4444")
                except Exception:
                    logger.exception("Error completing license activation")

            def activation_worker():
                try:
                    res = activate_license(key)
                except Exception as e:
                    logger.exception("License activation error")
                    res = {"success": False, "message": f"Activation error: {e}"}
                post_ui(finish_activation, res)

            threading.Thread(target=activation_worker, daemon=True).start()

        btn_verify = ctk.CTkButton(
            dialog,
            text="Verify & Activate",
            command=execute_activation,
            width=200,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#059669",
            hover_color="#047857"
        )
        btn_verify.pack(pady=(0, 8))

        btn_checkout = ctk.CTkButton(
            dialog,
            text="Don't have a license yet? Buy FULL — 249 €",
            command=lambda: webbrowser.open(LEMON_CHECKOUT_URL),
            font=ctk.CTkFont(family="Segoe UI", size=11, underline=True),
            fg_color="transparent",
            hover_color="#1F2937",
            text_color="#60A5FA"
        )
        btn_checkout.pack()

    btn_activate_license.configure(command=open_activation_dialog)

    # Startup DEMO/EXPIRED Modal
    def check_startup_license_modal():
        lic = current_lic_status["data"]
        lic_type = lic.get("license_type", "DEMO")
        if lic_type == "EXPIRED":
            messagebox.showwarning(
                "ZUKWEND License Expired",
                f"The evaluation period has ended ({lic.get('invoice_count', 10)}/{lic.get('max_invoices', 10)} invoices or 7-day period completed).\n\n"
                f"To continue analyzing documents without limits, purchase a FULL license or enter an active key."
            )
        elif lic_type == "DEMO":
            inv_rem = lic.get("invoices_remaining", 10)
            days_rem = lic.get("days_remaining", 7)
            inv_cnt = lic.get("invoice_count", 0)
            print(f"[ZUKWEND] Starting in evaluation mode ({inv_cnt}/10 invoices processed, {days_rem} days remaining)")

    frame_main = ctk.CTkFrame(root, corner_radius=12)
    frame_main.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    # Document Selection
    lbl_pdf = ctk.CTkLabel(
        frame_main, 
        text="TARGET INVOICE DOCUMENT (PDF)", 
        font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), 
        text_color="#D1D5DB"
    )
    lbl_pdf.pack(anchor="w", padx=20, pady=(12, 4))

    frame_file = ctk.CTkFrame(frame_main, fg_color="transparent")
    frame_file.pack(fill="x", padx=20, pady=(0, 10))

    pdf_var = ctk.StringVar(value="")
    entry_pdf = ctk.CTkEntry(
        frame_file, 
        textvariable=pdf_var, 
        placeholder_text="Select invoice PDF file...", 
        font=ctk.CTkFont(family="Segoe UI", size=12)
    )
    entry_pdf.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def sfoglia():
        path = filedialog.askopenfilename(
            title="Select Invoice PDF", 
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")]
        )
        if path:
            pdf_var.set(path)

    btn_sfoglia = ctk.CTkButton(
        frame_file, 
        text="Browse...", 
        command=sfoglia, 
        width=85, 
        font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
    )
    btn_sfoglia.pack(side="right")

    # Engine Selection
    lbl_engine = ctk.CTkLabel(
        frame_main, 
        text="PROCESSING ENGINE", 
        font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), 
        text_color="#D1D5DB"
    )
    lbl_engine.pack(anchor="w", padx=20, pady=(4, 6))

    mode_var = ctk.StringVar(value=cfg.get("mode", "local"))

    rb_local = ctk.CTkRadioButton(
        frame_main, 
        text="On-Premise Local AI (High Privacy & Zero-Config)", 
        variable=mode_var, 
        value="local", 
        font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
    )
    rb_local.pack(anchor="w", padx=20, pady=(2, 2))

    lbl_local_desc = ctk.CTkLabel(
        frame_main, 
        text="Self-contained execution on local hardware. Zero external data transmission.\nIncludes resilient fallback engine for instant, uninterrupted operations.", 
        font=ctk.CTkFont(family="Segoe UI", size=10), 
        text_color="#9CA3AF", 
        justify="left"
    )
    lbl_local_desc.pack(anchor="w", padx=45, pady=(0, 8))

    rb_cloud = ctk.CTkRadioButton(
        frame_main, 
        text="High-Precision Cloud AI (BYOC)", 
        variable=mode_var, 
        value="cloud", 
        font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
    )
    rb_cloud.pack(anchor="w", padx=20, pady=(2, 2))

    lbl_cloud_desc = ctk.CTkLabel(
        frame_main, 
        text="Frontier reasoning for complex document layouts with your API provider.\nSupports OpenAI, Google Gemini, Groq, Anthropic, Mistral AI (EU/GDPR compliant).", 
        font=ctk.CTkFont(family="Segoe UI", size=10), 
        text_color="#9CA3AF", 
        justify="left"
    )
    lbl_cloud_desc.pack(anchor="w", padx=45, pady=(0, 6))

    api_key_var = ctk.StringVar(value=cfg.get("api_key", ""))
    entry_key = ctk.CTkEntry(
        frame_main, 
        textvariable=api_key_var, 
        placeholder_text="Enter your API Key...", 
        font=ctk.CTkFont(family="Segoe UI", size=12), 
        show="*"
    )
    entry_key.pack(fill="x", padx=45, pady=(0, 10))

    def on_mode_change(*args):
        if mode_var.get() == "cloud":
            entry_key.configure(state="normal")
        else:
            entry_key.configure(state="disabled")

    mode_var.trace_add("write", on_mode_change)
    on_mode_change()

    # Document Language Selection (6 Languages)
    frame_lang = ctk.CTkFrame(frame_main, fg_color="transparent")
    frame_lang.pack(fill="x", padx=20, pady=(0, 10))

    lbl_lang = ctk.CTkLabel(
        frame_lang, 
        text="DOCUMENT & NOTICE LANGUAGE:", 
        font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), 
        text_color="#D1D5DB"
    )
    lbl_lang.pack(side="left", padx=(0, 12))

    lang_map = {
        "EN": "en",
        "DE": "de",
        "IT": "it",
        "FR": "fr",
        "ES": "es",
        "PT": "pt",
    }
    inv_lang_map = {v: k for k, v in lang_map.items()}

    current_lang_label = inv_lang_map.get(cfg.get("lang", "en"), "EN")

    def on_lang_change(selected_label: str):
        selected_code = lang_map.get(selected_label, "en")
        cfg["lang"] = selected_code
        save_user_config(cfg)

    combo_lang = ctk.CTkComboBox(
        frame_lang, 
        values=list(lang_map.keys()), 
        command=on_lang_change,
        state="readonly", 
        width=120, 
        font=ctk.CTkFont(family="Segoe UI", size=12)
    )
    combo_lang.set(current_lang_label)
    combo_lang.pack(side="left")

    # Progress & Feedback Area
    progress_bar = ctk.CTkProgressBar(frame_main)
    progress_bar.pack(fill="x", padx=20, pady=(8, 4))
    progress_bar.set(0)

    log_box = ctk.CTkTextbox(
        frame_main, 
        height=100, 
        font=ctk.CTkFont(family="Consolas", size=11), 
        text_color="#A7F3D0"
    )
    log_box.pack(fill="both", expand=True, padx=20, pady=(0, 10))
    log_box.insert("end", "[READY] Awaiting document analysis...\n")
    log_box.configure(state="disabled")

    output_dir_ref = {"path": None}
    progress_default_color = progress_bar.cget("progress_color")

    def append_log(message: str):
        log_box.configure(state="normal")
        log_box.insert("end", message + "\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    def on_pipeline_end_ok():
        """PIPELINE_END OK: refresh forzato della GUI e focus visivo sull'avvenuto completamento."""
        try:
            progress_bar.set(1.0)
            progress_bar.configure(progress_color="#10B981")
            btn_open_folder.configure(state="normal", text="OPEN OUTPUT FOLDER  (REPORT READY)")
            root.update_idletasks()
            root.deiconify()
            root.lift()
            root.attributes("-topmost", True)
            root.after(400, lambda: root.attributes("-topmost", False))
            root.focus_force()
            btn_open_folder.focus_set()
            root.update_idletasks()
        except Exception:
            logger.exception("Refresh GUI post-pipeline non riuscito")

    def update_progress(step: str, status: str, detail: str):
        step_weights = {
            "PIPELINE_START": 0.05,
            "LICENSE": 0.10,
            "LOAD": 0.20,
            "PARSE": 0.40,
            "NORMALIZE": 0.55,
            "CLASSIFY": 0.70,
            "COMPLIANCE": 0.80,
            "BILLING": 0.85,
            "REMINDER": 0.90,
            "REPORT": 0.95,
            "EXPORT": 1.0,
            "PIPELINE_END": 1.0,
        }
        val = step_weights.get(step, None)
        if val is not None:
            progress_bar.set(val)
        
        # Clean any raw list notation in detail
        if "=[" in detail or "=['" in detail:
            detail = re.sub(r'=[\'"]?\[[\'"]?([^\'"\]]+)[\'"]?\]', r'=\1', detail)
        
        append_log(f"[{step}] {status}: {detail}")

        if step == "PIPELINE_END" and status == "OK":
            on_pipeline_end_ok()

    frame_actions = ctk.CTkFrame(frame_main, fg_color="transparent")
    frame_actions.pack(fill="x", padx=20, pady=(0, 12))

    def open_output_folder():
        """
        Apre la cartella output nell'Esplora risorse.
        os.startfile e' non bloccante (ShellExecute): il main thread non si ferma;
        qualsiasi errore e' intercettato e non puo' mai far crashare la GUI.
        """
        target = os.path.abspath("output")
        try:
            target = ensure_output_folder()
            os.startfile(target)
        except Exception as e:
            logger.error(f"Output folder open failed ({target}): {e}")
            append_log(f"[WARN] Unable to open output folder: {e}")
            try:
                subprocess.Popen(["explorer", target])
            except Exception as e2:
                logger.error(f"Fallback explorer failed: {e2}")
                messagebox.showwarning("Output Folder", f"Unable to open folder:\n{target}\n\n{e2}")

    btn_open_folder = ctk.CTkButton(
        frame_actions,
        text="OPEN OUTPUT FOLDER",
        command=open_output_folder,
        state="normal",
        height=38,
        corner_radius=8,
        font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        fg_color="#059669",
        hover_color="#047857"
    )

    def restore_run_button():
        refresh_license_ui()
        btn_run.configure(text="RUN DOCUMENT ANALYSIS")
        # Re-evaluate btn_run disabled if expired
        if current_lic_status["data"].get("license_type") == "EXPIRED":
            btn_run.configure(state="disabled")
        else:
            btn_run.configure(state="normal")

    def worker_thread(pdf_path, selected_mode, selected_key, selected_lang):
        # NB: questo thread NON deve toccare widget Tk: ogni aggiornamento passa da post_ui().
        try:
            from workflow_engine import run_pipeline

            post_ui(append_log, f"[INFO] Initializing engine in {selected_mode.upper()} mode...")
            
            # Check current license status
            lic = safe_check_license()
            is_demo = (lic.get("license_type") != "FULL")

            result = run_pipeline(
                pdf_path=pdf_path,
                language=selected_lang,
                mode=selected_mode,
                api_key=selected_key if selected_mode == "cloud" else None,
                is_demo=is_demo,
                progress_callback=lambda s, st, d: post_ui(update_progress, s, st, d)
            )

            # Increment invoice count if in DEMO mode
            if is_demo and result.success:
                new_cnt = increment_invoice_count()
                post_ui(append_log, f"[LICENSE] Evaluation invoice processed ({new_cnt}/10)")

            save_user_config({
                "mode": selected_mode, 
                "api_key": selected_key, 
                "lang": selected_lang
            })

            if result.report_path:
                out_dir = str(Path(result.report_path).parent)
            elif result.export_paths:
                out_dir = str(Path(result.export_paths[0]).parent)
            else:
                out_dir = os.path.abspath("output")

            output_dir_ref["path"] = out_dir

            def on_complete():
                restore_run_button()
                if not result.invoice:
                    # Pipeline interrotta prima dell'analisi (es. licenza non valida, PDF illeggibile)
                    details = "; ".join(str(e.get("error", "")) for e in result.errors) or "unknown error"
                    append_log(f"[ERROR] Pipeline interrupted: {details}")
                    messagebox.showwarning("Processing Incomplete", f"The document could not be processed:\n\n{details}")
                    return
                headline = (
                    "Document processed successfully!" if result.success
                    else f"Document processed with {len(result.errors)} warning(s) - see log for details."
                )
                messagebox.showinfo(
                    "Processing Complete", 
                    f"{headline}\n\nInvoice: {result.invoice.get('invoice_number', 'N/A')}\nAmount: {result.invoice.get('amount', 0.0)} {result.invoice.get('currency', 'EUR')}\nAction: {result.billing.get('action', 'N/A')}"
                )

            post_ui(on_complete)

        except Exception as e:
            logger.exception("Fatal error in worker thread")

            def on_error(err=e):
                restore_run_button()
                append_log(f"[ERROR] Fatal exception: {err}")
                messagebox.showerror("Execution Error", f"Failed to complete workflow:\n{err}")

            post_ui(on_error)

    def avvia():
        lic = safe_check_license()
        if not lic.get("is_valid", False):
            refresh_license_ui()
            messagebox.showwarning(
                "License Expired or Invalid",
                f"The evaluation period has ended ({lic.get('invoice_count', 10)}/{lic.get('max_invoices', 10)} invoices processed).\n"
                f"To continue, activate a FULL license or purchase it on ZUKWEND.com."
            )
            return

        pdf_path = pdf_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Missing Document", "Please select a valid PDF invoice document.")
            return

        selected_mode = mode_var.get()
        selected_key = api_key_var.get().strip()
        selected_lang = lang_map.get(combo_lang.get(), "en")

        if selected_mode == "cloud" and not selected_key:
            messagebox.showwarning("Missing API Key", "Cloud AI mode selected: please provide your API Key.")
            return

        btn_run.configure(state="disabled", text="PROCESSING INVOICE...")
        btn_open_folder.configure(text="OPEN OUTPUT FOLDER")  # resta sempre abilitato
        progress_bar.configure(progress_color=progress_default_color)
        progress_bar.set(0)

        log_box.configure(state="normal")
        log_box.delete("1.0", "end")
        log_box.configure(state="disabled")

        t = threading.Thread(
            target=worker_thread, 
            args=(pdf_path, selected_mode, selected_key, selected_lang),
            daemon=True
        )
        t.start()

    btn_run = ctk.CTkButton(
        frame_actions, 
        text="RUN DOCUMENT ANALYSIS", 
        command=avvia, 
        height=42, 
        corner_radius=8, 
        font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), 
        fg_color="#2563EB", 
        hover_color="#1D4ED8"
    )
    btn_run.pack(fill="x")
    # "Apri cartella output" ABILITATO e visibile fin dall'avvio (state='normal')
    btn_open_folder.pack(fill="x", pady=(6, 0))

    # Initial UI refresh and startup check
    refresh_license_ui()
    root.after(100, check_startup_license_modal)

    root.mainloop()

if __name__ == "__main__":
    launch_gui_launcher()