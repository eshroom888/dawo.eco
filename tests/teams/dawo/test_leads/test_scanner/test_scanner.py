"""Tests for B2BLeadScanner agent.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner
"""

import pytest
from unittest.mock import AsyncMock

from teams.dawo.leads.scanner.agent import B2BLeadScanner
from teams.dawo.leads.scanner.config import LeadScannerConfig
from teams.dawo.leads.scanner.tools import HunterAPIError


class TestB2BLeadScanner:
    """Tests for B2BLeadScanner agent."""

    @pytest.fixture
    def scanner(
        self,
        scanner_config: LeadScannerConfig,
        mock_hunter_client: AsyncMock,
    ) -> B2BLeadScanner:
        """Create scanner with mocked dependencies."""
        return B2BLeadScanner(
            config=scanner_config,
            hunter_client=mock_hunter_client,
        )

    @pytest.mark.asyncio
    async def test_scan_returns_result(
        self,
        scanner: B2BLeadScanner,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that scan returns ScanResult."""
        result = await scanner.scan()

        assert result is not None
        assert result.domains_searched > 0
        assert len(result.leads) > 0

    @pytest.mark.asyncio
    async def test_scan_filters_by_confidence(
        self,
        scanner: B2BLeadScanner,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that scan filters leads below confidence threshold."""
        # Mock response with low confidence
        mock_hunter_client.domain_search.return_value = {
            "organization": "Low Confidence Corp",
            "country": "Norway",
            "emails": [
                {"value": "test@low.com", "confidence": 50},  # 0.5 < 0.7 threshold
            ],
        }

        result = await scanner.scan()

        # Should filter out low confidence leads
        for lead in result.leads:
            assert lead.confidence >= scanner._config.min_confidence

    @pytest.mark.asyncio
    async def test_scan_filters_by_country(
        self,
        scanner: B2BLeadScanner,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that scan filters leads from non-target countries."""
        # Mock response with non-target country
        mock_hunter_client.domain_search.return_value = {
            "organization": "US Company",
            "country": "United States",
            "emails": [
                {"value": "test@us.com", "confidence": 95},
            ],
        }

        result = await scanner.scan()

        # Should filter out non-target country
        for lead in result.leads:
            if lead.country:
                assert any(
                    c.lower() in lead.country.lower()
                    for c in scanner._config.countries
                )

    @pytest.mark.asyncio
    async def test_scan_handles_api_error_gracefully(
        self,
        scanner: B2BLeadScanner,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that scan continues on API errors (graceful degradation)."""
        # First call fails, second succeeds
        mock_hunter_client.domain_search.side_effect = [
            HunterAPIError("API Error"),
            {
                "organization": "Good Company",
                "country": "Norway",
                "emails": [{"value": "test@good.com", "confidence": 90}],
            },
        ]

        result = await scanner.scan()

        # Should have errors but continue
        assert len(result.errors) > 0
        assert result.domains_searched > 0

    @pytest.mark.asyncio
    async def test_scan_respects_max_leads(
        self,
        scanner_config: LeadScannerConfig,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that scan respects max_leads_per_scan limit."""
        # Set low limit
        scanner_config.max_leads_per_scan = 2
        scanner = B2BLeadScanner(scanner_config, mock_hunter_client)

        result = await scanner.scan()

        assert len(result.leads) <= 2

    @pytest.mark.asyncio
    async def test_scan_logs_statistics(
        self,
        scanner: B2BLeadScanner,
        mock_hunter_client: AsyncMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that scan logs statistics."""
        import logging

        with caplog.at_level(logging.INFO):
            await scanner.scan()

        # Should log scan completion
        assert any("Scan complete" in record.message for record in caplog.records)

    def test_is_relevant_country_matches_partial(
        self,
        scanner: B2BLeadScanner,
    ) -> None:
        """Test country matching with partial strings."""
        assert scanner._is_relevant_country("Norway")
        assert scanner._is_relevant_country("norway")
        assert scanner._is_relevant_country("NORWAY")
        assert scanner._is_relevant_country("Sweden")
        assert not scanner._is_relevant_country("Germany")
        assert not scanner._is_relevant_country("United States")

    def test_is_relevant_country_returns_true_when_no_filter(
        self,
        scanner_config: LeadScannerConfig,
        mock_hunter_client: AsyncMock,
    ) -> None:
        """Test that no country filter means all countries are relevant."""
        scanner_config.countries = []
        scanner = B2BLeadScanner(scanner_config, mock_hunter_client)

        assert scanner._is_relevant_country("Any Country")
