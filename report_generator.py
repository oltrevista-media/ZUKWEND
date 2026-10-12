"""
ZUKWEND — Multilingual Billing Agent
Modulo: report_generator.py
Ruolo: Generazione report AR in formato PDF, DOCX, JSON, HTML
Versione: 2.1.0-ENTERPRISE (Full 6-Language Native Edition)
REPTANA MODE | OLTREVISTA 2030 | Offline-First
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("zukwend.report_generator")

# ---------------------------------------------------------------------------
# Import librerie opzionali con fallback
# ---------------------------------------------------------------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.platypus.flowables import KeepTogether
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab non disponibile — PDF limitato a testo")

try:
    from docx import Document as DocxDocument
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx non disponibile — DOCX disabilitato")

try:
    from jinja2 import Template as Jinja2Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    logger.info("jinja2 non disponibile — HTML usa template inline")

# ---------------------------------------------------------------------------
# Costanti e Dizionari Multilingua Completi (6 Lingue)
# ---------------------------------------------------------------------------
BRAND_COLOR_HEX = "#FF6B00"   # Arancione OLTREVISTA
TEXT_COLOR      = "#1A1A1A"
LIGHT_GRAY      = "#F5F5F5"
MEDIUM_GRAY     = "#CCCCCC"

DISCLAIMER_TEXT = {
    "it": "Il software fornisce suggerimenti, non decisioni. Output da verificare prima dell'uso operativo. Nessun dato inviato a server esterni.",
    "en": "This software provides suggestions, not decisions. Output must be verified before operational use. No data sent to external servers.",
    "fr": "Ce logiciel fournit des suggestions, pas des décisions. La sortie doit être vérifiée avant utilisation opérationnelle. Aucune donnée envoyée à des serveurs externes.",
    "de": "Diese Software liefert Vorschläge, keine Entscheidungen. Die Ausgabe muss vor dem operativen Einsatz geprüft werden. Keine Daten an externe Server gesendet.",
    "es": "Este software proporciona sugerencias, no decisiones. La salida debe verificarse antes del uso operativo. Ningún dato enviado a servidores externos.",
    "pt": "Este software fornece sugestões, não decisões. A saída deve ser verificada antes do uso operacional. Nenhum dado enviado a servidores externos.",
}

RISK_LABELS = {
    "it": {"LOW": "BASSO", "MEDIUM": "MEDIO", "HIGH": "ALTO", "NONE": "NESSUNO", "UNKNOWN": "N/D"},
    "en": {"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH", "NONE": "NONE", "UNKNOWN": "N/A"},
    "fr": {"LOW": "FAIBLE", "MEDIUM": "MOYEN", "HIGH": "ÉLEVÉ", "NONE": "AUCUN", "UNKNOWN": "N/D"},
    "de": {"LOW": "NIEDRIG", "MEDIUM": "MITTEL", "HIGH": "HOCH", "NONE": "KEIN", "UNKNOWN": "N/B"},
    "es": {"LOW": "BAJO", "MEDIUM": "MEDIO", "HIGH": "ALTO", "NONE": "NINGUNO", "UNKNOWN": "N/D"},
    "pt": {"LOW": "BAIXO", "MEDIUM": "MÉDIO", "HIGH": "ALTO", "NONE": "NENHUM", "UNKNOWN": "N/D"},
}

REPORT_LABELS = {
    "it": {
        "title": "Dati Fattura",
        "inv_num": "Numero Fattura",
        "issue_date": "Data Emissione",
        "due_date": "Data Scadenza",
        "amount": "Importo",
        "client": "Cliente",
        "status": "Stato",
        "overdue": "Giorni Scaduta",
        "risk": "Livello Rischio",
        "reminder_lvl": "Livello Sollecito",
        "rem_title": "Sollecito Generato",
        "recs_title": "Raccomandazioni",
        "audit_title": "Riepilogo Elaborazione",
        "no_anomalies": "Nessuna anomalia rilevata.",
        "processed": "Elaborato",
        "offline_tag": "Dati inviati esternamente: NO | Offline-First",
        "demo_banner": "⚠ VERSIONE DEMO — Non destinata all'uso operativo"
    },
    "en": {
        "title": "Invoice Details",
        "inv_num": "Invoice Number",
        "issue_date": "Issue Date",
        "due_date": "Due Date",
        "amount": "Amount",
        "client": "Client",
        "status": "Status",
        "overdue": "Days Overdue",
        "risk": "Risk Level",
        "reminder_lvl": "Notice Level",
        "rem_title": "Generated Collection Notice",
        "recs_title": "Recommendations",
        "audit_title": "Processing Audit",
        "no_anomalies": "No anomalies detected.",
        "processed": "Processed",
        "offline_tag": "Data sent externally: NO | Offline-First",
        "demo_banner": "⚠ DEMO VERSION — Not intended for operational use"
    },
    "de": {
        "title": "Rechnungsdaten",
        "inv_num": "Rechnungsnummer",
        "issue_date": "Rechnungsdatum",
        "due_date": "Fälligkeitsdatum",
        "amount": "Betrag",
        "client": "Kunde",
        "status": "Status",
        "overdue": "Tage überfällig",
        "risk": "Risikostufe",
        "reminder_lvl": "Mahnstufe",
        "rem_title": "Erstelltes Mahnschreiben",
        "recs_title": "Empfehlungen",
        "audit_title": "Verarbeitungsprotokoll",
        "no_anomalies": "Keine Unregelmäßigkeiten festgestellt.",
        "processed": "Verarbeitet",
        "offline_tag": "Daten extern gesendet: NEIN | Offline-First",
        "demo_banner": "⚠ DEMO-VERSION — Nicht für den produktiven Einsatz bestimmt"
    },
    "fr": {
        "title": "Détails Facture",
        "inv_num": "Numéro Facture",
        "issue_date": "Date Émission",
        "due_date": "Date Échéance",
        "amount": "Montant",
        "client": "Client",
        "status": "Statut",
        "overdue": "Jours de Retard",
        "risk": "Niveau de Risque",
        "reminder_lvl": "Niveau de Relance",
        "rem_title": "Relance Générée",
        "recs_title": "Recommandations",
        "audit_title": "Journal de Traitement",
        "no_anomalies": "Aucune anomalie détectée.",
        "processed": "Traité le",
        "offline_tag": "Données envoyées à l'extérieur: NON | Offline-First",
        "demo_banner": "⚠ VERSION DÉMO — Non destinée à un usage opérationnel"
    },
    "es": {
        "title": "Datos de la Factura",
        "inv_num": "Número de Factura",
        "issue_date": "Fecha de Emisión",
        "due_date": "Fecha de Vencimiento",
        "amount": "Importe",
        "client": "Cliente",
        "status": "Estado",
        "overdue": "Días Vencida",
        "risk": "Nivel de Riesgo",
        "reminder_lvl": "Nivel de Reclamación",
        "rem_title": "Aviso de Pago Generado",
        "recs_title": "Recomendaciones",
        "audit_title": "Registro de Procesamiento",
        "no_anomalies": "No se detectaron anomalías.",
        "processed": "Procesado",
        "offline_tag": "Datos enviados externamente: NO | Offline-First",
        "demo_banner": "⚠ VERSIÓN DEMO — No destinada a uso operativo"
    },
    "pt": {
        "title": "Dados da Fatura",
        "inv_num": "Número da Fatura",
        "issue_date": "Data de Emissão",
        "due_date": "Data de Vencimento",
        "amount": "Valor",
        "client": "Cliente",
        "status": "Estado",
        "overdue": "Dias em Atraso",
        "risk": "Nível de Risco",
        "reminder_lvl": "Nível de Cobrança",
        "rem_title": "Aviso de Cobrança Gerado",
        "recs_title": "Recomendações",
        "audit_title": "Registo de Processamento",
        "no_anomalies": "Nenhuma anomalia detetada.",
        "processed": "Processado",
        "offline_tag": "Dados enviados externamente: NÃO | Offline-First",
        "demo_banner": "⚠ VERSÃO DEMO — Não destinada a uso operacional"
    },
}

# ---------------------------------------------------------------------------
# Funzione principale: generate()
# ---------------------------------------------------------------------------
def generate(
    invoice: dict,
    classification: dict,
    compliance: dict,
    billing: dict,
    reminder_text: str,
    language: str = "it",
    output_dir: Optional[str] = None,
    formats: Optional[list] = None,
    is_demo: bool = False,
) -> dict:
    if formats is None:
        formats = ["pdf"]

    lang_code = language.lower() if language else "en"
    if lang_code not in REPORT_LABELS:
        lang_code = "en"

    out_dir = Path(output_dir) if output_dir else Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)

    inv_num = (invoice.get("invoice_number") or "UNKNOWN").replace("/", "-").replace("\\", "-")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"report_AR_{inv_num}_{timestamp}"

    paths = {}
    errors = []

    report_data = _build_report_data(invoice, classification, compliance, billing, reminder_text, lang_code, is_demo)

    for fmt in formats:
        fmt = fmt.lower().strip()
        try:
            if fmt == "pdf":
                p = _generate_pdf(report_data, out_dir / f"{base_name}.pdf", is_demo)
                paths["pdf"] = str(p)
            elif fmt == "docx":
                p = _generate_docx(report_data, out_dir / f"{base_name}.docx", is_demo)
                paths["docx"] = str(p)
            elif fmt == "json":
                p = _generate_json(report_data, out_dir / f"{base_name}.json")
                paths["json"] = str(p)
            elif fmt == "html":
                p = _generate_html(report_data, out_dir / f"{base_name}.html", is_demo)
                paths["html"] = str(p)
            else:
                logger.warning(f"Formato non supportato: {fmt}")
                errors.append(f"formato_non_supportato:{fmt}")
        except Exception as e:
            logger.error(f"Errore generazione {fmt}: {e}")
            errors.append(f"{fmt}:{e}")

    logger.info(f"Report generati: {list(paths.keys())} in {out_dir}")
    return {"paths": paths, "base_name": base_name, "output_dir": str(out_dir), "errors": errors}

# ---------------------------------------------------------------------------
# Builder dati report
# ---------------------------------------------------------------------------
def _build_report_data(invoice, classification, compliance, billing, reminder_text, language, is_demo):
    risk_map = RISK_LABELS.get(language, RISK_LABELS["en"])
    risk_raw  = classification.get("risk_level", "UNKNOWN")
    risk_label = risk_map.get(risk_raw, risk_raw)

    safe_amount = float(invoice.get("amount") or 0.0)
    labels = REPORT_LABELS.get(language, REPORT_LABELS["en"])

    recommendations = compliance.get("recommendations", [])
    if not recommendations:
        recommendations = [labels["no_anomalies"]]

    return {
        "generated_at": datetime.now().isoformat(),
        "software": "ZUKWEND Multilingual Billing Agent",
        "version": "2.1.0",
        "language": language,
        "labels": labels,
        "is_demo": is_demo,
        "invoice": {
            "number":     str(invoice.get("invoice_number") or "N/A"),
            "issue_date": str(invoice.get("issue_date") or "N/A"),
            "due_date":   str(invoice.get("due_date") or "N/A"),
            "amount":     safe_amount,
            "currency":   str(invoice.get("currency") or "EUR"),
            "client":     str(invoice.get("client_name") or "N/A"),
            "vendor":     str(invoice.get("vendor_name") or "N/A"),
        },
        "classification": {
            "payment_status":   str(classification.get("payment_status") or "N/A"),
            "days_overdue":     int(classification.get("days_overdue") or 0),
            "risk_level_raw":   risk_raw,
            "risk_level_label": risk_label,
            "reminder_level":   int(classification.get("reminder_level") or 1),
            "compliance_flag":  bool(classification.get("compliance_flag") or False),
            "rationale":        str(classification.get("classification_rationale") or ""),
            "next_escalation":  str(classification.get("next_escalation_date") or "N/A"),
        },
        "compliance": {
            "flags":           compliance.get("flags", []),
            "recommendations": recommendations,
            "disclaimer":       str(compliance.get("disclaimer") or DISCLAIMER_TEXT.get(language, DISCLAIMER_TEXT["en"])),
        },
        "billing": {
            "action":     str(billing.get("action") or "N/A"),
            "channel":    str(billing.get("recommended_channel") or "N/A"),
            "grace_days": int(billing.get("grace_days") or 5),
        },
        "reminder_text": (
            str(reminder_text or "") + (
                "\n\n---\n[Generato con ZUKWEND DEMO Trial - Sblocca la versione completa su zukwend.com]"
                if is_demo else ""
            )
        ),
        "audit": {
            "processed_at": datetime.now().isoformat(),
            "software_version": "2.1.0",
            "is_demo": is_demo,
            "data_sent_externally": False,
            "disclaimer": DISCLAIMER_TEXT.get(language, DISCLAIMER_TEXT["en"]),
        },
    }

# ---------------------------------------------------------------------------
# Generatore PDF
# ---------------------------------------------------------------------------
def _generate_pdf(data: dict, path: Path, is_demo: bool = False) -> Path:
    if REPORTLAB_AVAILABLE:
        return _generate_pdf_reportlab(data, path, is_demo)
    else:
        return _generate_pdf_text_fallback(data, path, is_demo)

def _generate_pdf_reportlab(data: dict, path: Path, is_demo: bool) -> Path:
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    brand_color = colors.HexColor(BRAND_COLOR_HEX)
    labels = data["labels"]
    story = []

    title_style = ParagraphStyle("ZTitle", parent=styles["Title"],
                                  textColor=brand_color, fontSize=16, spaceAfter=4)
    story.append(Paragraph("ZUKWEND — Multilingual Billing Agent", title_style))
    story.append(Paragraph(f"Report AR | {data['generated_at'][:10]}", styles["Normal"]))
    if is_demo:
        demo_style = ParagraphStyle("Demo", parent=styles["Normal"],
                                     textColor=colors.red, fontSize=10)
        story.append(Paragraph(labels["demo_banner"], demo_style))
    story.append(HRFlowable(width="100%", thickness=1, color=brand_color, spaceAfter=8))

    inv = data["invoice"]
    clf = data["classification"]
    story.append(Paragraph(labels["title"], styles["Heading2"]))
    table_data = [
        [labels["inv_num"],      inv["number"]],
        [labels["issue_date"],   inv["issue_date"]],
        [labels["due_date"],     inv["due_date"]],
        [labels["amount"],       f"{inv['currency']} {inv['amount']:.2f}"],
        [labels["client"],       inv["client"]],
        [labels["status"],       clf["payment_status"]],
        [labels["overdue"],      str(clf["days_overdue"])],
        [labels["risk"],         clf["risk_level_label"]],
        [labels["reminder_lvl"], f"L{clf['reminder_level']}"],
    ]
    t = Table(table_data, colWidths=[5.5*cm, 10.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor(LIGHT_GRAY)),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor(MEDIUM_GRAY)),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor(LIGHT_GRAY)]),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph(labels["rem_title"], styles["Heading2"]))
    for line in data["reminder_text"].split("\n"):
        if line.strip():
            story.append(Paragraph(line, styles["Normal"]))
        else:
            story.append(Spacer(1, 0.2*cm))
    story.append(Spacer(1, 0.5*cm))

    if data["compliance"]["recommendations"]:
        story.append(Paragraph(labels["recs_title"], styles["Heading2"]))
        for rec in data["compliance"]["recommendations"]:
            story.append(Paragraph(f"• {rec}", styles["Normal"]))
        story.append(Spacer(1, 0.3*cm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(MEDIUM_GRAY), spaceAfter=4))
    audit_style = ParagraphStyle("Audit", parent=styles["Normal"], fontSize=8, textColor=colors.gray)
    story.append(Paragraph(f"{labels['processed']}: {data['audit']['processed_at']} | {data['software']} {data['version']}", audit_style))
    story.append(Paragraph(labels["offline_tag"], audit_style))
    story.append(Spacer(1, 0.2*cm))

    disc_style = ParagraphStyle("Disc", parent=styles["Normal"], fontSize=8,
                                 textColor=colors.gray, borderPadding=4)
    story.append(Paragraph(data["audit"]["disclaimer"], disc_style))

    def _draw_demo_footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor("#DC2626"))  # Red warning
        footer_text = "⚠️ ZUKWEND DEMO EVALUATION COPY — Upgrade to FULL Version at https://zukwend.com"
        canvas.drawCentredString(A4[0] / 2.0, 0.8 * cm, footer_text)
        canvas.restoreState()

    if is_demo:
        doc.build(story, onFirstPage=_draw_demo_footer, onLaterPages=_draw_demo_footer)
    else:
        doc.build(story)

    logger.info(f"PDF generato: {path}")
    return path

def _generate_pdf_text_fallback(data: dict, path: Path, is_demo: bool) -> Path:
    txt_path = path.with_suffix(".txt")
    content = _build_text_report(data, is_demo)
    txt_path.write_text(content, encoding="utf-8")
    logger.warning(f"PDF fallback (testo): {txt_path}")
    return txt_path

def _build_text_report(data: dict, is_demo: bool) -> str:
    sep = "=" * 60
    inv = data["invoice"]
    clf = data["classification"]
    labels = data["labels"]
    lines = [
        sep,
        "ZUKWEND — Multilingual Billing Agent",
        f"Report AR | {data['generated_at'][:10]}",
        labels["demo_banner"] if is_demo else "FULL ENTERPRISE",
        sep,
        labels["title"].upper(),
        f"  {labels['inv_num']}:     {inv['number']}",
        f"  {labels['due_date']}:    {inv['due_date']}",
        f"  {labels['amount']}:      {inv['currency']} {inv['amount']:.2f}",
        f"  {labels['client']}:      {inv['client']}",
        f"  {labels['status']}:      {clf['payment_status']} ({clf['days_overdue']})",
        f"  {labels['risk']}:        {clf['risk_level_label']} | L{clf['reminder_level']}",
        sep,
        labels["rem_title"].upper(),
        data["reminder_text"],
        sep,
        labels["recs_title"].upper(),
    ] + [f"  • {r}" for r in data["compliance"]["recommendations"]] + [
        sep,
        f"{labels['processed']}: {data['audit']['processed_at']}",
        data["audit"]["disclaimer"],
        sep,
    ]
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Generatore DOCX
# ---------------------------------------------------------------------------
def _generate_docx(data: dict, path: Path, is_demo: bool = False) -> Path:
    if not DOCX_AVAILABLE:
        raise RuntimeError("python-docx non disponibile")

    labels = data["labels"]
    doc = DocxDocument()
    inv = data["invoice"]
    clf = data["classification"]

    title = doc.add_heading("ZUKWEND — Multilingual Billing Agent", level=1)
    title.runs[0].font.color.rgb = RGBColor(0xFF, 0x6B, 0x00)
    doc.add_paragraph(f"Report AR | {data['generated_at'][:10]}")
    if is_demo:
        p = doc.add_paragraph(labels["demo_banner"])
        p.runs[0].font.color.rgb = RGBColor(0xFF, 0, 0)

    doc.add_heading(labels["title"], level=2)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "Field"
    hdr[1].text = "Value"
    rows = [
        (labels["inv_num"],      inv["number"]),
        (labels["issue_date"],   str(inv["issue_date"])),
        (labels["due_date"],     str(inv["due_date"])),
        (labels["amount"],       f"{inv['currency']} {inv['amount']:.2f}"),
        (labels["client"],       inv["client"]),
        (labels["status"],       clf["payment_status"]),
        (labels["overdue"],      str(clf["days_overdue"])),
        (labels["risk"],         clf["risk_level_label"]),
    ]
    for field, value in rows:
        row = table.add_row().cells
        row[0].text = field
        row[1].text = str(value)

    doc.add_heading(labels["rem_title"], level=2)
    doc.add_paragraph(data["reminder_text"])

    doc.add_heading(labels["recs_title"], level=2)
    for rec in data["compliance"]["recommendations"]:
        doc.add_paragraph(f"• {rec}")

    doc.add_heading(labels["audit_title"], level=3)
    audit_para = doc.add_paragraph(
        f"{labels['processed']}: {data['audit']['processed_at']} | {data['software']}\n"
        f"{labels['offline_tag']}"
    )
    audit_para.runs[0].font.size = Pt(9)

    disclaimer = doc.add_paragraph(data["audit"]["disclaimer"])
    disclaimer.runs[0].font.size = Pt(9)
    disclaimer.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    doc.save(str(path))
    logger.info(f"DOCX generato: {path}")
    return path

# ---------------------------------------------------------------------------
# Generatore JSON
# ---------------------------------------------------------------------------
def _generate_json(data: dict, path: Path) -> Path:
    json_out = {
        "zukwend_version": data["version"],
        "generated_at": data["generated_at"],
        "language": data["language"],
        "is_demo": data["is_demo"],
        "invoice": data["invoice"],
        "classification": data["classification"],
        "compliance": data["compliance"],
        "billing": data["billing"],
        "reminder_text": data["reminder_text"],
        "audit": data["audit"],
    }
    path.write_text(
        json.dumps(json_out, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    logger.info(f"JSON generato: {path}")
    return path

# ---------------------------------------------------------------------------
# Generatore HTML
# ---------------------------------------------------------------------------
def _generate_html(data: dict, path: Path, is_demo: bool = False) -> Path:
    inv = data["invoice"]
    clf = data["classification"]
    labels = data["labels"]
    risk_class = {"LOW": "risk-low", "MEDIUM": "risk-medium", "HIGH": "risk-high"}.get(
        clf["risk_level_raw"], ""
    )
    demo_banner = (
        f'<div class="demo-banner">{labels["demo_banner"]}</div>'
        if is_demo else ""
    )
    recs_html = "".join(f"<li>{r}</li>" for r in data["compliance"]["recommendations"])
    reminder_html = data["reminder_text"].replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html lang="{data['language']}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Report AR — ZUKWEND</title>
  <style>
    body {{ font-family: Calibri, 'Segoe UI', sans-serif; color: #1a1a1a; margin: 0; padding: 20px; background: #f9f9f9; }}
    .header {{ background: #ff6b00; color: white; padding: 20px 24px; border-radius: 6px 6px 0 0; }}
    .header h1 {{ margin: 0; font-size: 1.4em; }}
    .header p  {{ margin: 4px 0 0; font-size: 0.9em; opacity: 0.9; }}
    .container {{ background: white; border: 1px solid #e0e0e0; border-radius: 0 0 6px 6px; padding: 24px; }}
    .demo-banner {{ background: #ffeaea; color: #c00; border: 1px solid #f00; padding: 10px; margin-bottom: 16px; border-radius: 4px; }}
    .section-title {{ color: #ff6b00; border-bottom: 2px solid #ff6b00; padding-bottom: 4px; margin-top: 24px; font-size: 1.1em; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ padding: 8px 12px; text-align: left; border: 1px solid #e0e0e0; font-size: 0.95em; }}
    th {{ background: #f5f5f5; font-weight: bold; width: 35%; }}
    .risk-low    {{ color: #28a745; font-weight: bold; }}
    .risk-medium {{ color: #ffc107; font-weight: bold; }}
    .risk-high   {{ color: #dc3545; font-weight: bold; }}
    .reminder-box {{ background: #f9f4ef; border-left: 4px solid #ff6b00; padding: 16px; margin-top: 12px; border-radius: 0 4px 4px 0; font-size: 0.95em; line-height: 1.6; }}
    .disclaimer {{ font-size: 0.82em; color: #888; margin-top: 20px; border-top: 1px solid #eee; padding-top: 12px; }}
    .audit {{ font-size: 0.82em; color: #aaa; margin-top: 8px; }}
    ul {{ padding-left: 20px; }}
    li {{ margin-bottom: 4px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>ZUKWEND — Multilingual Billing Agent</h1>
    <p>Report AR | {data['generated_at'][:10]} | {data['software']} {data['version']}</p>
  </div>
  <div class="container">
    {demo_banner}
    <div class="section-title">{labels['title']}</div>
    <table>
      <tr><th>{labels['inv_num']}</th><td>{inv['number']}</td></tr>
      <tr><th>{labels['issue_date']}</th><td>{inv['issue_date']}</td></tr>
      <tr><th>{labels['due_date']}</th><td>{inv['due_date']}</td></tr>
      <tr><th>{labels['amount']}</th><td><strong>{inv['currency']} {inv['amount']:.2f}</strong></td></tr>
      <tr><th>{labels['client']}</th><td>{inv['client']}</td></tr>
      <tr><th>{labels['status']}</th><td>{clf['payment_status']}</td></tr>
      <tr><th>{labels['overdue']}</th><td>{clf['days_overdue']}</td></tr>
      <tr><th>{labels['risk']}</th><td class="{risk_class}">{clf['risk_level_label']}</td></tr>
      <tr><th>{labels['reminder_lvl']}</th><td>L{clf['reminder_level']}</td></tr>
    </table>
    <div class="section-title">{labels['rem_title']}</div>
    <div class="reminder-box">{reminder_html}</div>
    <div class="section-title">{labels['recs_title']}</div>
    <ul>{recs_html}</ul>
    <div class="disclaimer">{data['audit']['disclaimer']}</div>
    <div class="audit">
      {labels['processed']}: {data['audit']['processed_at']} | {labels['offline_tag']}
    </div>
  </div>
</body>
</html>"""

    path.write_text(html, encoding="utf-8")
    logger.info(f"HTML generato: {path}")
    return path