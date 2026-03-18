"""
app/pipeline/run_filing_pipeline.py

Orchestrates the end-to-end 10-K pipeline:
  1. Fetch latest 10-K metadata from SEC EDGAR
  2. Download the filing HTML
  3. Parse Item 1A, Item 7, Item 7A
  4. Extract structured signals via LLM
  5. Save JSON output to data/processed/

Usage:
    python -m app.pipeline.run_filing_pipeline --ticker NVDA
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.llm.client import extract_signals
from app.sec.edgar import get_latest_10k
from app.sec.filings import download_filing
from app.sec.parser import parse_sections
from app.storage.io import load_raw_filing, save_processed_signals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_pipeline(ticker: str) -> None:
    """
    Execute the full filing pipeline for one ticker.

    Args:
        ticker: Public company ticker symbol, e.g. 'NVDA'.
    """
    logger.info("=== Pipeline start: %s ===", ticker.upper())

    # Step 1: Fetch filing metadata
    logger.info("[1/5] Fetching latest 10-K metadata for %s", ticker)
    metadata = get_latest_10k(ticker)
    logger.info(
        "Found 10-K: %s filed %s (accession %s)",
        metadata.company,
        metadata.filing_date,
        metadata.accession_number,
    )

    # Step 2: Download filing HTML (skip if already cached locally)
    logger.info("[2/5] Downloading filing HTML")
    try:
        html = load_raw_filing(metadata.ticker, metadata.accession_number)
        logger.info("Using cached raw filing from disk")
    except FileNotFoundError:
        download_filing(metadata)
        html = load_raw_filing(metadata.ticker, metadata.accession_number)

    # Step 3: Parse sections
    logger.info("[3/5] Parsing Item 1A, Item 7, Item 7A")
    sections = parse_sections(html)

    # Step 4: LLM extraction
    logger.info("[4/5] Running LLM extraction")
    signals = extract_signals(metadata, sections)

    # Step 5: Save output
    logger.info("[5/5] Saving structured signals")
    output_path = save_processed_signals(signals)

    logger.info("=== Pipeline complete: %s ===", ticker.upper())
    logger.info("Output → %s", output_path)
    print(signals.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the 10-K filing pipeline for a given ticker."
    )
    parser.add_argument(
        "--ticker",
        required=True,
        type=str,
        help="Stock ticker symbol, e.g. NVDA",
    )
    args = parser.parse_args()

    try:
        run_pipeline(args.ticker)
    except (ValueError, RuntimeError) as exc:
        logger.error("Pipeline failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
