"""
tests/test_parser.py

Tests for the deterministic 10-K section parser.
"""

import pytest

from app.sec.parser import parse_sections, _extract_text, _find_section_boundaries


def _make_filing(item_1a: str = "", item_7: str = "", item_7a: str = "", item_8: str = "") -> str:
    """Build a minimal HTML 10-K document with the given section bodies."""
    return f"""
    <html><body>
    <p>ITEM 1A. RISK FACTORS</p>
    <p>{item_1a}</p>
    <p>ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS</p>
    <p>{item_7}</p>
    <p>ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK</p>
    <p>{item_7a}</p>
    <p>ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA</p>
    <p>{item_8}</p>
    </body></html>
    """


class TestExtractText:
    def test_strips_html_tags(self):
        html = "<html><body><p>Hello <b>world</b></p></body></html>"
        text = _extract_text(html)
        assert "<" not in text
        assert "Hello" in text
        assert "world" in text

    def test_removes_script_and_style(self):
        html = "<html><body><script>alert(1)</script><style>body{}</style><p>content</p></body></html>"
        text = _extract_text(html)
        assert "alert" not in text
        assert "body{}" not in text
        assert "content" in text


class TestFindSectionBoundaries:
    def test_finds_all_sections(self):
        html = _make_filing(
            item_1a="We face export control risks. " * 20,
            item_7="Revenue increased significantly. " * 20,
            item_7a="Interest rate exposure is limited. " * 20,
        )
        text = _extract_text(html)
        boundaries = _find_section_boundaries(text)
        assert "item_1a" in boundaries
        assert "item_7" in boundaries
        assert "item_7a" in boundaries

    def test_boundaries_are_ordered(self):
        html = _make_filing(
            item_1a="Risk content here. " * 20,
            item_7="MD&A content here. " * 20,
            item_7a="Market risk content here. " * 20,
        )
        text = _extract_text(html)
        boundaries = _find_section_boundaries(text)
        assert boundaries["item_1a"] < boundaries["item_7"] < boundaries["item_7a"]


class TestParseSections:
    def test_parses_all_sections(self):
        html = _make_filing(
            item_1a="Export controls are a major risk for our business operations. " * 15,
            item_7="Our revenue grew 50% year over year driven by AI data centre demand. " * 15,
            item_7a="We are exposed to interest rate and foreign exchange risks. " * 15,
        )
        sections = parse_sections(html)
        assert "risk" in sections.item_1a.lower()
        assert "revenue" in sections.item_7.lower()
        assert "interest rate" in sections.item_7a.lower()

    def test_sections_do_not_bleed_into_each_other(self):
        html = _make_filing(
            item_1a="UNIQUE_RISK_TEXT " * 15,
            item_7="UNIQUE_MDA_TEXT " * 15,
            item_7a="UNIQUE_MARKET_RISK_TEXT " * 15,
        )
        sections = parse_sections(html)
        assert "UNIQUE_MDA_TEXT" not in sections.item_1a
        assert "UNIQUE_MARKET_RISK_TEXT" not in sections.item_7

    def test_raises_on_missing_section(self):
        html = "<html><body><p>No sections here.</p></body></html>"
        with pytest.raises(ValueError, match="Could not locate required sections"):
            parse_sections(html)
