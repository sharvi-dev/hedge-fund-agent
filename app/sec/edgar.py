"""
app/sec/edgar.py

Ingestion layer for SEC EDGAR:
- maps ticker -> CIK
- fetches company submissions JSON
- locates the latest 10-K filing metadata
"""

from __future__ import annotations

import logging
from functools import lru_cache

import requests

from app.config import settings
from app.schemas import FilingMetadata

logger = logging.getLogger(__name__)

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
REQUEST_TIMEOUT_SECONDS = 10


def _headers() -> dict[str, str]:
    return {"User-Agent": settings.sec_user_agent}


def _get_json(url: str) -> dict:
    """
    Perform a GET request to the SEC and return parsed JSON.

    Raises:
        RuntimeError: if the request fails or the response is not valid JSON.
    """
    try:
        response = requests.get(
            url,
            headers=_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch SEC data from {url}: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"Invalid JSON returned by SEC for {url}") from exc


@lru_cache(maxsize=1)
def _get_company_tickers() -> dict:
    """
    Fetch and cache the SEC company tickers index for the current process.
    """
    logger.info("Fetching SEC company tickers index")
    return _get_json(COMPANY_TICKERS_URL)


def get_cik(ticker: str) -> str:
    """
    Resolve a ticker symbol to its zero-padded 10-digit CIK.

    Args:
        ticker: Public company ticker symbol, e.g. 'NVDA'

    Returns:
        Zero-padded 10-digit CIK string.

    Raises:
        ValueError: if the ticker is not found in the SEC ticker index.
    """
    ticker_upper = ticker.upper()
    logger.info("Resolving CIK for ticker: %s", ticker_upper)

    data = _get_company_tickers()

    for entry in data.values():
        entry_ticker = str(entry.get("ticker", "")).upper()
        if entry_ticker == ticker_upper:
            cik = str(entry["cik_str"]).zfill(10)
            logger.info("Resolved ticker %s to CIK %s", ticker_upper, cik)
            return cik

    raise ValueError(f"Ticker '{ticker}' not found in SEC company tickers index.")


def get_submissions(cik: str) -> dict:
    """
    Fetch the submissions JSON for a given CIK.

    Args:
        cik: Zero-padded 10-digit CIK string.

    Returns:
        Raw submissions JSON as a dict.
    """
    url = SUBMISSIONS_URL.format(cik=cik)
    logger.info("Fetching submissions for CIK %s from %s", cik, url)
    return _get_json(url)


def get_latest_10k(ticker: str) -> FilingMetadata:
    """
    Return metadata for the most recent non-amended 10-K filing for a ticker.

    Notes:
        - This function matches only form == '10-K'
        - It intentionally excludes '10-K/A' amendments for the MVP
        - SEC recent filings are assumed to be ordered newest-first

    Args:
        ticker: Public company ticker symbol, e.g. 'NVDA'

    Returns:
        FilingMetadata for the latest 10-K.

    Raises:
        ValueError: if no 10-K is found for the ticker.
        RuntimeError: if SEC filings arrays are inconsistent.
    """
    cik = get_cik(ticker)
    submissions = get_submissions(cik)

    company_name = str(submissions.get("name", ticker.upper()))
    filings = submissions.get("filings", {}).get("recent", {})

    forms = filings.get("form", [])
    accession_numbers = filings.get("accessionNumber", [])
    filing_dates = filings.get("filingDate", [])
    primary_documents = filings.get("primaryDocument", [])

    _validate_recent_filings_shape(
        forms=forms,
        accession_numbers=accession_numbers,
        filing_dates=filing_dates,
        primary_documents=primary_documents,
    )

    for form, accession, filing_date, primary_document in zip(
        forms,
        accession_numbers,
        filing_dates,
        primary_documents,
    ):
        if form == "10-K":
            filing = FilingMetadata(
                ticker=ticker.upper(),
                company=company_name,
                cik=cik,
                filing_type=form,
                accession_number=accession,
                filing_date=filing_date,
                primary_document=primary_document,
                filing_index_url=_build_index_url(cik, accession),
                filing_document_url=_build_document_url(
                    cik=cik,
                    accession_number=accession,
                    primary_document=primary_document,
                ),
            )

            logger.info(
                "Latest 10-K for %s: filed %s, accession %s",
                filing.ticker,
                filing.filing_date,
                filing.accession_number,
            )
            return filing

    raise ValueError(f"No 10-K filing found for ticker '{ticker}' (CIK {cik}).")


def _validate_recent_filings_shape(
    *,
    forms: list[str],
    accession_numbers: list[str],
    filing_dates: list[str],
    primary_documents: list[str],
) -> None:
    """
    Ensure the SEC 'recent' filings arrays are aligned.

    Raises:
        RuntimeError: if the filings arrays have inconsistent lengths.
    """
    expected_length = len(forms)
    lengths = {
        "form": len(forms),
        "accessionNumber": len(accession_numbers),
        "filingDate": len(filing_dates),
        "primaryDocument": len(primary_documents),
    }

    if not all(length == expected_length for length in lengths.values()):
        raise RuntimeError(
            "SEC submissions 'recent' filing arrays have inconsistent lengths: "
            f"{lengths}"
        )


def _build_index_url(cik: str, accession_number: str) -> str:
    """
    Build the EDGAR filing index URL from CIK and accession number.

    Example:
        CIK:       0001045810
        Accession: 0001045810-26-000024
        URL:       https://www.sec.gov/Archives/edgar/data/1045810/000104581026000024/0001045810-26-000024-index.htm
    """
    accession_clean = accession_number.replace("-", "")
    cik_int = str(int(cik))
    return (
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/"
        f"{accession_clean}/{accession_number}-index.htm"
    )


def _build_document_url(
    *,
    cik: str,
    accession_number: str,
    primary_document: str,
) -> str:
    """
    Build the direct filing document URL from CIK, accession number, and primary document.

    Example:
        https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_clean}/{primary_document}
    """
    accession_clean = accession_number.replace("-", "")
    cik_int = str(int(cik))
    return (
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/"
        f"{accession_clean}/{primary_document}"
    )