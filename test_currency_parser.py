#!/usr/bin/env python3
"""
================================================================================
ZUKWEND v2.1.1 — UNIVERSAL CURRENCY PARSER & NOTICE GENERATOR UNIT TEST SUITE
Destinatario: Antigravity / Gemini 3.8 Flash
Progetto Target: REPO_ZUKWEND (Engine Core)
File: test_currency_parser.py
================================================================================
Verifica i requisiti FIX-TOTAL ENGINE v2.1.1:
1. normalize_currency(raw_val):
   - Anglo-Sassone ("18,450.00" -> 18450.00)
   - Continentale ("18.450,00" -> 18450.00)
   - Svizzero ("18'450.00" -> 18450.00)
   - Simboli originali ($, €, £, CHF) e default EUR
2. Pulizia Nome Cliente (rimozione ':' iniziale orfano, virgole, spazi doppi)
3. Pipeline completa su "b2b_invoice_sample_en.pdf":
   - Amount: 18450.00 (EUR / $)
   - Days Overdue: 126
   - Notice text: "overdue by 126 days" (e NON "0 days")
   - Client Name: "Global Logistics Solutions Ltd."
================================================================================
"""

import sys
import unittest
from pathlib import Path
from datetime import date, timedelta

# Imposta il percorso del modulo
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import parser
import normalizer
import classifier
import deducer
import workflow_engine
from generate_sample_en_pdf import generate_sample_invoice

class TestUniversalCurrencyParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Assicura la presenza del file sample PDF aggiornato con 126 giorni di ritardo
        cls.pdf_path = CURRENT_DIR / "b2b_invoice_sample_en.pdf"
        generate_sample_invoice(str(cls.pdf_path), days_overdue=126)

    def test_01_normalize_currency_formats(self):
        """Azione 1: Verifica parser importi formati Anglo-Sassone, Continentale e Svizzero."""
        test_cases = [
            ("18,450.00", 18450.00, "EUR"),
            ("18.450,00", 18450.00, "EUR"),
            ("18'450.00", 18450.00, "EUR"),
            ("18’450.00", 18450.00, "EUR"),
            ("$ 18,450.00", 18450.00, "$"),
            ("$18,450.00", 18450.00, "$"),
            ("EUR 18,450.00", 18450.00, "EUR"),
            ("€ 18.450,00", 18450.00, "€"),
            ("CHF 18'450.00", 18450.00, "CHF"),
            ("18'450.00 CHF", 18450.00, "CHF"),
            ("£ 18,450.00", 18450.00, "£"),
        ]

        for raw_val, expected_amt, expected_curr in test_cases:
            # Test su parser.normalize_currency
            res_p = parser.normalize_currency(raw_val)
            self.assertEqual(res_p.amount, expected_amt, f"Fallito importo parser per '{raw_val}'")
            self.assertEqual(res_p.currency, expected_curr, f"Fallita valuta parser per '{raw_val}'")

            # Verifica unpacking tupla (amount, currency)
            amt, curr = res_p
            self.assertEqual(amt, expected_amt)
            self.assertEqual(curr, expected_curr)

            # Test su normalizer.normalize_currency
            res_n = normalizer.normalize_currency(raw_val)
            self.assertEqual(res_n.amount, expected_amt, f"Fallito importo normalizer per '{raw_val}'")
            self.assertEqual(res_n.currency, expected_curr, f"Fallita valuta normalizer per '{raw_val}'")

    def test_02_client_name_cleaning(self):
        """Azione 2: Verifica pulizia caratteri di punteggiatura orfani nel Nome Cliente."""
        dirty_names = [
            (": Global Logistics Solutions Ltd.", "Global Logistics Solutions Ltd."),
            (":  Global  Logistics   Solutions  Ltd.  ", "Global Logistics Solutions Ltd."),
            (", Global Logistics Solutions Ltd. ,", "Global Logistics Solutions Ltd."),
            ("Global Logistics Solutions Ltd.", "Global Logistics Solutions Ltd."),
            (":: Global Logistics Solutions Ltd. ::", "Global Logistics Solutions Ltd."),
        ]

        for raw_name, clean_expected in dirty_names:
            norm_name = normalizer.normalize_name(raw_name)
            self.assertEqual(norm_name, clean_expected, f"Pulizia nome fallita per '{raw_name}'")
            self.assertFalse(norm_name.startswith(":"), f"Nome inizia ancora con due punti: '{norm_name}'")

    def test_03_layout_token_and_address_cleaning(self):
        """Azione 2b (v2.1.2): Trimming finale token spuri layout su indirizzo e nome cliente."""
        test_addresses = [
            ("London, UK Invoice", "London, UK"),
            ("45 Canary Wharf, London, E14 5AB, UK Invoice", "45 Canary Wharf, London, E14 5AB, UK"),
            ("Paris, France Facture", "Paris, France"),
            ("Berlin, Germany Rechnung", "Berlin, Germany"),
            ("Milano, Italy Page 1", "Milano, Italy"),
            ("Madrid, Spain - Invoice No: 99", "Madrid, Spain"),
            ("London, UK", "London, UK"),
        ]

        for raw_addr, expected_addr in test_addresses:
            clean_addr = normalizer.normalize_address(raw_addr)
            self.assertEqual(clean_addr, expected_addr, f"Pulizia indirizzo fallita per '{raw_addr}'")
            self.assertNotIn("Invoice", clean_addr or "", f"Parola 'Invoice' ancora presente in indirizzo: '{clean_addr}'")

        test_names = [
            ("Global Logistics Solutions Ltd. Invoice", "Global Logistics Solutions Ltd."),
            ("Acme Corp Page", "Acme Corp"),
            ("Siemens AG Rechnung", "Siemens AG"),
            ("Alstom SA Facture", "Alstom SA"),
        ]
        for raw_n, exp_n in test_names:
            clean_n = normalizer.normalize_name(raw_n)
            self.assertEqual(clean_n, exp_n, f"Pulizia nome con token layout fallita per '{raw_n}'")

    def test_04_dynamic_recommendations_localization(self):
        """Azione 1b (v2.1.2): Localizzazione dinamica raccomandazioni 100% EN su report/deducer."""
        dummy_inv = {"detected_language": "en", "amount": 18450.0, "currency": "$"}
        dummy_classif = {
            "compliance_flag": True,
            "flags": ["high_value_kyc_aml", "critical_overdue_risk_inesigibilita"],
            "reminder_level": 3,
            "days_overdue": 126
        }

        comp_en = deducer.check_compliance(dummy_inv, dummy_classif, language="en")
        recs_en = comp_en["recommendations"]

        expected_en = [
            "Amount exceeds compliance threshold: authorization required.",
            "High value amount: verify KYC/AML procedures.",
            "Notice level 3: consult legal counsel prior to formal escalation.",
            "Overdue exceeds 90 days: evaluate debt recovery or bad debt provisioning.",
        ]

        for expected in expected_en:
            self.assertIn(expected, recs_en, f"Raccomandazione EN mancante: '{expected}'")

        # Verifica assenza assoluta di residui in lingua italiana
        italian_fragments = ["Importo superiore", "Livello 3", "Oltre 90", "legale", "soglia"]
        for rec in recs_en:
            for frag in italian_fragments:
                self.assertNotIn(frag.lower(), rec.lower(), f"Residuo italiano '{frag}' in raccomandazione EN: '{rec}'")

    def test_05_full_pipeline_verification(self):
        """Azione 3 (v2.1.2): Esecuzione pipeline completa su b2b_invoice_sample_en.pdf e smoke test."""
        result = workflow_engine.run_pipeline(str(self.pdf_path), language="en", mode="local")
        self.assertTrue(result.success, f"Pipeline fallita con errori: {result.errors}")

        invoice = result.invoice
        classification = result.classification
        compliance = result.compliance
        reminder_text = result.reminder_text

        # 1. Amount: 18450.00 (EUR / $)
        self.assertEqual(invoice.get("amount"), 18450.00, "Importo estratto non corrisponde a 18450.00")
        self.assertIn(invoice.get("currency"), ["$", "USD", "EUR"], "Valuta estratta non valida")

        # 2. Days Overdue: 126
        self.assertEqual(classification.get("days_overdue"), 126, "Giorni di ritardo non corrispondono a 126")

        # 3. Notice text: "overdue by 126 days" (e NON "0 days")
        self.assertIn("overdue by 126 days", reminder_text, "Il testo del sollecito non contiene 'overdue by 126 days'")
        self.assertNotIn("0 days", reminder_text, "Il testo del sollecito contiene erroneamente '0 days'")
        self.assertNotIn("overdue by 0 days", reminder_text, "Il testo del sollecito contiene erroneamente 'overdue by 0 days'")

        # 4. Client Name: "Global Logistics Solutions Ltd." (senza ':' iniziale e senza token spuri)
        self.assertEqual(invoice.get("client_name"), "Global Logistics Solutions Ltd.", "Nome cliente estratto non corretto")
        self.assertFalse(invoice.get("client_name", "").startswith(":"), "Nome cliente inizia con ':'")

        # 5. Client Address: pulito senza la parola "Invoice" in coda
        client_address = invoice.get("client_address")
        self.assertIsNotNone(client_address, "Indirizzo cliente non estratto")
        self.assertEqual(client_address, "45 Canary Wharf, London, E14 5AB, UK", f"Indirizzo non corretto: '{client_address}'")
        self.assertFalse(client_address.endswith("Invoice"), "Indirizzo termina ancora con 'Invoice'")
        self.assertNotIn("Invoice", client_address, "Indirizzo contiene ancora 'Invoice'")

        # 6. Raccomandazioni 100% in lingua inglese
        recs = compliance.get("recommendations", [])
        self.assertTrue(len(recs) > 0, "Nessuna raccomandazione presente")
        expected_subset = [
            "Amount exceeds compliance threshold: authorization required.",
            "Notice level 3: consult legal counsel prior to formal escalation.",
            "Overdue exceeds 90 days: evaluate debt recovery or bad debt provisioning."
        ]
        for exp in expected_subset:
            self.assertIn(exp, recs, f"Raccomandazione EN attesa mancante: {exp}")

        for rec in recs:
            for it_frag in ["superiore alla soglia", "consultare un legale", "oltre 90 giorni"]:
                self.assertNotIn(it_frag, rec.lower(), f"Raccomandazione contiene testo italiano: {rec}")

        # 7. Verifica iniezione dinamica importo nel testo sollecito ($ 18,450.00 o EUR 18,450.00)
        self.assertTrue(
            "18,450.00" in reminder_text or "18450.00" in reminder_text,
            "Importo esatto non presente nel testo del sollecito"
        )

        print("\n===========================================================================")
        print("  VERIFICA PIPELINE v2.1.2 COMPLETATA CON SUCCESSO (100% CRITERI RISPETTATI):")
        print(f"  • Amount:       {invoice.get('amount')} ({invoice.get('currency')})")
        print(f"  • Days Overdue: {classification.get('days_overdue')}")
        print(f"  • Client Name:  '{invoice.get('client_name')}'")
        print(f"  • Client Addr:  '{client_address}' (Invoice RIMOSSA con successo)")
        print(f"  • Recs EN:      {recs}")
        print("===========================================================================")

if __name__ == "__main__":
    unittest.main()
