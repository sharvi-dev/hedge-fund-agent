"""
app/schemas.py

All Pydantic schemas for the hedge-fund-agent pipeline.
"""

from typing import List

from pydantic import BaseModel


class FilingMetadata(BaseModel):
    """Metadata returned by the EDGAR ingestion layer."""

    ticker: str
    company: str
    cik: str
    filing_type: str
    accession_number: str
    filing_date: str
    primary_document: str
    filing_index_url: str
    filing_document_url: str


class FilingSections(BaseModel):
    """Raw text extracted from key 10-K sections by the parser."""

    item_1a: str  # Risk Factors
    item_7: str   # MD&A
    item_7a: str  # Quantitative and Qualitative Disclosures About Market Risk


class FilingSignals(BaseModel):
    """Structured signals extracted by the LLM from a 10-K filing."""

    company: str
    ticker: str
    filing_type: str
    filing_date: str
    risk_themes: List[str]
    growth_drivers: List[str]
    uncertainty_score: float
    management_tone: str
    margin_pressure: bool
    capex_expansion: bool
    citations: List[str]
