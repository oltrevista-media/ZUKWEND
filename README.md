# ZUKWEND — Hybrid AR & Billing AI Agent

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20(64--bit)-blue.svg)](https://zukwend.com)
[![License](https://img.shields.io/badge/License-Lifetime%20(2%20Activations)-success.svg)](https://zukwend.com)
[![AI Architecture](https://img.shields.io/badge/AI%20Engine-3--Tier%20Native%20Out--of--the--Box-purple.svg)](https://zukwend.com)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline%20First-green.svg)](https://zukwend.com)
[![Ecosystem](https://img.shields.io/badge/Ecosystem-OLTREVISTA-orange.svg)](https://oltrevista.com)

**ZUKWEND** è l'agente desktop intelligente sviluppato per l'automazione dei processi di Accounts Receivable (AR), il monitoraggio dello scaduto commerciale, l'analisi dell'aging delle fatture e la generazione guidata di comunicazioni e solleciti professionali in 6 lingue.

Progettato per studi professionali, PMI, liberi professionisti e uffici finance, ZUKWEND garantisce totale riservatezza e sicurezza: i documenti e i dati contabili non lasciano mai la postazione di lavoro locale.

- **Sito Ufficiale Prodotto**: [https://zukwend.com](https://zukwend.com)
- **Holding Ecosystem**: [https://oltrevista.com](https://oltrevista.com)

---

## 🏛️ Architettura AI 3-Tier (Descrizione Tecnico-Commerciale)

ZUKWEND adotta un'architettura di calcolo ibrida e modulare a 3 livelli, studiata per offrire massima flessibilità operativa, indipendenza infrastrutturale e sovranità del dato:

### Level 1 — Built-in Native AI Agent (Included)
- **Operativo al 100% out-of-the-box subito dopo l'installazione.**
- **Zero configurazioni richieste, zero installazioni esterne, zero Ollama obbligatorio, zero chiavi API richieste per iniziare.**
- Il motore analitico e deduttivo integrato estrae i dati contabili da PDF e documenti, normalizza scadenze e anagrafiche, e genera bozze di sollecito strutturate multilivello in totale autonomia, anche a computer completamente disconnesso da internet.

### Level 2 — Local Ollama Power-Up (Optional)
- **Integrazione 1-click per modelli LLM locali estesi.**
- Connessione immediata a istanze locali di Ollama per eseguire modelli open-weights avanzati (*Gemma, Mistral, Qwen, DeepSeek*) direttamente sull'hardware della workstation.
- Massima privacy, controllo totale sui pesi dei modelli e calcolo 100% offline senza trasmissione di dati su server esterni.

### Level 3 — Cloud BYOC Power-Up (Optional)
- **Bring Your Own Keys (BYOC) per modelli Cloud di classe enterprise.**
- Connessione diretta e trasparente delle proprie API Key personali (*Anthropic Claude, OpenAI GPT-4o, Google Gemini, DeepSeek, Groq, Mistral EU GDPR*).
- Calcolo ad alte prestazioni con scalabilità istantanea e zero ricarico sui token di calcolo.

---

## 📁 Gerarchia Cartelle, Dossier Cliente & Multi-Valuta (v2.1.6)

ZUKWEND v2.1.6 introduce l'automazione dei **Dossier Cliente Consolidati** con logica **Anti-Data Leak** e supporto **Multi-Valuta**:

### 1. Raggruppamento Strict P.IVA (100% Match)
- Le posizioni aperte dello stesso debitore vengono consolidate in un unico dossier cliente **esclusivamente se la Partita IVA / Tax ID coincide al 100%**.
- Se la P.IVA manca o ha lunghezza insufficiente (< 5 caratteri), la fattura viene isolata in un dossier singolo autonomo per evitare contaminazioni tra debitori diversi.
- I caratteri speciali non ammessi da Windows (`/ \ : * ? " < > | &`) vengono automaticamente sanitizzati e la lunghezza del nome cartella è limitata a 40 caratteri.

### 2. Struttura Output
```
output/
├── CLIENTS/
│   └── {CLIENT_SLUG_VAT}/
│       └── {YYYY-MM-DD}/
│           ├── STATEMENT_OF_ACCOUNT_CONSOLIDATED.pdf  (Estratto conto unico con tabella analitica)
│           ├── REMINDER_EMAIL_CONSOLIDATED.txt        (E-mail unificata: OGGETTO + CORPO)
│           └── Individual_Invoices_Archive/           (Trittici .pdf, .xlsx, .json dei singoli titoli)
├── MASTER_SUMMARY_AGING_{YYYYMMDD}.xlsx               (Foglio 1: AR Aging Analysis | Foglio 2: ERP_Ingestion date ISO)
└── master_erp_ingestion_{YYYYMMDD}.json               (Batch payload per SAP, Zucchetti, TeamSystem)
```

### 3. Gestione Multi-Valuta Rigorosa
- Nell'Estratto Conto PDF e nell'e-mail di sollecito, le fatture in valute differenti (es. EUR, USD, GBP) vengono analiticamente elencate e sommate **esclusivamente in subtotali separati per valuta**.
- È matematicamente esclusa qualsiasi somma algebrica incrociata tra valute diverse.

### 4. Opzioni GUI nei Settings & Pulsanti Veloci
- Nei Settings della GUI sono disponibili i controlli per `dossier_mode` (default: Attivo) e `generate_individual_archive` (default: Attivo).
- Al completamento dell'analisi, il pannello inferiore espone 3 pulsanti veloci:
  - **[📄 Apri Estratto Conto]**: Apre istantaneamente `STATEMENT_OF_ACCOUNT_CONSOLIDATED.pdf`.
  - **[📊 Apri Master Excel]**: Apre `MASTER_SUMMARY_AGING_YYYYMMDD.xlsx`.
  - **[📁 Apri Cartella Output]**: Apre la cartella Windows del batch.

---

## 🛡️ Note Tecniche Windows Defender (SmartScreen)

Trattandosi di un software desktop nativo offline, distribuito tramite pacchetto autonomo e privo di telemetria cloud verso server centralizzati, al primo avvio su Windows 10/11 Microsoft Defender SmartScreen potrebbe mostrare la schermata informativa blu:

> **"PC protetto da Windows / App non riconosciuta"**  
> *(Windows protected your PC / Unrecognized app)*

### Procedura di avvio:
1. Cliccare sulla voce **"Ulteriori informazioni"** (o *"More info"*).
2. Cliccare sul pulsante **"Esegui comunque"** (o *"Run anyway"*).

ZUKWEND è sicuro al 100%: opera esclusivamente in locale sui documenti selezionati dall'utente, non installa servizi di background nascosti e non invia informazioni contabili all'esterno.

---

## 💳 Pricing & Licenze

| Piano | Prezzo | Condizioni |
| :--- | :--- | :--- |
| **Licenza a Vita (Lifetime License)** | **~~349 €~~ 249 € una tantum** | **[OFFERTA DI LANCIO — LICENZA A VITA]** (Pagamento unico una tantum. Zero abbonamenti). Zero costi ricorrenti, nessun canone o abbonamento mensile. Include **2 attivazioni con vincolo hardware** (Hardware-locked Machine ID) per workstation principale e laptop aziendale. |

- **Video Presentazione Ufficiale — Guarda come Funziona**: [https://youtu.be/a6V65LRN4oc](https://youtu.be/a6V65LRN4oc)
- Acquisto licenza: [https://zukwend.lemonsqueezy.com/checkout/buy/c6c7d5b7-7ee9-4717-a708-c386ad1d2344](https://zukwend.lemonsqueezy.com/checkout/buy/c6c7d5b7-7ee9-4717-a708-c386ad1d2344) (Portale: [https://zukwend.com](https://zukwend.com))

---

## 🌐 Struttura Multilingue & Portale Web

Il portale [zukwend.com](https://zukwend.com) offre landing page geolocalizzate e ottimizzate per ciascun mercato target:

| Lingua | Percorso Landing | Mercato / Focus |
| :--- | :--- | :--- |
| 🇮🇹 **Italiano** | `it-solleciti-fatture.html` | Solleciti di Pagamento & Gestione Crediti Commerciali |
| 🇩🇪 **Tedesco** | `de-mahnwesen-software.html` | Mahnwesen Software & Rechnungs-Mahnungen |
| 🇬🇧 **Inglese** | `en-invoice-reminder-software.html` / `index.html` | Autonomous Invoice Reminder & AR Agent |
| 🇪🇸 **Spagnolo** | `es-recordatorios-de-pago.html` | Recordatorios de Pago & Gestión de Cobranzas |
| 🇫🇷 **Francese** | `fr-relance-factures.html` | Logiciel de Relance Factures Impayées |
| 🇵🇹 **Portoghese** | `pt-lembrete-de-faturas.html` | Gestão de Cobrança e Lembretes de Faturas |

---

## 📋 Requisiti di Sistema

- **Sistema Operativo**: Windows 10 / Windows 11 (64-bit)
- **RAM**: 4 GB minimi (8 GB raccomandati per workflow intensivi; 16+ GB se si abilitano modelli Ollama locali estesi via Level 2)
- **Spazio su Disco**: ~150 MB (motore nativo Level 1 incluso)
- **Connessione Internet**: Non richiesta per l'operatività standard (Level 1 e Level 2 operano 100% offline)

---

## ⚖️ Note Legali, Licenza & Privacy (EULA)

ZUKWEND è un agente software desktop autonomo fornito "Così com'è" (As-Is) per l'automazione amministrativa, il tracciamento dei crediti insoluti e la predisposizione di bozze di sollecito. Non costituisce uno strumento di fatturazione elettronica attiva (non emette file XML per SDI/Agenzia delle Entrate) né un'agenzia di recupero crediti. Tutte le bozze generate devono essere verificate e approvate da personale qualificato prima della spedizione.

- **Termini di Licenza & EULA:** [https://zukwend.com/DISCLAIMER_EULA.html](https://zukwend.com/DISCLAIMER_EULA.html)
- **Privacy Policy (Local-First):** [https://zukwend.com/DISCLAIMER_EULA.html#privacy](https://zukwend.com/DISCLAIMER_EULA.html#privacy)
- **Contatti Ufficiali & Licenze:** contact@oltrevista.com *(destinato esclusivamente a quesiti amministrativi e licenze commerciali per il software autonomo desktop fornito As-Is)*

---
© 2026 **OLTREVISTA** — [oltrevista.com](https://oltrevista.com). Tutti i diritti riservati.
