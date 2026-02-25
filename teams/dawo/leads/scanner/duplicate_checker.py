"""Lead Duplicate Checker for B2B Lead Research Scanner.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Checks transformed leads against existing database records
to prevent duplicates.
"""

import logging
from typing import Protocol, Optional
from uuid import UUID
from difflib import SequenceMatcher

from teams.dawo.leads.scanner.schemas import TransformedLead


logger = logging.getLogger(__name__)


# Duplicate detection constants
COMPANY_MATCH_THRESHOLD = 0.9  # 90% similarity for fuzzy company match
COMPANY_SUFFIXES = ["as", "ab", "aps", "oy", "ltd", "inc", "gmbh", "sa", "ag"]


class LeadRepositoryProtocol(Protocol):
    """Protocol for lead repository dependency."""

    async def get_lead_by_email(self, email: str) -> Optional[object]:
        """Get lead by email address."""
        ...

    async def get_leads_by_company(
        self,
        company: str,
        country: Optional[str] = None,
    ) -> list[object]:
        """Get leads by company name."""
        ...


class LeadDuplicateChecker:
    """Checks for duplicate leads in the database.

    Performs deduplication using:
    1. Exact email match (primary check)
    2. Fuzzy company name + country match (secondary check)

    Accepts repository via dependency injection.
    """

    def __init__(
        self,
        repository: LeadRepositoryProtocol,
        match_threshold: float = COMPANY_MATCH_THRESHOLD,
    ) -> None:
        """Initialize the duplicate checker.

        Args:
            repository: Lead repository for database queries
            match_threshold: Similarity threshold for fuzzy matching (0-1)
        """
        self._repository = repository
        self._match_threshold = match_threshold

    async def check_duplicates(
        self,
        leads: list[TransformedLead],
    ) -> list[TransformedLead]:
        """Filter out leads that already exist in database.

        Args:
            leads: List of transformed leads to check

        Returns:
            List of non-duplicate leads
        """
        logger.info(f"Checking {len(leads)} leads for duplicates")

        non_duplicates: list[TransformedLead] = []
        seen_emails: set[str] = set()  # Track emails in current batch
        duplicates_found = 0

        for lead in leads:
            # Check within current batch first
            email_lower = lead.email.lower()
            if email_lower in seen_emails:
                logger.debug(f"Duplicate in batch: {lead.email}")
                duplicates_found += 1
                continue

            # Check against database
            is_duplicate = await self._is_duplicate(lead)
            if is_duplicate:
                logger.debug(f"Duplicate in database: {lead.email}")
                duplicates_found += 1
                continue

            # Not a duplicate
            non_duplicates.append(lead)
            seen_emails.add(email_lower)

        logger.info(
            f"Duplicate check complete: "
            f"{len(non_duplicates)} unique, {duplicates_found} duplicates"
        )

        return non_duplicates

    async def _is_duplicate(self, lead: TransformedLead) -> bool:
        """Check if a single lead is a duplicate.

        Args:
            lead: Lead to check

        Returns:
            True if duplicate found, False otherwise
        """
        # Check exact email match first (most reliable)
        existing_by_email = await self._repository.get_lead_by_email(lead.email)
        if existing_by_email:
            return True

        # Check fuzzy company match
        # This catches cases where the same company has different emails
        normalized_company = self._normalize_company(lead.company)
        existing_by_company = await self._repository.get_leads_by_company(
            lead.company,
            lead.country,
        )

        for existing in existing_by_company:
            existing_company = self._normalize_company(
                getattr(existing, "company", "")
            )
            similarity = self._calculate_similarity(
                normalized_company,
                existing_company,
            )
            if similarity >= self._match_threshold:
                logger.debug(
                    f"Fuzzy match: {lead.company} ~ {existing_company} "
                    f"(similarity: {similarity:.2f})"
                )
                return True

        return False

    def _normalize_company(self, name: str) -> str:
        """Normalize company name for comparison.

        Removes common suffixes and normalizes case/whitespace.

        Args:
            name: Company name to normalize

        Returns:
            Normalized company name
        """
        if not name:
            return ""

        # Lowercase and strip
        normalized = name.lower().strip()

        # Remove common company suffixes
        for suffix in COMPANY_SUFFIXES:
            # Check with and without space
            for pattern in [f" {suffix}", f" {suffix}."]:
                if normalized.endswith(pattern):
                    normalized = normalized[: -len(pattern)]

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings.

        Uses SequenceMatcher for fuzzy matching.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity ratio (0-1)
        """
        if not str1 or not str2:
            return 0.0

        return SequenceMatcher(None, str1, str2).ratio()
