"""
app/llm/client.py

LLM layer: calls OpenAI to extract structured FilingSignals from 10-K sections.
Enforces JSON output and retries on transient failures.
"""

from __future__ import annotations

import json
import logging
import time

from openai import OpenAI, APIError, RateLimitError

from app.config import settings
from app.llm.prompts import SYSTEM_PROMPT, build_extraction_prompt
from app.schemas import FilingMetadata, FilingSections, FilingSignals

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o"
_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 5


def _get_client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def extract_signals(
    metadata: FilingMetadata,
    sections: FilingSections,
) -> FilingSignals:
    """
    Call the LLM to extract structured FilingSignals from parsed 10-K sections.

    Args:
        metadata: Filing metadata (company, ticker, date, etc.)
        sections: Parsed text for Item 1A, Item 7, Item 7A.

    Returns:
        Validated FilingSignals instance.

    Raises:
        RuntimeError: if the LLM fails after all retries or returns invalid JSON.
    """
    prompt = build_extraction_prompt(
        company=metadata.company,
        ticker=metadata.ticker,
        filing_date=metadata.filing_date,
        item_1a=sections.item_1a,
        item_7=sections.item_7,
        item_7a=sections.item_7a,
    )

    client = _get_client()
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        logger.info(
            "LLM extraction attempt %d/%d for %s", attempt, _MAX_RETRIES, metadata.ticker
        )
        try:
            response = client.chat.completions.create(
                model=_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw_json = response.choices[0].message.content
            if not raw_json:
                raise ValueError("LLM returned an empty response.")

            logger.debug("Raw LLM response: %s", raw_json[:500])
            signals = FilingSignals.model_validate(json.loads(raw_json))
            logger.info("Successfully extracted signals for %s", metadata.ticker)
            return signals

        except (APIError, RateLimitError) as exc:
            logger.warning("OpenAI API error on attempt %d: %s", attempt, exc)
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)

        except (json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(
                f"LLM returned invalid JSON or schema mismatch for {metadata.ticker}: {exc}"
            ) from exc

    raise RuntimeError(
        f"LLM extraction failed for {metadata.ticker} after {_MAX_RETRIES} attempts: {last_exc}"
    )
