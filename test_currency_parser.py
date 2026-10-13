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

    def test_03_full_pipeline_verification(self):
        """Azione 3: Esecuzione pipeline completa su b2b_invoice_sample_en.pdf e verifica requisiti 100%."""
        result = workflow_engine.run_pipeline(str(self.pdf_path), language="en", mode="local")
        self.assertTrue(result.success, f"Pipeline fallita con errori: {result.errors}")

        invoice = result.invoice
        classification = result.classification
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

        # 4. Client Name: "Global Logistics Solutions Ltd." (senza ':' iniziale)
        self.assertEqual(invoice.get("client_name"), "Global Logistics Solutions Ltd.", "Nome cliente estratto non corretto")
        self.assertFalse(invoice.get("client_name", "").startswith(":"), "Nome cliente inizia con ':'")

        # 5. Verifica iniezione dinamica importo nel testo sollecito ($ 18,450.00 o EUR 18,450.00)
        self.assertTrue(
            "18,450.00" in reminder_text or "18450.00" in reminder_text,
            "Importo esatto non presente nel testo del sollecito"
        )

        print("\n===========================================================================")
        print("  VERIFICA PIPELINE COMPLETATA CON SUCCESSO (100% CRITERI RISPETTATI):")
        print(f"  • Amount:       {invoice.get('amount')} ({invoice.get('currency')})")
        print(f"  • Days Overdue: {classification.get('days_overdue')}")
        print(f"  • Client Name:  '{invoice.get('client_name')}'")
        print(f"  • Notice Match: 'overdue by 126 days' confermato (0 days ASSENTE)")
        print("===========================================================================")

if __name__ == "__main__":
    unittest.main()
