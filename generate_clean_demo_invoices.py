"""
ZUKWEND — Clean B2B Sample Invoice Generator (6 Localized Invoices)
Compliant with ORDER v3.46 (Demo Folder Standardization)
Generates exactly 6 clean, professional B2B sample invoices in PDF format:
1. Italian (IT)
2. English (EN)
3. German (DE)
4. French (FR)
5. Spanish (ES)
6. Portuguese (PT)
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

DEMO_DIR = Path("C:/OLTREVISTA_AI/ZUKWEND_repo/demo")

INVOICES_SPEC = [
    {
        "lang": "it",
        "filename": "demo_invoice_it.pdf",
        "vendor_name": "Lombardia Sistemi Industriali S.p.A.",
        "vendor_address": "Corso Buenos Aires 45, 20124 Milano (MI) — P.IVA IT01928374650",
        "client_keyword": "Spett.le:",
        "client_name": "Milano Tech Solutions S.r.l.",
        "client_address": "Via Monte Napoleone 8, 20121 Milano (MI)",
        "client_tax_label": "P.IVA:",
        "client_tax_id": "IT08472910963",
        "inv_label": "Fattura n.",
        "inv_number": "FT-2026-IT01",
        "issue_label": "Data emissione:",
        "issue_date": "2026-09-20",
        "due_label": "Data scadenza:",
        "due_date": "2026-10-18",
        "terms_label": "Condizioni di pagamento:",
        "terms": "30 giorni data fattura fine mese",
        "items": [
            ("Consulenza Sistemi Cloud e Cybersecurity", "40 ore", "€ 85,00", "€ 3.400,00"),
            ("Manutenzione Software ERP Annuale", "1", "€ 1.450,00", "€ 1.450,00"),
        ],
        "total_label": "TOTALE FATTURA (Importo Dovuto):",
        "amount_str": "EUR 4.850,00",
        "bank_info": "Coordinate Bancarie: IBAN IT95X0306903245100000001234 — Swift/BIC: UNCRITM1XXX",
        "notes": "Fattura commerciale B2B soggetta a split payment. Pagamento tramite bonifico bancario.",
    },
    {
        "lang": "en",
        "filename": "demo_invoice_en.pdf",
        "vendor_name": "Apex Global Logistics Ltd.",
        "vendor_address": "100 Bishopsgate, London, EC2N 4AG, United Kingdom — Tax ID: GB-849201948",
        "client_keyword": "Bill To:",
        "client_name": "Horizon Data Systems Inc.",
        "client_address": "75 London Wall, London, EC2M 5QD, UK",
        "client_tax_label": "VAT ID:",
        "client_tax_id": "GB924817502",
        "inv_label": "Invoice No.",
        "inv_number": "INV-2026-EN02",
        "issue_label": "Date of issue:",
        "issue_date": "2026-09-05",
        "due_label": "Due date:",
        "due_date": "2026-10-05",
        "terms_label": "Payment terms:",
        "terms": "Net 30 Days",
        "items": [
            ("Cross-Border Freight Forwarding Logistics", "2 Units", "$ 5,200.00", "$ 10,400.00"),
            ("Customs Clearance and Handling Services", "1 Service", "$ 3,850.00", "$ 3,850.00"),
        ],
        "total_label": "TOTAL INVOICE (Amount Due):",
        "amount_str": "$ 14,250.00",
        "bank_info": "Bank Details: Barclays Bank UK — Account: 82910482 — Sort Code: 20-00-00 — IBAN: GB29BARC20000082910482",
        "notes": "Standard B2B commercial invoice. Payment via wire transfer within specified payment terms.",
    },
    {
        "lang": "de",
        "filename": "demo_invoice_de.pdf",
        "vendor_name": "Rheinland Industrietechnik GmbH",
        "vendor_address": "Königsallee 60, 40212 Düsseldorf, Deutschland — USt-IdNr.: DE293847561",
        "client_keyword": "Kunde:",
        "client_name": "Bavaria Maschinenbau GmbH",
        "client_address": "Industriestrasse 45, 80339 Muenchen, Deutschland",
        "client_tax_label": "USt-IdNr.:",
        "client_tax_id": "DE318947291",
        "inv_label": "Rechnung Nr.",
        "inv_number": "RECH-2026-DE03",
        "issue_label": "Ausstellungsdatum:",
        "issue_date": "2026-08-15",
        "due_label": "Faelligkeitsdatum:",
        "due_date": "2026-09-15",
        "terms_label": "Zahlungsbedingungen:",
        "terms": "30 Tage netto faellig",
        "items": [
            ("Industrielle Steuerungskomponenten Modul A4", "10 Stk.", "€ 1.250,00", "€ 12.500,00"),
            ("Systemintegration und Kalibrierung", "1 Pauschale", "€ 6.420,00", "€ 6.420,00"),
        ],
        "total_label": "GESAMTBETRAG (Rechnung faellig):",
        "amount_str": "EUR 18.920,00",
        "bank_info": "Bankverbindung: Deutsche Bank Frankfurt — IBAN: DE89370400440532013000 — BIC: DEUTDEDDFXX",
        "notes": "Gewerbliche B2B-Rechnung. Bitte ueberweisen Sie den Gesamtbetrag unter Angabe der Rechnungsnummer.",
    },
    {
        "lang": "fr",
        "filename": "demo_invoice_fr.pdf",
        "vendor_name": "Hexagone Cloud Services SAS",
        "vendor_address": "15 Rue de Rivoli, 75001 Paris, France — TVA: FR58392019482",
        "client_keyword": "Client:",
        "client_name": "Alliance Digitale SAS",
        "client_address": "24 Rue de la Paix, 75002 Paris, France",
        "client_tax_label": "TVA:",
        "client_tax_id": "FR74839201948",
        "inv_label": "Facture N°",
        "inv_number": "FAC-2026-FR04",
        "issue_label": "Date de facturation:",
        "issue_date": "2026-07-15",
        "due_label": "Date d'echeance:",
        "due_date": "2026-08-14",
        "terms_label": "Conditions de paiement:",
        "terms": "Paiement à 30 jours date de facture",
        "items": [
            ("Abonnement Infrastructure Serveurs Haute Disponibilité", "1 Mois", "€ 4.500,00", "€ 4.500,00"),
            ("Support Technique Dédié Entreprise 24/7", "1 Forfait", "€ 2.840,00", "€ 2.840,00"),
        ],
        "total_label": "MONTANT TOTAL (Facture emise):",
        "amount_str": "EUR 7.340,00",
        "bank_info": "Coordonnées Bancaires: BNP Paribas Paris — IBAN: FR7630004012345678901234567 — BIC: BNPAFRPPXXX",
        "notes": "Facture commerciale B2B. En cas de retard de paiement, une indemnité forfaitaire légale sera appliquée.",
    },
    {
        "lang": "es",
        "filename": "demo_invoice_es.pdf",
        "vendor_name": "Soluciones Ibericas de Transporte S.L.",
        "vendor_address": "Calle Gran Via 32, 28013 Madrid, Espana — CIF: ESA28394851",
        "client_keyword": "Cliente:",
        "client_name": "Iberia Logistica y Distribucion S.L.",
        "client_address": "Paseo de la Castellana 120, 28046 Madrid, Espana",
        "client_tax_label": "CIF:",
        "client_tax_id": "ESB84920183",
        "inv_label": "Factura n.°",
        "inv_number": "FAC-2026-ES05",
        "issue_label": "Fecha de factura:",
        "issue_date": "2026-06-10",
        "due_label": "Fecha de vencimiento:",
        "due_date": "2026-07-10",
        "terms_label": "Condiciones de pago:",
        "terms": "Pago a 30 dias fecha factura emitida",
        "items": [
            ("Distribucion Logistica Nacional Ruta Norte-Sur", "3 Rutas", "€ 8.500,00", "€ 25.500,00"),
            ("Almacenamiento y Gestion de Stock Paletizado", "1 Trimestre", "€ 6.000,00", "€ 6.000,00"),
        ],
        "total_label": "IMPORTE TOTAL (Factura vencimiento):",
        "amount_str": "EUR 31.500,00",
        "bank_info": "Datos Bancarios: Banco Santander — IBAN: ES9100491500051234567892 — BIC: BSCHESMMXXX",
        "notes": "Factura comercial B2B emitida de acuerdo con la legislacion mercantil vigente.",
    },
    {
        "lang": "pt",
        "filename": "demo_invoice_pt.pdf",
        "vendor_name": "Atlantico Consultoria e Gestao Lda.",
        "vendor_address": "Rua Augusta 110, 1100-053 Lisboa, Portugal — NIF: PT501928374",
        "client_keyword": "Cliente:",
        "client_name": "Lisboa Inovacao e Tecnologia Lda.",
        "client_address": "Avenida da Liberdade 180, 1250-146 Lisboa, Portugal",
        "client_tax_label": "NIF:",
        "client_tax_id": "PT509837261",
        "inv_label": "Fatura N.º",
        "inv_number": "FAT-2026-PT06",
        "issue_label": "Data da fatura:",
        "issue_date": "2026-09-25",
        "due_label": "Data de vencimento:",
        "due_date": "2026-10-25",
        "terms_label": "Condicoes de pagamento:",
        "terms": "Pagamento a 30 dias fatura emitida",
        "items": [
            ("Desenvolvimento de Software à Medida e APIs", "60 horas", "€ 110,00", "€ 6.600,00"),
            ("Consultoria de Transformacao Digital e Cloud", "1 Servico", "€ 2.550,00", "€ 2.550,00"),
        ],
        "total_label": "VALOR TOTAL (Fatura vencimento):",
        "amount_str": "EUR 9.150,00",
        "bank_info": "Dados Bancarios: Millennium BCP — IBAN: PT50003300001234567890123 — BIC: BCPTPTLX",
        "notes": "Fatura comercial B2B emitida por computador ao abrigo do artigo 35.º do CIVA.",
    },
]


def build_pdf(spec: dict, dest_path: Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(dest_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    # Vendor Header Banner
    vendor_title = ParagraphStyle(
        "VendorTitle",
        parent=styles["Heading1"],
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0F172A")
    )
    vendor_sub = ParagraphStyle(
        "VendorSub",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569")
    )
    story.append(Paragraph(f"<b>{spec['vendor_name']}</b>", vendor_title))
    story.append(Paragraph(spec["vendor_address"], vendor_sub))
    story.append(Spacer(1, 10))

    # Divider bar
    divider = Table([[""]], colWidths=[523], rowHeights=[2])
    divider.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FF6B00")),
        ("PADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 12))

    # Recipient / Client Block (Cleanly isolated vertically)
    client_p = ParagraphStyle("ClientP", parent=styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#1E293B"))
    client_html = f"""
    <b>{spec['client_keyword']}</b><br/>
    <b>{spec['client_name']}</b><br/>
    {spec['client_address']}<br/>
    <b>{spec['client_tax_label']} {spec['client_tax_id']}</b>
    """
    client_box = Table([[Paragraph(client_html, client_p)]], colWidths=[523])
    client_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(client_box)
    story.append(Spacer(1, 10))

    # Invoice Details Block (Cleanly isolated vertically)
    inv_p = ParagraphStyle("InvP", parent=styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#1E293B"))
    inv_html = f"""
    <b>{spec['inv_label']}</b> {spec['inv_number']} &nbsp;|&nbsp; 
    <b>{spec['issue_label']}</b> {spec['issue_date']} &nbsp;|&nbsp; 
    <b>{spec['due_label']}</b> {spec['due_date']} &nbsp;|&nbsp; 
    <b>{spec['terms_label']}</b> {spec['terms']}
    """
    inv_box = Table([[Paragraph(inv_html, inv_p)]], colWidths=[523])
    inv_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(inv_box)
    story.append(Spacer(1, 15))

    # Line Items Table
    table_data = [["Description", "Qty", "Unit Price", "Total Amount"]]
    for item in spec["items"]:
        table_data.append([item[0], item[1], item[2], item[3]])
    table_data.append([spec["total_label"], "", "", spec["amount_str"]])

    items_table = Table(table_data, colWidths=[263, 70, 95, 95])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#E2E8F0")),
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -2), 9),
        ("PADDING", (0, 0), (-1, -1), 6),
        # Total Row
        ("SPAN", (0, -1), (2, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FEF3C7")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 10),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#92400E")),
        ("BOX", (0, -1), (-1, -1), 1.5, colors.HexColor("#F59E0B")),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 20))

    # Banking & Legal Footer
    footer_p = ParagraphStyle("FooterP", parent=styles["Normal"], fontSize=8, leading=12, textColor=colors.HexColor("#64748B"))
    story.append(Paragraph(f"<b>{spec['bank_info']}</b>", footer_p))
    story.append(Spacer(1, 4))
    story.append(Paragraph(spec["notes"], footer_p))

    doc.build(story)
    print(f"[OK] Generated: {dest_path.name}")


def main():
    print(f"[*] Generating 6 standardized localized demo invoices in {DEMO_DIR}...")
    for spec in INVOICES_SPEC:
        target = DEMO_DIR / spec["filename"]
        build_pdf(spec, target)
    print("[*] All 6 demo invoices created successfully.")


if __name__ == "__main__":
    main()
