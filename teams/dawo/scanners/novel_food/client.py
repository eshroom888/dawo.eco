"""Novel Food Catalogue HTTP client.

Epic 6, Story 6-2, Task 4: Catalogue client.

Queries the EU Food & Feed Portal for Novel Food Catalogue entries.
Uses RetryMiddleware for resilient HTTP requests.
Tries backend JSON endpoint first, falls back to HTML page scraping.
"""

import asyncio
import logging
from typing import Any, Optional, Protocol, runtime_checkable

import httpx

from teams.dawo.scanners.novel_food.config import NovelFoodMonitorConfig, SpeciesConfig

logger = logging.getLogger(__name__)


class NovelFoodClientError(Exception):
    """Raised when catalogue query fails after retries."""


@runtime_checkable
class RetryResultProtocol(Protocol):
    """Protocol for RetryMiddleware result object."""

    success: bool
    response: Any
    last_error: Optional[str]


@runtime_checkable
class RetryMiddlewareProtocol(Protocol):
    """Protocol for RetryMiddleware dependency injection."""

    async def execute_with_retry(self, func: Any, context: str = "") -> RetryResultProtocol: ...


class NovelFoodCatalogueClient:
    """HTTP client for querying the EU Novel Food Catalogue.

    Story 6-2, Task 4: Query the EU Food & Feed Portal.

    Accepts httpx.AsyncClient, RetryMiddleware, and config via constructor.
    All HTTP requests go through retry middleware.
    Rate limiting enforced between species queries.

    Attributes:
        _client: Async HTTP client for making requests
        _retry: Retry middleware for resilient requests
        _config: Monitor configuration with URLs and delay settings
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        retry: RetryMiddlewareProtocol,
        config: NovelFoodMonitorConfig,
    ) -> None:
        """Initialize catalogue client.

        Args:
            http_client: Async HTTP client
            retry: Retry middleware instance
            config: Novel food monitor configuration
        """
        self._client = http_client
        self._retry = retry
        self._config = config
        self._headers = {
            "Accept": "application/json",
            "Accept-Language": "en",
            "User-Agent": config.user_agent,
        }

    async def search_species(self, species_name: str) -> bytes:
        """Fetch search results for one species.

        Queries the backend JSON endpoint. Uses RetryMiddleware for each request.

        Args:
            species_name: Latin species name to search for

        Returns:
            Raw response bytes (JSON or HTML)

        Raises:
            NovelFoodClientError: If search fails after retries
        """
        async def _fetch() -> bytes:
            resp = await self._client.get(
                self._config.search_url,
                params={"searchText": species_name},
                headers=self._headers,
                timeout=self._config.timeout_seconds,
            )
            resp.raise_for_status()
            return resp.content

        result = await self._retry.execute_with_retry(
            _fetch, context=f"novel_food_search_{species_name}"
        )
        if not result.success:
            raise NovelFoodClientError(
                f"Search failed for '{species_name}' after retries: {result.last_error}"
            )
        logger.info(
            "Fetched Novel Food Catalogue for '%s': %d bytes",
            species_name,
            len(result.response),
        )
        return result.response

    async def fetch_all_species(
        self, species_list: list[SpeciesConfig]
    ) -> dict[str, bytes]:
        """Fetch all species with rate limiting delay between requests.

        Args:
            species_list: List of species configurations to query

        Returns:
            Dict mapping species latin name to raw response bytes.
            Failed species are omitted (logged as warnings).
        """
        results: dict[str, bytes] = {}
        errors: list[str] = []

        for i, species in enumerate(species_list):
            try:
                data = await self.search_species(species.latin_name)
                results[species.latin_name] = data
            except NovelFoodClientError as e:
                logger.warning(
                    "Failed to fetch species '%s': %s",
                    species.latin_name,
                    e,
                )
                errors.append(f"{species.latin_name}: {e}")

            # Rate limiting: sleep between requests (not after last)
            if i < len(species_list) - 1:
                await asyncio.sleep(self._config.request_delay_seconds)

        if errors:
            logger.warning(
                "Partial fetch failure: %d/%d species failed: %s",
                len(errors),
                len(species_list),
                "; ".join(errors),
            )

        return results


__all__ = [
    "NovelFoodCatalogueClient",
    "NovelFoodClientError",
    "RetryMiddlewareProtocol",
    "RetryResultProtocol",
]
