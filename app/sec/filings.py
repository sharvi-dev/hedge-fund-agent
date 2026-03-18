"""
app/sec/filings.py

Filing retrieval layer: downloads the primary HTML document for a 10-K filing
and stores it locally in data/raw/.
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from app.config import settings
from app.schemas import FilingMetadata
from app.storage.io import save_raw_filing

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 30


def download_filing(metadata: FilingMetadata) -> Path:
    """
    Download the primary HTML document for a filing and save it to data/raw/.

    Args:
        metadata: FilingMetadata returned by edgar.get_latest_10k().

    Returns:
        Path to the saved raw HTML file.

    Raises:
        RuntimeError: if the download fails.
    """
    url = metadata.filing_document_url
    logger.info(
        "Downloading filing for %s from %s", metadata.ticker, url
    )

    try:
        response = requests.get(
            url,
            headers={"User-Agent": settings.sec_user_agent},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to download filing for {metadata.ticker} from {url}: {exc}"
        ) from exc

    content = response.text
    path = save_raw_filing(
        ticker=metadata.ticker,
        accession_number=metadata.accession_number,
        content=content,
    )
    logger.info(
        "Filing for %s saved (%d bytes) → %s",
        metadata.ticker,
        len(content),
        path,
    )
    return path
