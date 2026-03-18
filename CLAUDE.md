# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

---

# 🧠 Project Overview

`hedge-fund-agent` is an AI-powered financial document intelligence system designed for hedge fund workflows.

The system ingests SEC filings (10-K, 10-Q), earnings call transcripts, and financial data, then:

- extracts structured insights using LLMs
- detects changes across filings over time
- generates machine-readable signals
- produces analyst-ready outputs
- enables downstream quant research and backtesting

⚠️ This is NOT a chatbot. This is a **production-style research pipeline**.

---

# 🎯 Core MVP Goal

Build a pipeline that:

1. Fetches the latest 10-K for a ticker
2. Parses key sections (Item 1A, Item 7, Item 7A)
3. Extracts structured signals using an LLM
4. Saves outputs as JSON for research use

---

# 🏗️ Architecture Overview

The system is a **multi-stage pipeline**, not a monolithic agent.

## High-Level Flow

External Data → Ingestion → Raw Storage → Parsing → Structured Sections → LLM Extraction → Signals → Storage → Interfaces

---

## End-to-End Pipeline

1. Fetch SEC filing metadata
2. Download filing HTML/text
3. Save raw document
4. Parse into sections (Item 1A, 7, 7A)
5. Normalize text
6. Run LLM extraction
7. Generate structured signals
8. Save processed output

---

# 📁 Repository Structure (Required)

```text
hedge-fund-agent/
├── README.md
├── CLAUDE.md
├── .env.example
├── .gitignore
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── sec/
│   │   ├── __init__.py
│   │   ├── edgar.py
│   │   ├── filings.py
│   │   └── parser.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── prompts.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── run_filing_pipeline.py
│   └── storage/
│       ├── __init__.py
│       └── io.py
├── data/
│   ├── raw/
│   └── processed/
└── tests/

---

## Modules

### 1. Ingestion Layer (`app/sec/`)
Responsible for fetching filings from SEC EDGAR.

- `edgar.py`
  - ticker → CIK mapping
  - fetch submissions JSON
  - locate latest filing

- `filings.py`
  - download filing HTML/text
  - store raw files

---

### 2. Parsing Layer (`app/sec/parser.py`)

Extract structured sections:

- Item 1A (Risk Factors)
- Item 7 (MD&A)
- Item 7A (Market Risk)

⚠️ Must use semantic section parsing, NOT naive chunking.

---

### 3. LLM Layer (`app/llm/`)

- `client.py`
  - interface to OpenAI / Claude
  - structured output generation

- `prompts.py`
  - extraction prompts
  - strict schema outputs

⚠️ Always return structured JSON, not free text.

---

### 4. Pipeline Layer (`app/pipeline/`)

- `run_filing_pipeline.py`

Orchestrates:
1. fetch filing
2. parse sections
3. call LLM
4. save results

---

### 5. Storage Layer (`app/storage/`)

- raw filings → `data/raw/`
- processed outputs → `data/processed/`

Later:
- Postgres (structured data)
- vector DB (retrieval)

---

### 6. Schema Layer (`app/schemas.py`)

Defines structured outputs using Pydantic.

Example:

```python
class FilingSignals(BaseModel):
    ticker: str
    filing_date: str
    risk_themes: List[str]
    growth_drivers: List[str]
    uncertainty_score: float
    management_tone: str