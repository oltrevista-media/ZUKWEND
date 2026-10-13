"""
Generatore di fattura di test in lingua inglese b2b_invoice_sample_en.pdf
Specifiche v2.1.2:
- Importo: $ 18,450.00
- Client: : Global Logistics Solutions Ltd. (con ':' iniziale per testare pulizia)
- Address: 45 Canary Wharf, London, E14 5AB, UK Invoice (con 'Invoice' in coda per testare pulizia token layout)
- Scadenza: 126 giorni fa rispetto ad oggi (es. 2026-06-09 per oggi 2026-10-13)
"""
from pathlib import Path
from datetime import date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_sample_invoice(output_path: str = "b2b_invoice_sample_en.pdf", days_overdue: int = 126):
    today = date.today()
    due_date = today - timedelta(days=days_overdue)
    issue_date = due_date - timedelta(days=30)

    pdf_file = Path(output_path)
    doc = SimpleDocTemplate(str(pdf_file), pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []

    # Vendor Header
    vendor_title = ParagraphStyle("Vendor", parent=styles["Heading1"], fontSize=14, textColor=colors.HexColor("#FF6B00"))
    story.append(Paragraph("ACME GLOBAL LOGISTICS CORP.", vendor_title))
    story.append(Paragraph("100 Wall Street, New York, NY 10005, USA — Tax ID: US-987654321", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Client Header (with leading colon and trailing 'Invoice' to verify extraction and normalization trimming)
    client_style = ParagraphStyle("Client", parent=styles["Normal"], fontSize=11, leading=14)
    story.append(Paragraph("<b>Bill To:</b><br/>: Global Logistics Solutions Ltd.<br/>45 Canary Wharf, London, E14 5AB, UK Invoice", client_style))
    story.append(Spacer(1, 20))

    # Invoice Details
    inv_style = ParagraphStyle("InvDetails", parent=styles["Normal"], fontSize=11, leading=14)
    inv_text = f"""
    <b>Invoice No:</b> INV-2026-ENG-001<br/>
    <b>Issue Date:</b> {issue_date.strftime('%Y-%m-%d')}<br/>
    <b>Due Date:</b> {due_date.strftime('%Y-%m-%d')}<br/>
    <b>Payment Terms:</b> 30 Days Net
    """
    story.append(Paragraph(inv_text, inv_style))
    story.append(Spacer(1, 20))

    # Line Items Table
    table_data = [
        ["Description", "Qty", "Unit Price", "Total"],
        ["International Ocean Freight Forwarding", "1", "$ 18,450.00", "$ 18,450.00"],
        ["TOTAL AMOUNT DUE", "", "", "$ 18,450.00"]
    ]
    t = Table(table_data, colWidths=[220, 60, 110, 110])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F5F5")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFF4EE")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 30))

    # Banking / Wire Info
    story.append(Paragraph("Wire Instructions: Swift/BIC: ACMUS33XXX — Account: 88392019482", styles["Normal"]))
    doc.build(story)
    print(f"Sample PDF created: {pdf_file.resolve()}")
    return str(pdf_file.resolve())

if __name__ == "__main__":
    generate_sample_invoice()
