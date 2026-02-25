"""Tests for CatalogueParser.

Story 6-2, Task 5: Create catalogue parser.
"""

import json
import pytest

from teams.dawo.scanners.novel_food.parser import CatalogueParser, CatalogueParseError
from teams.dawo.scanners.novel_food.schemas import NovelFoodEntryRecord


class TestParseJsonResponse:
    """Tests for CatalogueParser.parse_json_response()."""

    def test_parse_valid_json(self, sample_json_response):
        """Test 11.2: parse valid JSON response."""
        parser = CatalogueParser()
        entries = parser.parse_json_response(sample_json_response, "Hericium erinaceus")
        assert len(entries) == 2
        assert all(isinstance(e, NovelFoodEntryRecord) for e in entries)

    def test_parse_json_species_latin_set(self, sample_json_response):
        parser = CatalogueParser()
        entries = parser.parse_json_response(sample_json_response, "Hericium erinaceus")
        assert all(e.species_latin == "Hericium erinaceus" for e in entries)

    def test_parse_json_entry_name_extracted(self, sample_json_response):
        parser = CatalogueParser()
        entries = parser.parse_json_response(sample_json_response, "Hericium erinaceus")
        names = [e.entry_name for e in entries]
        assert "Hericium erinaceus (Lion's Mane) - fruiting body" in names

    def test_parse_json_status_normalized(self, sample_json_response):
        """Test 11.6: normalizes status values correctly."""
        parser = CatalogueParser()
        entries = parser.parse_json_response(sample_json_response, "Hericium erinaceus")
        # "Yes" should normalize to "novel"
        assert entries[0].novel_food_status == "novel"

    def test_parse_json_empty_list(self):
        """Test 11.7: returns empty list for no results."""
        parser = CatalogueParser()
        entries = parser.parse_json_response(b"[]", "Nonexistent species")
        assert entries == []

    def test_parse_json_computes_hash(self, sample_json_response):
        parser = CatalogueParser()
        entries = parser.parse_json_response(sample_json_response, "Hericium erinaceus")
        assert all(e.raw_html_hash != "" for e in entries)
        assert len(entries[0].raw_html_hash) == 64  # SHA-256 hex


class TestParseHtmlResponse:
    """Tests for CatalogueParser.parse_html_response()."""

    def test_parse_valid_html(self, sample_html_response):
        """Test 11.3: parse valid HTML response."""
        parser = CatalogueParser()
        entries = parser.parse_html_response(sample_html_response, "Hericium erinaceus")
        assert len(entries) >= 1
        assert all(isinstance(e, NovelFoodEntryRecord) for e in entries)

    def test_parse_html_extracts_entry_name(self, sample_html_response):
        parser = CatalogueParser()
        entries = parser.parse_html_response(sample_html_response, "Hericium erinaceus")
        assert entries[0].entry_name == "Hericium erinaceus (Lion's Mane) - fruiting body"

    def test_parse_html_normalizes_status(self, sample_html_response):
        parser = CatalogueParser()
        entries = parser.parse_html_response(sample_html_response, "Hericium erinaceus")
        assert entries[0].novel_food_status == "novel"

    def test_parse_html_empty_result(self):
        parser = CatalogueParser()
        entries = parser.parse_html_response(
            b"<html><body></body></html>", "Nonexistent"
        )
        assert entries == []


class TestParserFallback:
    """Tests for JSON-to-HTML fallback behavior."""

    def test_parse_response_json_first(self, sample_json_response):
        """Test 11.4: fallback from JSON to HTML."""
        parser = CatalogueParser()
        entries = parser.parse_response(sample_json_response, "Hericium erinaceus")
        assert len(entries) == 2

    def test_parse_response_html_fallback(self, sample_html_response):
        parser = CatalogueParser()
        entries = parser.parse_response(sample_html_response, "Hericium erinaceus")
        assert len(entries) >= 1

    def test_parse_response_invalid_returns_empty(self):
        """Test 11.5: unexpected format returns empty list (BS4 parses leniently)."""
        parser = CatalogueParser()
        result = parser.parse_response(b"\x00\x01binary garbage", "Test")
        assert result == []


class TestStatusNormalization:
    """Tests for status value normalization."""

    def test_yes_to_novel(self):
        parser = CatalogueParser()
        assert parser._normalize_novel_food_status("Yes") == "novel"

    def test_no_to_not_novel(self):
        parser = CatalogueParser()
        assert parser._normalize_novel_food_status("No") == "not_novel"

    def test_not_determined(self):
        parser = CatalogueParser()
        assert parser._normalize_novel_food_status("Not determined") == "not_determined"

    def test_case_insensitive(self):
        parser = CatalogueParser()
        assert parser._normalize_novel_food_status("YES") == "novel"
        assert parser._normalize_novel_food_status("no") == "not_novel"

    def test_empty_to_not_determined(self):
        parser = CatalogueParser()
        assert parser._normalize_novel_food_status("") == "not_determined"
        assert parser._normalize_novel_food_status(None) == "not_determined"

    def test_ambiguous_value(self):
        parser = CatalogueParser()
        assert parser._normalize_novel_food_status("Ambiguous") == "ambiguous"


class TestCatalogueParseError:
    """Tests for CatalogueParseError."""

    def test_is_exception(self):
        assert issubclass(CatalogueParseError, Exception)

    def test_message(self):
        err = CatalogueParseError("parse failed: missing field")
        assert "parse failed" in str(err)
