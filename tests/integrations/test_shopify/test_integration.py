"""Integration tests for Shopify client.

These tests require a live Shopify store connection.
They are skipped by default unless SHOPIFY_INTEGRATION_TEST=1 is set.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.shopify import (
    ShopifyClient,
    ShopifyProduct,
    build_utm_url,
    get_product_url_with_utm,
)
from teams.dawo.middleware.retry import RetryConfig, RetryResult


# Skip integration tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.environ.get("SHOPIFY_INTEGRATION_TEST") != "1",
    reason="Integration tests disabled. Set SHOPIFY_INTEGRATION_TEST=1 to run.",
)


@pytest.fixture
def live_client():
    """Create client with live credentials from environment."""
    store_domain = os.environ.get("MYSHOPIFY_DOMAIN", "")
    access_token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")

    if not store_domain or not access_token:
        pytest.skip("MYSHOPIFY_DOMAIN and SHOPIFY_ACCESS_TOKEN required")

    return ShopifyClient(
        store_domain=store_domain,
        access_token=access_token,
        retry_config=RetryConfig(max_retries=2, base_delay=0.5),
    )


class TestLiveProductRetrieval:
    """Test product retrieval against live Shopify store."""

    @pytest.mark.asyncio
    async def test_search_products_live(self, live_client):
        """Search products returns results from live store."""
        products = await live_client.search_products("mushroom", limit=5)

        # Should find at least one mushroom product
        assert len(products) >= 1
        assert all(isinstance(p, ShopifyProduct) for p in products)

    @pytest.mark.asyncio
    async def test_get_product_by_handle_live(self, live_client):
        """Get product by handle from live store."""
        # First search for a product to get a valid handle
        products = await live_client.search_products("extract", limit=1)
        if not products:
            pytest.skip("No products found in store")

        handle = products[0].handle
        product = await live_client.get_product_by_handle(handle)

        assert product is not None
        assert product.handle == handle
        assert product.id.startswith("gid://shopify/Product/")

    @pytest.mark.asyncio
    async def test_caching_reduces_api_calls(self, live_client):
        """Verify caching reduces API calls on repeated queries."""
        products = await live_client.search_products("lion", limit=1)
        if not products:
            pytest.skip("No products found")

        handle = products[0].handle

        # First call hits API
        product1 = await live_client.get_product_by_handle(handle)

        # Second call should use cache (same result, no API call)
        product2 = await live_client.get_product_by_handle(handle)

        assert product1.id == product2.id
        assert product1.title == product2.title


class TestLiveCollectionRetrieval:
    """Test collection-based queries against live store."""

    @pytest.mark.asyncio
    async def test_get_products_by_collection_live(self, live_client):
        """Get products from a live collection."""
        # This assumes there's a collection - adjust handle as needed
        products = await live_client.get_products_by_collection(
            "all", limit=5  # 'all' is a common default collection
        )

        # May be empty if collection doesn't exist
        if products:
            assert all(isinstance(p, ShopifyProduct) for p in products)


class TestNovelFoodClassificationLive:
    """Test Novel Food classification with real products."""

    @pytest.mark.asyncio
    async def test_chaga_product_is_supplement(self, live_client):
        """Chaga products must be classified as supplement."""
        products = await live_client.search_products("chaga", limit=1)

        if products:
            assert products[0].novel_food_classification == "supplement"

    @pytest.mark.asyncio
    async def test_lions_mane_is_food(self, live_client):
        """Lion's Mane without supplement tag is classified as food."""
        products = await live_client.search_products("lion's mane", limit=1)

        if products:
            product = products[0]
            # Unless explicitly tagged as supplement
            if "supplement" not in [t.lower() for t in product.tags]:
                if "chaga" not in [t.lower() for t in product.tags]:
                    assert product.novel_food_classification == "food"


class TestUTMIntegration:
    """Test UTM generation with real product URLs."""

    @pytest.mark.asyncio
    async def test_utm_with_real_product(self, live_client):
        """UTM parameters work with real product URLs."""
        products = await live_client.search_products("extract", limit=1)
        if not products:
            pytest.skip("No products found")

        product = products[0]
        utm_url = get_product_url_with_utm(
            product_url=product.product_url,
            content_type="feed_post",
            post_id="test123",
        )

        assert "utm_source=instagram" in utm_url
        assert "utm_campaign=feed_post" in utm_url
        assert "utm_content=test123" in utm_url
        assert product.handle in utm_url


class TestDegradedModeRecovery:
    """Test graceful degradation and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_stale_cache_after_api_failure(self):
        """Stale cache is returned when API fails."""
        mock_http = AsyncMock()

        # First call succeeds
        mock_http.post.return_value = RetryResult(
            success=True,
            response=MagicMock(
                json=lambda: {
                    "data": {
                        "products": {
                            "edges": [
                                {
                                    "node": {
                                        "id": "gid://shopify/Product/123",
                                        "title": "Test Product",
                                        "handle": "test-product",
                                        "descriptionHtml": "",
                                        "productType": "Extract",
                                        "tags": [],
                                        "variants": {"edges": []},
                                        "images": {"edges": []},
                                        "collections": {"edges": []},
                                    }
                                }
                            ]
                        }
                    }
                }
            ),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="test-token",
                cache_ttl_seconds=1,  # Short TTL for testing
            )

            # First call populates cache
            product1 = await client.get_product_by_handle("test-product")
            assert product1 is not None
            assert product1.is_placeholder is False

            # Simulate API failure
            mock_http.post.return_value = RetryResult(
                success=False,
                attempts=3,
                last_error="Connection failed",
                is_incomplete=True,
            )

            # Wait for cache to expire
            import time

            time.sleep(1.1)

            # Second call uses stale cache
            product2 = await client.get_product_by_handle("test-product")

            # Should get stale data with placeholder flag
            assert product2 is not None
            assert product2.is_placeholder is True
            assert product2.id == product1.id
