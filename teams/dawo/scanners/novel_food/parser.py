"""Novel Food Catalogue parser.

Epic 6, Story 6-2, Task 5: Catalogue parser.

Parses JSON or HTML responses from the EU Food & Feed Portal
into NovelFoodEntryRecord DTOs. Tries JSON first, falls back to HTML.
"""

import hashlib
import json
import logging
from typing import Optional

from bs4 import BeautifulSoup, Tag

from teams.dawo.scanners.novel_food.schemas import NovelFoodEntryRecord

logger = logging.getLogger(__name__)


class CatalogueParseError(Exception):
    """Raised when catalogue response cannot be parsed."""


# Status normalization maps
_NOVEL_FOOD_STATUS_MAP = {
    "yes": "novel",
    "no": "not_novel",
    "not determined": "not_determined",
    "not yet determined": "not_determined",
    "ambiguous": "ambiguous",
}

_AUTHORIZATION_STATUS_MAP = {
    "authorised": "authorised",
    "authorized": "authorised",
    "not authorised": "not_authorised",
    "not authorized": "not_authorised",
    "pending": "pending",
    "not applicable": "not_applicable",
    "n/a": "not_applicable",
}


class CatalogueParser:
    """Parser for EU Novel Food Catalogue responses.

    Story 6-2, Task 5: Parse JSON or HTML responses.

    Tries JSON parsing first. If the response is not valid JSON,
    falls back to HTML parsing with BeautifulSoup.

    Normalizes status values to enum-compatible strings.
    Computes SHA-256 hash of raw response bytes per entry.
    """

    def parse_response(
        self, data: bytes, species_latin: str
    ) -> list[NovelFoodEntryRecord]:
        """Parse response, trying JSON first then HTML fallback.

        Args:
            data: Raw response bytes
            species_latin: Latin species name for the query

        Returns:
            List of parsed entry records

        Raises:
            CatalogueParseError: If neither JSON nor HTML parsing succeeds
        """
        # Try JSON first
        try:
            return self.parse_json_response(data, species_latin)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(
                "JSON parse failed for '%s', trying HTML fallback: %s",
                species_latin,
                e,
            )

        # Try HTML fallback
        try:
            entries = self.parse_html_response(data, species_latin)
        except Exception as e:
            logger.error(
                "Failed to parse response for '%s': %s",
                species_latin,
                e,
            )
            raise CatalogueParseError(
                f"Failed to parse response for '{species_latin}': {e}"
            ) from e

        # Zero entries may be expected for some species (Task 5.9)
        if not entries:
            logger.warning(
                "No entries found for species '%s' after JSON+HTML parsing (%d bytes)",
                species_latin,
                len(data),
            )
        return entries

    def parse_json_response(
        self, data: bytes, species_latin: str
    ) -> list[NovelFoodEntryRecord]:
        """Parse backend JSON response.

        Args:
            data: Raw JSON bytes
            species_latin: Latin species name

        Returns:
            List of NovelFoodEntryRecord
        """
        items = json.loads(data)
        if not isinstance(items, list):
            raise CatalogueParseError(f"Expected JSON array, got {type(items).__name__}")

        entries: list[NovelFoodEntryRecord] = []
        for item in items:
            entry_hash = hashlib.sha256(
                json.dumps(item, sort_keys=True).encode("utf-8")
            ).hexdigest()

            entry = NovelFoodEntryRecord(
                species_latin=species_latin,
                entry_name=item.get("name", ""),
                novel_food_status=self._normalize_novel_food_status(
                    item.get("novelFoodStatus")
                ),
                authorization_status=self._normalize_authorization_status(
                    item.get("authorisationStatus")
                ),
                history_of_consumption=item.get("historyOfConsumption") or "",
                member_state_comments=item.get("memberStateComments") or "",
                commission_comments=item.get("commissionComments") or "",
                conditions_of_use=item.get("conditionsOfUse") or "",
                regulation_reference=item.get("regulationReference") or "",
                union_list_entry=item.get("unionListEntry") or "",
                raw_html_hash=entry_hash,
            )
            entries.append(entry)

        if not entries:
            logger.warning(
                "No entries found for species '%s' in JSON response",
                species_latin,
            )

        return entries

    def parse_html_response(
        self, data: bytes, species_latin: str
    ) -> list[NovelFoodEntryRecord]:
        """Parse HTML search page response with BeautifulSoup.

        Args:
            data: Raw HTML bytes
            species_latin: Latin species name

        Returns:
            List of NovelFoodEntryRecord
        """
        soup = BeautifulSoup(data, "lxml")
        result_items = soup.select(".search-result-item")

        entries: list[NovelFoodEntryRecord] = []
        for item in result_items:
            entry_hash = hashlib.sha256(str(item).encode("utf-8")).hexdigest()

            entry_name = ""
            h3 = item.select_one("h3")
            if h3:
                entry_name = h3.get_text(strip=True)

            entry = NovelFoodEntryRecord(
                species_latin=species_latin,
                entry_name=entry_name,
                novel_food_status=self._normalize_novel_food_status(
                    self._extract_field(item, ".field-novel-food-status")
                ),
                authorization_status=self._normalize_authorization_status(
                    self._extract_field(item, ".field-authorisation-status")
                ),
                history_of_consumption=self._extract_field(item, ".field-history"),
                member_state_comments=self._extract_field(item, ".field-member-state"),
                commission_comments=self._extract_field(item, ".field-commission"),
                conditions_of_use=self._extract_field(item, ".field-conditions"),
                regulation_reference=self._extract_field(item, ".field-regulation"),
                union_list_entry=self._extract_field(item, ".field-union-list"),
                raw_html_hash=entry_hash,
            )
            entries.append(entry)

        if not entries:
            logger.warning(
                "No entries found for species '%s' in HTML response",
                species_latin,
            )

        return entries

    def _extract_field(self, item: "Tag", selector: str) -> str:
        """Extract text from an HTML element by CSS selector."""
        el = item.select_one(selector)
        return el.get_text(strip=True) if el else ""

    def _normalize_novel_food_status(self, value: Optional[str]) -> str:
        """Normalize novel food status to enum-compatible string.

        Args:
            value: Raw status string from API/HTML

        Returns:
            Normalized status string
        """
        if not value:
            return "not_determined"
        return _NOVEL_FOOD_STATUS_MAP.get(value.strip().lower(), "not_determined")

    def _normalize_authorization_status(self, value: Optional[str]) -> str:
        """Normalize authorization status to enum-compatible string.

        Args:
            value: Raw authorization string from API/HTML

        Returns:
            Normalized authorization status string
        """
        if not value:
            return "not_applicable"
        return _AUTHORIZATION_STATUS_MAP.get(value.strip().lower(), "not_applicable")


__all__ = [
    "CatalogueParser",
    "CatalogueParseError",
]
