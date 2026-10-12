"""
Script di utilità per generare una fattura B2B finta per il testing di ZUKWEND.
"""
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from pathlib import Path

def crea_pdf_fattura():
    output_path = Path("fattura_test_b2b.pdf")
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []

    # Intestazione Azienda Emittente
    title_style = ParagraphStyle("Vendor", parent=styles["Heading1"], fontSize=14, textColor=colors.HexColor("#FF6B00"))
    story.append(Paragraph("ACME SOLUTIONS S.R.L.", title_style))
    story.append(Paragraph("Via Roma 10, 50123 Firenze (FI) — P.IVA 01234567890", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Dati Cliente e Fattura
    story.append(Paragraph("<b>Spett.le</b><br/>CLIENTE DEMO S.P.A.<br/>Via Milano 20, 20100 Milano (MI)", styles["Normal"]))
    story.append(Spacer(1, 20))

    inv_style = ParagraphStyle("InvDetails", parent=styles["Normal"], fontSize=11, leading=14)
    inv_text = """
    <b>Fattura n.</b> INV-2026-001<br/>
    <b>Data emissione:</b> 2026-09-01<br/>
    <b>Data scadenza:</b> 2026-09-30<br/>
    <b>Condizioni di pagamento:</b> 30 giorni data fattura
    """
    story.append(Paragraph(inv_text, inv_style))
    story.append(Spacer(1, 20))

    # Tabella Prodotti / Importo
    table_data = [
        ["Descrizione Servizio", "Quantità", "Prezzo Unitario", "Totale"],
        ["Consulenza Software AR Automation", "1", "1.250,00", "1.250,00"],
        ["TOTALE FATTURA", "", "", "EUR 1.250,00"]
    ]
    t = Table(table_data, colWidths=[220, 70, 100, 110])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F5F5F5")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#FFF4EE")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 30))

    # Chiusura
    story.append(Paragraph("Coordinate Bancarie IBAN: IT95X0306903245100000001234", styles["Normal"]))
    doc.build(story)
    print(f"Fattura di test generata con successo: {output_path.absolute()}")

if __name__ == "__main__":
    crea_pdf_fattura()