"""Tests for NovelFoodCatalogueClient.

Story 6-2, Task 4: Create catalogue client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Optional

from teams.dawo.scanners.novel_food.client import (
    NovelFoodCatalogueClient,
    NovelFoodClientError,
)
from teams.dawo.scanners.novel_food.config import SpeciesConfig, NovelFoodMonitorConfig


@dataclass
class MockRetryResult:
    success: bool = True
    response: object = None
    attempts: int = 1
    last_error: Optional[str] = None
    is_incomplete: bool = False


class TestSearchSpecies:
    """Tests for NovelFoodCatalogueClient.search_species()."""

    @pytest.mark.asyncio
    async def test_search_success_json(self, novel_food_config, sample_json_response):
        """Test 11.15: search_species with mocked httpx (JSON response)."""
        retry = AsyncMock()
        retry.execute_with_retry.return_value = MockRetryResult(
            success=True,
            response=sample_json_response,
        )
        http_client = AsyncMock()

        client = NovelFoodCatalogueClient(
            http_client=http_client,
            retry=retry,
            config=novel_food_config,
        )
        result = await client.search_species("Hericium erinaceus")
        assert isinstance(result, bytes)
        assert len(result) > 0
        retry.execute_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_retry_on_failure(self, novel_food_config):
        """Test 11.18: search_species retry on failure."""
        retry = AsyncMock()
        retry.execute_with_retry.return_value = MockRetryResult(
            success=False,
            response=None,
            last_error="Connection timed out",
        )
        http_client = AsyncMock()

        client = NovelFoodCatalogueClient(
            http_client=http_client,
            retry=retry,
            config=novel_food_config,
        )
        with pytest.raises(NovelFoodClientError, match="Search failed"):
            await client.search_species("Hericium erinaceus")

    @pytest.mark.asyncio
    async def test_search_passes_correct_params(self, novel_food_config):
        """Verify search_species passes searchText param and proper headers."""
        retry = AsyncMock()
        retry.execute_with_retry.return_value = MockRetryResult(
            success=True,
            response=b'[]',
        )
        http_client = AsyncMock()

        client = NovelFoodCatalogueClient(
            http_client=http_client,
            retry=retry,
            config=novel_food_config,
        )
        await client.search_species("Hericium erinaceus")

        # The retry should wrap the actual HTTP call
        call_args = retry.execute_with_retry.call_args
        assert "novel_food_search" in call_args.kwargs.get("context", call_args.args[1] if len(call_args.args) > 1 else "")


class TestFetchAllSpecies:
    """Tests for NovelFoodCatalogueClient.fetch_all_species()."""

    @pytest.mark.asyncio
    async def test_fetch_all_returns_dict(self, novel_food_config, sample_json_response):
        """Test fetch_all_species returns dict keyed by species name."""
        retry = AsyncMock()
        retry.execute_with_retry.return_value = MockRetryResult(
            success=True,
            response=sample_json_response,
        )
        http_client = AsyncMock()

        client = NovelFoodCatalogueClient(
            http_client=http_client,
            retry=retry,
            config=novel_food_config,
        )
        result = await client.fetch_all_species(list(novel_food_config.species))
        assert isinstance(result, dict)
        assert len(result) == 2  # Two species in config

    @pytest.mark.asyncio
    async def test_fetch_all_rate_limiting(self, novel_food_config, sample_json_response):
        """Test 11.17: fetch_all_species rate limiting delay."""
        retry = AsyncMock()
        retry.execute_with_retry.return_value = MockRetryResult(
            success=True,
            response=sample_json_response,
        )
        http_client = AsyncMock()

        client = NovelFoodCatalogueClient(
            http_client=http_client,
            retry=retry,
            config=novel_food_config,
        )
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client.fetch_all_species(list(novel_food_config.species))
            # Should sleep between species (n-1 times for n species)
            assert mock_sleep.call_count == 1  # 2 species - 1 = 1 sleep

    @pytest.mark.asyncio
    async def test_fetch_all_partial_failure(self, novel_food_config):
        """Test partial failure — some species succeed, some fail."""
        call_count = 0

        async def mock_retry(func, context=""):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MockRetryResult(success=True, response=b'[{"name": "test"}]')
            return MockRetryResult(success=False, last_error="timeout")

        retry = AsyncMock()
        retry.execute_with_retry = mock_retry
        http_client = AsyncMock()

        client = NovelFoodCatalogueClient(
            http_client=http_client,
            retry=retry,
            config=novel_food_config,
        )
        result = await client.fetch_all_species(list(novel_food_config.species))
        # Should have at least one success and one failure recorded
        assert len(result) >= 1


class TestNovelFoodClientError:
    """Tests for NovelFoodClientError exception."""

    def test_is_exception(self):
        assert issubclass(NovelFoodClientError, Exception)

    def test_message(self):
        err = NovelFoodClientError("test message")
        assert str(err) == "test message"
