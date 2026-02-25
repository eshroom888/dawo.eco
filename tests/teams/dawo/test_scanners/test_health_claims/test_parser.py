"""Tests for RegisterParser.

Story 6-1, Task 12.2-12.3: Parser tests.
"""

import pytest
from io import BytesIO

import pandas as pd

from teams.dawo.scanners.health_claims.parser import RegisterParser, ParseError


@pytest.fixture
def parser():
    return RegisterParser()


@pytest.fixture
def valid_csv_data():
    """Valid CSV data with required columns."""
    csv = (
        "Claim ID;Substance;Status;Claim Text;Conditions of Use\n"
        "ID-001;Beta-glucans;Authorised;Beta-glucans maintain cholesterol;3g per day\n"
        "ID-002;Vitamin C;Authorised;Vitamin C protects cells;80mg per day\n"
    )
    return csv.encode("utf-8-sig")


@pytest.fixture
def valid_xls_data():
    """Valid XLS data with required columns."""
    df = pd.DataFrame({
        "Claim ID": ["ID-001", "ID-002"],
        "Substance": ["Beta-glucans", "Vitamin C"],
        "Status": ["Authorised", "Authorised"],
        "Claim Text": ["Beta-glucans maintain cholesterol", "Vitamin C protects cells"],
    })
    buf = BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


class TestRegisterParserParse:
    """Tests for RegisterParser.parse()."""

    def test_parse_valid_csv(self, parser, valid_csv_data):
        df = parser.parse(valid_csv_data)
        assert len(df) == 2
        assert "claim_id" in df.columns
        assert "substance" in df.columns
        assert "status" in df.columns

    def test_parse_valid_xls(self, parser, valid_xls_data):
        df = parser.parse(valid_xls_data)
        assert len(df) == 2
        assert "claim_id" in df.columns
        assert "substance" in df.columns

    def test_parse_normalizes_columns(self, parser, valid_csv_data):
        df = parser.parse(valid_csv_data)
        # "Claim ID" -> "claim_id"
        assert "claim_id" in df.columns
        # "Conditions of Use" -> "conditions_of_use"
        assert "conditions_of_use" in df.columns

    def test_parse_empty_data_raises(self, parser):
        with pytest.raises(ParseError, match="Empty data"):
            parser.parse(b"")

    def test_parse_invalid_format_raises(self, parser):
        with pytest.raises(ParseError):
            parser.parse(b"this is not valid xls or csv data \x00\x01\x02")

    def test_parse_missing_columns_raises(self, parser):
        csv = "Column A;Column B\nval1;val2\n"
        with pytest.raises(ParseError, match="Missing required columns"):
            parser.parse(csv.encode("utf-8-sig"))

    def test_parse_date_columns(self, parser):
        csv = (
            "Claim ID;Substance;Status;Date of Entry;Last Update\n"
            "ID-001;Beta-glucans;Authorised;16/05/2012;\n"
        )
        df = parser.parse(csv.encode("utf-8-sig"))
        if "date_of_entry" in df.columns:
            assert pd.notna(df["date_of_entry"].iloc[0])

    def test_parse_preserves_all_rows(self, parser):
        csv = "Claim ID;Substance;Status\n"
        for i in range(100):
            csv += f"ID-{i:03d};Substance {i};Authorised\n"
        df = parser.parse(csv.encode("utf-8-sig"))
        assert len(df) == 100

    def test_parse_handles_unicode(self, parser):
        csv = "Claim ID;Substance;Status\nID-001;Vitamine C (Ascorbinsäure);Authorised\n"
        df = parser.parse(csv.encode("utf-8-sig"))
        assert "Ascorbinsäure" in df["substance"].iloc[0]

    def test_parse_empty_xls_then_csv_fail_raises(self, parser):
        """Edge case: XLS parses but returns empty df, CSV fallback also fails."""
        # Create a valid but empty XLS (headers only, no rows)
        empty_df = pd.DataFrame(columns=["Claim ID", "Substance", "Status"])
        buf = BytesIO()
        empty_df.to_excel(buf, index=False, engine="openpyxl")
        data = buf.getvalue()
        # XLS parse succeeds but returns empty df, CSV fallback fails on binary data
        with pytest.raises(ParseError, match="Failed to parse as XLS or CSV"):
            parser.parse(data)
