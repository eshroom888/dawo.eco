"""Tests for LeadDuplicateChecker.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.leads.scanner.duplicate_checker import LeadDuplicateChecker
from teams.dawo.leads.scanner.schemas import TransformedLead


class TestLeadDuplicateChecker:
    """Tests for LeadDuplicateChecker service."""

    @pytest.fixture
    def checker(
        self,
        mock_lead_repository: AsyncMock,
    ) -> LeadDuplicateChecker:
        """Create checker with mocked repository."""
        return LeadDuplicateChecker(
            repository=mock_lead_repository,
            match_threshold=0.9,
        )

    @pytest.mark.asyncio
    async def test_check_duplicates_filters_existing_emails(
        self,
        checker: LeadDuplicateChecker,
        sample_transformed_leads: list[TransformedLead],
        mock_lead_repository: AsyncMock,
    ) -> None:
        """Test that leads with existing emails are filtered."""
        # First lead's email already exists
        mock_lead_repository.get_lead_by_email.side_effect = [
            MagicMock(),  # First lead exists
            None,  # Second lead doesn't exist
        ]

        result = await checker.check_duplicates(sample_transformed_leads)

        assert len(result) == 1  # Only second lead

    @pytest.mark.asyncio
    async def test_check_duplicates_allows_new_emails(
        self,
        checker: LeadDuplicateChecker,
        sample_transformed_leads: list[TransformedLead],
        mock_lead_repository: AsyncMock,
    ) -> None:
        """Test that new emails pass through."""
        # No existing leads
        mock_lead_repository.get_lead_by_email.return_value = None
        mock_lead_repository.get_leads_by_company.return_value = []

        result = await checker.check_duplicates(sample_transformed_leads)

        assert len(result) == len(sample_transformed_leads)

    @pytest.mark.asyncio
    async def test_check_duplicates_filters_fuzzy_company_match(
        self,
        checker: LeadDuplicateChecker,
        mock_lead_repository: AsyncMock,
    ) -> None:
        """Test that similar company names are detected as duplicates."""
        lead = TransformedLead(
            email="new@example.no",
            first_name="New",
            last_name="Person",
            company="Example Health Store AS",
            country="Norway",
        )

        # Email doesn't exist
        mock_lead_repository.get_lead_by_email.return_value = None
        # But similar company exists
        existing = MagicMock()
        existing.company = "Example Health Store"  # Without AS suffix
        mock_lead_repository.get_leads_by_company.return_value = [existing]

        result = await checker.check_duplicates([lead])

        # Should be filtered as duplicate
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_check_duplicates_allows_different_companies(
        self,
        checker: LeadDuplicateChecker,
        mock_lead_repository: AsyncMock,
    ) -> None:
        """Test that different company names pass through."""
        lead = TransformedLead(
            email="new@wellness.no",
            first_name="New",
            last_name="Person",
            company="Wellness Center AS",
            country="Norway",
        )

        # Email doesn't exist
        mock_lead_repository.get_lead_by_email.return_value = None
        # Different company exists
        existing = MagicMock()
        existing.company = "Health Food Store"  # Completely different
        mock_lead_repository.get_leads_by_company.return_value = [existing]

        result = await checker.check_duplicates([lead])

        # Should pass through
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_check_duplicates_deduplicates_within_batch(
        self,
        checker: LeadDuplicateChecker,
        mock_lead_repository: AsyncMock,
    ) -> None:
        """Test that duplicate emails within same batch are detected."""
        leads = [
            TransformedLead(
                email="same@example.com",
                first_name="First",
                last_name="Person",
                company="Company A",
            ),
            TransformedLead(
                email="SAME@example.com",  # Same email, different case
                first_name="Second",
                last_name="Person",
                company="Company B",
            ),
        ]

        mock_lead_repository.get_lead_by_email.return_value = None
        mock_lead_repository.get_leads_by_company.return_value = []

        result = await checker.check_duplicates(leads)

        # Only first should pass
        assert len(result) == 1
        assert result[0].first_name == "First"

    def test_normalize_company_removes_suffixes(
        self,
        checker: LeadDuplicateChecker,
    ) -> None:
        """Test company name normalization removes common suffixes."""
        assert checker._normalize_company("Example AS") == "example"
        assert checker._normalize_company("Example AB") == "example"
        assert checker._normalize_company("Example Ltd") == "example"
        assert checker._normalize_company("Example Inc") == "example"
        assert checker._normalize_company("Example GmbH") == "example"

    def test_normalize_company_handles_empty(
        self,
        checker: LeadDuplicateChecker,
    ) -> None:
        """Test company name normalization handles empty strings."""
        assert checker._normalize_company("") == ""
        assert checker._normalize_company("   ") == ""

    def test_calculate_similarity(
        self,
        checker: LeadDuplicateChecker,
    ) -> None:
        """Test similarity calculation."""
        # Identical strings
        assert checker._calculate_similarity("example", "example") == 1.0

        # Similar strings
        similarity = checker._calculate_similarity("example health", "example health store")
        assert 0.7 < similarity < 1.0

        # Very different strings
        similarity = checker._calculate_similarity("abc", "xyz")
        assert similarity < 0.5

    def test_calculate_similarity_handles_empty(
        self,
        checker: LeadDuplicateChecker,
    ) -> None:
        """Test similarity calculation handles empty strings."""
        assert checker._calculate_similarity("", "example") == 0.0
        assert checker._calculate_similarity("example", "") == 0.0
        assert checker._calculate_similarity("", "") == 0.0
