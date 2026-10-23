"""
Generazione PDF Test Fattura Positiva Scaduta
b2b_invoice_positive_overdue.pdf
Specifiche:
- Invoice #INV-2026-0999
- Invoice Date: May 10, 2026 | Due Date: June 09, 2026
- Total Amount Due: € +18,450.00 (Importo POSITIVO, NESSUNA dicitura Credit Note)
- Customer: Global Logistics Solutions Ltd.
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_positive_overdue_pdf(output_path: str = "demo/b2b_invoice_positive_overdue.pdf"):
    pdf_file = Path(output_path)
    pdf_file.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(pdf_file),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    # Vendor Header
    vendor_title = ParagraphStyle(
        "VendorTitle",
        parent=styles["Heading1"],
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1E3A8A")
    )
    story.append(Paragraph("<b>EUROPEAN LOGISTICS FREIGHT CORP.</b>", vendor_title))
    story.append(Paragraph("120 Avenue des Champs-Elysees, 75008 Paris, France — VAT: FR-12345678901", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Customer Header
    customer_style = ParagraphStyle(
        "CustomerStyle",
        parent=styles["Normal"],
        fontSize=11,
        leading=15
    )
    story.append(Paragraph(
        "<b>Customer / Bill To:</b><br/>"
        "Global Logistics Solutions Ltd.<br/>"
        "45 Canary Wharf, London, E14 5AB, United Kingdom",
        customer_style
    ))
    story.append(Spacer(1, 20))

    # Invoice Details Block
    inv_details_style = ParagraphStyle(
        "InvDetailsStyle",
        parent=styles["Normal"],
        fontSize=11,
        leading=16
    )
    inv_text = """
    <b>Invoice #INV-2026-0999</b><br/>
    <b>Invoice Date:</b> May 10, 2026<br/>
    <b>Due Date:</b> June 09, 2026<br/>
    <b>Payment Terms:</b> 30 Days Net
    """
    story.append(Paragraph(inv_text, inv_details_style))
    story.append(Spacer(1, 20))

    # Line Items Table
    table_data = [
        ["Description", "Qty", "Unit Price", "Total"],
        ["Cross-Border Intermodal Freight Transport", "1", "€ +18,450.00", "€ +18,450.00"],
        ["TOTAL AMOUNT DUE", "", "", "€ +18,450.00"]
    ]
    t = Table(table_data, colWidths=[240, 50, 115, 115])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFF6FF")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#1E3A8A")),
    ]))
    story.append(t)
    story.append(Spacer(1, 30))

    # Wire transfer details
    story.append(Paragraph("<b>Wire Instructions:</b> IBAN: FR7630006000011234567890189 — BIC: BPAFRPP", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>Standard Commercial B2B Invoice — Subject to commercial law.</i>", styles["Normal"]))

    doc.build(story)
    print(f"[OK] Generated: {pdf_file.resolve()}")
    return str(pdf_file.resolve())

if __name__ == "__main__":
    generate_positive_overdue_pdf()
