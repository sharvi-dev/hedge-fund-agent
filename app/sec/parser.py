"""
app/sec/parser.py

Parsing layer: deterministically extracts Item 1A, Item 7, and Item 7A
from a 10-K HTML filing using BeautifulSoup + regex.

Strategy:
  1. Parse HTML with BeautifulSoup, extracting visible text.
  2. Locate section boundaries using regex anchored to SEC item headings.
  3. Slice text between consecutive boundaries to isolate each section.

This module never calls an LLM.
"""

from __future__ import annotations

import logging
import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from app.schemas import FilingSections

logger = logging.getLogger(__name__)

# Regex patterns that match the start of each target section heading.
# They are intentionally liberal to handle variations in formatting.
_ITEM_PATTERNS: list[tuple[str, str]] = [
    ("item_1a", r"item\s+1a[\.\s\u2014\-–:]*\s*risk\s+factors"),
    ("item_7",  r"item\s+7[\.\s\u2014\-–:]*\s*management[\u2019']?s?\s+discussion"),
    ("item_7a", r"item\s+7a[\.\s\u2014\-–:]*\s*quantitative"),
    # Sentinel to mark the end of Item 7A — typically Item 8
    ("item_8",  r"item\s+8[\.\s\u2014\-–:]*\s*financial\s+statements"),
]

# Minimum character threshold — headings that appear in the table of contents
# are typically very short. We skip matches whose trailing text is too thin.
_MIN_SECTION_CHARS = 200


def _extract_text(html: str) -> str:
    """Strip HTML tags and return normalised plain text."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "lxml")
    # Remove script / style noise
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse excessive whitespace while preserving paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _find_section_boundaries(text: str) -> dict[str, int]:
    """
    Return the character offset of each section, enforcing document order.

    Strategy: search backwards from the end of the document.
    For each section (processed in reverse order), take the last match
    that appears *before* the next section's chosen position.
    This correctly skips table-of-contents entries, which appear early in
    the document, and lands on the actual body headings.
    """
    boundaries: dict[str, int] = {}
    text_lower = text.lower()

    # Collect all qualifying matches per section up front
    all_matches: dict[str, list] = {}
    for name, pattern in _ITEM_PATTERNS:
        all_matches[name] = [
            m for m in re.finditer(pattern, text_lower)
            if len(text) - m.start() > _MIN_SECTION_CHARS
        ]

    # Walk sections in reverse; each must appear before the next section
    names = [name for name, _ in _ITEM_PATTERNS]
    max_offset = len(text)

    for name in reversed(names):
        candidates = [m for m in all_matches[name] if m.start() < max_offset]
        if candidates:
            chosen = candidates[-1]  # last match before the next section
            boundaries[name] = chosen.start()
            max_offset = chosen.start()
            logger.debug("Found %s at offset %d", name, chosen.start())
        else:
            logger.warning("Section '%s' not found in document", name)

    return boundaries


def parse_sections(html: str) -> FilingSections:
    """
    Extract Item 1A, Item 7, and Item 7A from a 10-K HTML filing.

    Args:
        html: Raw HTML content of the filing.

    Returns:
        FilingSections with the text of each section.

    Raises:
        ValueError: if any required section cannot be located.
    """
    logger.info("Parsing 10-K sections from HTML (%d chars)", len(html))
    text = _extract_text(html)
    boundaries = _find_section_boundaries(text)

    missing = [k for k in ("item_1a", "item_7", "item_7a") if k not in boundaries]
    if missing:
        raise ValueError(
            f"Could not locate required sections in filing: {missing}. "
            "The filing may use non-standard formatting."
        )

    def _slice(start_key: str, end_key: str) -> str:
        start = boundaries[start_key]
        end = boundaries.get(end_key)
        chunk = text[start:end].strip() if end else text[start:].strip()
        return chunk

    sections = FilingSections(
        item_1a=_slice("item_1a", "item_7"),
        item_7=_slice("item_7", "item_7a"),
        item_7a=_slice("item_7a", "item_8"),
    )

    logger.info(
        "Parsed sections — 1A: %d chars, 7: %d chars, 7A: %d chars",
        len(sections.item_1a),
        len(sections.item_7),
        len(sections.item_7a),
    )
    return sections
