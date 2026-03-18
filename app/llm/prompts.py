"""
app/llm/prompts.py

Prompt templates for LLM-based extraction from 10-K sections.
All prompts demand structured JSON output matching FilingSignals.
"""

SYSTEM_PROMPT = """\
You are a financial analyst AI that extracts structured signals from SEC 10-K filings.
You MUST respond with valid JSON only — no prose, no markdown, no explanation.
Your JSON must exactly match the schema provided in the user message.
"""

EXTRACTION_PROMPT_TEMPLATE = """\
Extract structured signals from the following 10-K filing sections.

## Company
{company} ({ticker})

## Filing Date
{filing_date}

## Item 1A — Risk Factors
{item_1a}

## Item 7 — MD&A
{item_7}

## Item 7A — Market Risk
{item_7a}

---

Respond ONLY with a JSON object that matches this exact schema:

{{
  "company": "<string — full company name>",
  "ticker": "<string — ticker symbol>",
  "filing_type": "10-K",
  "filing_date": "<string — YYYY-MM-DD>",
  "risk_themes": ["<list of concise risk theme strings, max 10>"],
  "growth_drivers": ["<list of concise growth driver strings, max 10>"],
  "uncertainty_score": <float between 0.0 (low uncertainty) and 1.0 (high uncertainty)>,
  "management_tone": "<string — one of: positive, cautious, positive but cautious, negative, neutral>",
  "margin_pressure": <true | false>,
  "capex_expansion": <true | false>,
  "citations": ["<list of section references, e.g. Item 1A, Item 7>"]
}}

Rules:
- Base every field on evidence in the provided text.
- uncertainty_score should reflect hedging language, forward-looking disclaimers, and risk density.
- margin_pressure = true if management discusses cost increases, pricing pressure, or declining margins.
- capex_expansion = true if management signals increased capital expenditure or capacity investment.
- citations must reference only the sections that contributed to each signal.
- Do NOT invent facts not present in the text.
"""


def build_extraction_prompt(
    *,
    company: str,
    ticker: str,
    filing_date: str,
    item_1a: str,
    item_7: str,
    item_7a: str,
) -> str:
    """Render the extraction prompt with filing-specific values."""
    return EXTRACTION_PROMPT_TEMPLATE.format(
        company=company,
        ticker=ticker,
        filing_date=filing_date,
        item_1a=item_1a[:8000],   # truncate to stay within context limits
        item_7=item_7[:8000],
        item_7a=item_7a[:4000],
    )
