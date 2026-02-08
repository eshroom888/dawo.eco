"""Unit tests for Shopify client."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from integrations.shopify.client import (
    ShopifyClient,
    ShopifyProduct,
    ProductPlaceholder,
)
from teams.dawo.middleware.retry import RetryConfig, RetryResult


class TestShopifyClientInit:
    """Test ShopifyClient initialization."""

    def test_init_requires_store_domain(self):
        """ShopifyClient requires store_domain."""
        with pytest.raises(ValueError, match="store_domain is required"):
            ShopifyClient(
                store_domain="",
                access_token="test-token",
            )

    def test_init_requires_access_token(self):
        """ShopifyClient requires access_token."""
        with pytest.raises(ValueError, match="access_token is required"):
            ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="",
            )

    def test_init_with_valid_params(self, retry_config):
        """ShopifyClient initializes with valid parameters."""
        client = ShopifyClient(
            store_domain="test.myshopify.com",
            access_token="shpat_test123",
            retry_config=retry_config,
        )
        assert client._store_domain == "test.myshopify.com"
        assert client._access_token == "shpat_test123"

    def test_init_with_custom_cache_ttl(self):
        """ShopifyClient accepts custom cache TTL."""
        client = ShopifyClient(
            store_domain="test.myshopify.com",
            access_token="shpat_test123",
            cache_ttl_seconds=7200,
        )
        assert client._cache_ttl == timedelta(seconds=7200)


class TestShopifyClientGetProductByHandle:
    """Test get_product_by_handle method."""

    @pytest.mark.asyncio
    async def test_get_product_by_handle_success(
        self, mock_http_client, retry_config, lions_mane_graphql_response
    ):
        """Successfully retrieve product by handle."""
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: lions_mane_graphql_response),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                retry_config=retry_config,
            )
            product = await client.get_product_by_handle("lions-mane-extract")

        assert product is not None
        assert product.id == "gid://shopify/Product/123"
        assert product.title == "Lion's Mane Extract"
        assert product.handle == "lions-mane-extract"
        assert product.price == "299.00"
        assert product.inventory_quantity == 80  # 50 + 30

    @pytest.mark.asyncio
    async def test_get_product_by_handle_not_found(
        self, mock_http_client, retry_config, empty_products_response
    ):
        """Return None when product not found."""
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: empty_products_response),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                retry_config=retry_config,
            )
            product = await client.get_product_by_handle("nonexistent")

        assert product is None

    @pytest.mark.asyncio
    async def test_get_product_by_handle_uses_cache(
        self, mock_http_client, retry_config, lions_mane_graphql_response
    ):
        """Second call uses cache, no API call."""
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: lions_mane_graphql_response),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                retry_config=retry_config,
            )

            # First call
            product1 = await client.get_product_by_handle("lions-mane-extract")
            # Second call (should use cache)
            product2 = await client.get_product_by_handle("lions-mane-extract")

        # Only one API call made
        assert mock_http_client.post.call_count == 1
        assert product1.id == product2.id


class TestShopifyClientGetProductById:
    """Test get_product_by_id method."""

    @pytest.mark.asyncio
    async def test_get_product_by_id_success(
        self, mock_http_client, retry_config, lions_mane_graphql_response
    ):
        """Successfully retrieve product by ID."""
        # Modify response for ID-based query
        response = {
            "data": {
                "product": lions_mane_graphql_response["data"]["products"]["edges"][0][
                    "node"
                ]
            }
        }
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: response),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                retry_config=retry_config,
            )
            product = await client.get_product_by_id("gid://shopify/Product/123")

        assert product is not None
        assert product.id == "gid://shopify/Product/123"

    @pytest.mark.asyncio
    async def test_get_product_by_id_uses_cache(
        self, mock_http_client, retry_config, lions_mane_graphql_response
    ):
        """Second call uses cache, no API call."""
        response = {
            "data": {
                "product": lions_mane_graphql_response["data"]["products"]["edges"][0][
                    "node"
                ]
            }
        }
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: response),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                retry_config=retry_config,
            )

            # First call
            product1 = await client.get_product_by_id("gid://shopify/Product/123")
            # Second call (should use cache)
            product2 = await client.get_product_by_id("gid://shopify/Product/123")

        # Only one API call made
        assert mock_http_client.post.call_count == 1
        assert product1.id == product2.id


class TestRetryBehavior:
    """Test retry behavior with mocked failures."""

    @pytest.mark.asyncio
    async def test_retry_attempts_on_failure(
        self, mock_http_client, retry_config
    ):
        """Verify retry attempts are made on API failure."""
        mock_http_client.post.return_value = RetryResult(
            success=False,
            attempts=3,
            last_error="Connection timeout",
            is_incomplete=True,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                retry_config=retry_config,
            )
            product = await client.get_product_by_handle("test-product")

        # Should return None after failed retries
        assert product is None
        # HTTP client was called (retry logic is in RetryableHttpClient)
        assert mock_http_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_stale_cache_after_retry_failure(
        self, mock_http_client, retry_config, lions_mane_graphql_response
    ):
        """Stale cache returned when API fails after retries."""
        # First call succeeds
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: lions_mane_graphql_response),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                retry_config=retry_config,
                cache_ttl_seconds=1,  # Short TTL
            )

            # First call populates cache
            product1 = await client.get_product_by_handle("lions-mane-extract")
            assert product1 is not None
            assert product1.is_placeholder is False

            # Wait for cache to expire
            import time
            time.sleep(1.1)

            # Now API fails
            mock_http_client.post.return_value = RetryResult(
                success=False,
                attempts=3,
                last_error="Service unavailable",
                is_incomplete=True,
            )

            # Second call should use stale cache
            product2 = await client.get_product_by_handle("lions-mane-extract")

        assert product2 is not None
        assert product2.is_placeholder is True
        assert product2.id == product1.id


class TestShopifyClientSearchProducts:
    """Test search_products method."""

    @pytest.mark.asyncio
    async def test_search_products_success(
        self, mock_http_client, retry_config, lions_mane_graphql_response
    ):
        """Successfully search products."""
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: lions_mane_graphql_response),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                retry_config=retry_config,
            )
            products = await client.search_products("lion")

        assert len(products) == 1
        assert products[0].title == "Lion's Mane Extract"

    @pytest.mark.asyncio
    async def test_search_products_empty(
        self, mock_http_client, retry_config, empty_products_response
    ):
        """Return empty list when no matches."""
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: empty_products_response),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                retry_config=retry_config,
            )
            products = await client.search_products("xyz123notfound")

        assert products == []


class TestShopifyClientGetProductsByCollection:
    """Test get_products_by_collection method."""

    @pytest.mark.asyncio
    async def test_get_products_by_collection_success(
        self, mock_http_client, retry_config, products_by_collection_response
    ):
        """Successfully retrieve products by collection handle."""
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: products_by_collection_response),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                retry_config=retry_config,
            )
            products = await client.get_products_by_collection("mushroom-extracts")

        assert len(products) == 2
        assert products[0].title == "Lion's Mane Extract"
        assert products[1].title == "Reishi Extract"


class TestNovelFoodClassification:
    """Test Novel Food classification logic."""

    def test_chaga_is_always_supplement(self):
        """Chaga products must be classified as supplement."""
        from integrations.shopify.client import ShopifyClient

        client = ShopifyClient.__new__(ShopifyClient)
        classification = client._determine_novel_food_classification(
            ["chaga", "antioxidant"]
        )
        assert classification == "supplement"

    def test_supplement_tag_is_supplement(self):
        """Products with supplement tag are supplements."""
        from integrations.shopify.client import ShopifyClient

        client = ShopifyClient.__new__(ShopifyClient)
        classification = client._determine_novel_food_classification(
            ["lions_mane", "supplement"]
        )
        assert classification == "supplement"

    def test_kosttilskudd_tag_is_supplement(self):
        """Products with Norwegian 'kosttilskudd' tag are supplements."""
        from integrations.shopify.client import ShopifyClient

        client = ShopifyClient.__new__(ShopifyClient)
        classification = client._determine_novel_food_classification(
            ["reishi", "kosttilskudd"]
        )
        assert classification == "supplement"

    def test_regular_mushroom_is_food(self):
        """Regular mushroom products default to food."""
        from integrations.shopify.client import ShopifyClient

        client = ShopifyClient.__new__(ShopifyClient)
        classification = client._determine_novel_food_classification(
            ["lions_mane", "nootropic", "focus"]
        )
        assert classification == "food"

    def test_case_insensitive_classification(self):
        """Classification is case-insensitive."""
        from integrations.shopify.client import ShopifyClient

        client = ShopifyClient.__new__(ShopifyClient)

        assert (
            client._determine_novel_food_classification(["CHAGA", "IMMUNE"])
            == "supplement"
        )
        assert (
            client._determine_novel_food_classification(["Supplement", "Lions_Mane"])
            == "supplement"
        )


class TestCacheBehavior:
    """Test cache TTL and expiration."""

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(
        self, mock_http_client, lions_mane_graphql_response
    ):
        """Cache entries expire after TTL."""
        mock_http_client.post.return_value = RetryResult(
            success=True,
            response=MagicMock(json=lambda: lions_mane_graphql_response),
            attempts=1,
        )

        with patch(
            "integrations.shopify.client.RetryableHttpClient",
            return_value=mock_http_client,
        ):
            client = ShopifyClient(
                store_domain="test.myshopify.com",
                access_token="shpat_test123",
                cache_ttl_seconds=1,  # 1 second TTL
            )

            # First call
            await client.get_product_by_handle("lions-mane-extract")

            # Simulate time passing
            import time

            time.sleep(1.1)

            # Second call should hit API again
            await client.get_product_by_handle("lions-mane-extract")

        # Two API calls made
        assert mock_http_client.post.call_count == 2

    def test_clear_cache(self, retry_config):
        """clear_cache removes all cached products."""
        client = ShopifyClient(
            store_domain="test.myshopify.com",
            access_token="shpat_test123",
            retry_config=retry_config,
        )

        # Manually add to cache
        product = ShopifyProduct(
            id="123",
            title="Test",
            description="",
            handle="test",
            price="100.00",
            currency="NOK",
            variants=[],
            images=[],
            inventory_quantity=10,
            product_type="Test",
            tags=[],
            novel_food_classification="food",
            sku=None,
            benefits=[],
            product_url="",
            collection_handles=[],
            is_placeholder=False,
        )
        client._cache["handle:test"] = (product, datetime.now(timezone.utc))

        assert len(client._cache) == 1
        client.clear_cache()
        assert len(client._cache) == 0


class TestProductDataModel:
    """Test ShopifyProduct dataclass fields."""

    def test_shopify_product_has_all_fields(self):
        """ShopifyProduct includes all required fields."""
        product = ShopifyProduct(
            id="gid://shopify/Product/123",
            title="Lion's Mane Extract",
            description="<p>Premium extract</p>",
            handle="lions-mane-extract",
            price="299.00",
            currency="NOK",
            variants=[{"sku": "LM-60"}],
            images=["https://cdn.shopify.com/image.jpg"],
            inventory_quantity=50,
            product_type="Extract",
            tags=["lions_mane", "focus"],
            novel_food_classification="food",
            sku="LM-60",
            benefits=["Cognitive support", "Focus enhancement"],
            product_url="https://dawo.no/products/lions-mane-extract",
            collection_handles=["mushroom-extracts", "focus-support"],
            is_placeholder=False,
        )

        assert product.id == "gid://shopify/Product/123"
        assert product.sku == "LM-60"
        assert len(product.benefits) == 2
        assert "mushroom-extracts" in product.collection_handles
        assert product.is_placeholder is False


class TestProductPlaceholder:
    """Test ProductPlaceholder for graceful degradation."""

    def test_placeholder_creation(self):
        """ProductPlaceholder stores degradation info."""
        placeholder = ProductPlaceholder(
            handle="lions-mane-extract",
            reason="api_unavailable",
            cached_at=datetime.now(timezone.utc),
            stale_data=None,
        )

        assert placeholder.handle == "lions-mane-extract"
        assert placeholder.reason == "api_unavailable"
        assert placeholder.stale_data is None

    def test_placeholder_with_stale_data(self):
        """ProductPlaceholder can hold stale product data."""
        stale_product = ShopifyProduct(
            id="123",
            title="Lion's Mane (Stale)",
            description="",
            handle="lions-mane-extract",
            price="299.00",
            currency="NOK",
            variants=[],
            images=[],
            inventory_quantity=50,
            product_type="Extract",
            tags=[],
            novel_food_classification="food",
            sku=None,
            benefits=[],
            product_url="",
            collection_handles=[],
            is_placeholder=True,
        )

        placeholder = ProductPlaceholder(
            handle="lions-mane-extract",
            reason="api_timeout",
            cached_at=datetime.now(timezone.utc) - timedelta(hours=12),
            stale_data=stale_product,
        )

        assert placeholder.stale_data is not None
        assert placeholder.stale_data.is_placeholder is True
