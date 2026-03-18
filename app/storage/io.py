"""
app/storage/io.py

Storage layer: save and load raw filings and processed JSON outputs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.schemas import FilingSignals

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


def _ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def save_raw_filing(ticker: str, accession_number: str, content: str) -> Path:
    """
    Save raw HTML/text filing content to data/raw/.

    Returns:
        Path to the saved file.
    """
    _ensure_dirs()
    accession_clean = accession_number.replace("-", "")
    filename = f"{ticker.upper()}_{accession_clean}.html"
    path = RAW_DIR / filename
    path.write_text(content, encoding="utf-8")
    logger.info("Saved raw filing to %s", path)
    return path


def save_processed_signals(signals: FilingSignals) -> Path:
    """
    Save structured FilingSignals as JSON to data/processed/.

    Returns:
        Path to the saved file.
    """
    _ensure_dirs()
    filename = f"{signals.ticker}_{signals.filing_date}.json"
    path = PROCESSED_DIR / filename
    path.write_text(signals.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Saved processed signals to %s", path)
    return path


def load_raw_filing(ticker: str, accession_number: str) -> str:
    """
    Load a previously saved raw filing from data/raw/.

    Raises:
        FileNotFoundError: if the file does not exist.
    """
    accession_clean = accession_number.replace("-", "")
    filename = f"{ticker.upper()}_{accession_clean}.html"
    path = RAW_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Raw filing not found: {path}")
    return path.read_text(encoding="utf-8")


def load_processed_signals(ticker: str, filing_date: str) -> FilingSignals:
    """
    Load a previously saved FilingSignals JSON from data/processed/.

    Raises:
        FileNotFoundError: if the file does not exist.
    """
    filename = f"{ticker.upper()}_{filing_date}.json"
    path = PROCESSED_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Processed signals not found: {path}")
    return FilingSignals.model_validate(json.loads(path.read_text(encoding="utf-8")))
