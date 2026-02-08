"""Shopify client for product data retrieval with caching.

This module provides a Shopify client that uses the Shopify Admin GraphQL API
with a 1-hour cache layer to reduce API calls per FR48 requirements.

Architecture Compliance:
- Configuration injected via constructor
- Async-first design
- RetryableHttpClient for all API calls
- Graceful error handling with stale cache fallback
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Protocol, runtime_checkable

from teams.dawo.middleware.retry import RetryConfig, RetryResult
from teams.dawo.middleware.http_client import RetryableHttpClient

logger = logging.getLogger(__name__)

# Shopify Admin GraphQL API version
SHOPIFY_API_VERSION = "2024-01"


@dataclass
class ShopifyProduct:
    """Product data from Shopify.

    Attributes:
        id: Shopify product ID (GraphQL global ID)
        title: Product title
        description: Product description (HTML)
        handle: URL handle
        price: Price as string (e.g., "299.00")
        currency: Currency code (e.g., "NOK")
        variants: List of variant data
        images: List of image URLs
        inventory_quantity: Total inventory across variants
        product_type: Product type classification
        tags: List of product tags
        novel_food_classification: food or supplement (from tags)
        sku: Primary SKU for variant-level lookups
        benefits: List of product benefits (from description/metafields)
        product_url: Full product URL
        collection_handles: List of collection handles product belongs to
        is_placeholder: True if data is stale (graceful degradation)
    """

    id: str
    title: str
    description: str
    handle: str
    price: str
    currency: str
    variants: list[dict[str, Any]]
    images: list[str]
    inventory_quantity: int
    product_type: str
    tags: list[str]
    novel_food_classification: str  # "food" or "supplement"
    sku: Optional[str] = None
    benefits: list[str] = field(default_factory=list)
    product_url: str = ""
    collection_handles: list[str] = field(default_factory=list)
    is_placeholder: bool = False


@dataclass
class ProductPlaceholder:
    """Placeholder when product data is unavailable.

    Used for graceful degradation when Shopify API is unavailable.

    Attributes:
        handle: Product URL handle
        reason: Degradation reason (api_unavailable, not_found, cache_expired)
        cached_at: When the stale data was originally cached
        stale_data: Stale product data if available
    """

    handle: str
    reason: str
    cached_at: Optional[datetime] = None
    stale_data: Optional[ShopifyProduct] = None


@runtime_checkable
class ShopifyClientProtocol(Protocol):
    """Protocol defining the Shopify client interface.

    Any class implementing this protocol can be used as a Shopify client.
    This allows for easy mocking and alternative implementations.
    """

    async def get_product_by_handle(self, handle: str) -> Optional[ShopifyProduct]:
        """Get product by URL handle."""
        ...

    async def get_product_by_id(self, product_id: str) -> Optional[ShopifyProduct]:
        """Get product by Shopify ID."""
        ...

    async def search_products(self, query: str) -> list[ShopifyProduct]:
        """Search products by query."""
        ...

    async def get_products_by_collection(
        self, collection_handle: str
    ) -> list[ShopifyProduct]:
        """Get products from a collection by handle."""
        ...


# GraphQL query fragments
PRODUCT_FIELDS_FRAGMENT = """
    id
    title
    handle
    descriptionHtml
    productType
    tags
    variants(first: 100) {
        edges {
            node {
                id
                sku
                price
                inventoryQuantity
            }
        }
    }
    images(first: 10) {
        edges {
            node {
                url
            }
        }
    }
    collections(first: 10) {
        edges {
            node {
                handle
            }
        }
    }
"""

SEARCH_PRODUCTS_QUERY = """
query SearchProducts($query: String!, $first: Int!) {
    products(first: $first, query: $query) {
        edges {
            node {
                %s
            }
        }
    }
}
""" % PRODUCT_FIELDS_FRAGMENT

PRODUCT_BY_ID_QUERY = """
query GetProduct($id: ID!) {
    product(id: $id) {
        %s
    }
}
""" % PRODUCT_FIELDS_FRAGMENT

PRODUCTS_BY_COLLECTION_QUERY = """
query GetProductsByCollection($handle: String!, $first: Int!) {
    collection(handle: $handle) {
        products(first: $first) {
            edges {
                node {
                    %s
                }
            }
        }
    }
}
""" % PRODUCT_FIELDS_FRAGMENT


class ShopifyClient:
    """Shopify client with 1-hour caching layer.

    Implements ShopifyClientProtocol for type-safe injection.
    Uses Shopify Admin GraphQL API with RetryableHttpClient.

    Attributes:
        _store_domain: Shopify store domain
        _access_token: Shopify Admin API access token
        _http_client: RetryableHttpClient for API calls
        _cache: In-memory cache for products
        _cache_ttl: Cache time-to-live (default: 1 hour)
    """

    # Extended cache TTL for graceful degradation (24 hours)
    DEGRADED_CACHE_TTL = timedelta(hours=24)

    def __init__(
        self,
        store_domain: str,
        access_token: str,
        retry_config: Optional[RetryConfig] = None,
        cache_ttl_seconds: int = 3600,
        store_url: Optional[str] = None,
    ) -> None:
        """Initialize Shopify client.

        Args:
            store_domain: Shopify store domain (e.g., "dawo.myshopify.com")
            access_token: Shopify Admin API access token
            retry_config: Retry configuration (uses defaults if None)
            cache_ttl_seconds: Cache TTL in seconds (default: 3600 = 1 hour)
            store_url: Public store URL for product links (e.g., "https://dawo.no").
                       If not provided, defaults to https://{store_domain}.

        Raises:
            ValueError: If store_domain or access_token is empty
        """
        if not store_domain:
            raise ValueError("store_domain is required")
        if not access_token:
            raise ValueError("access_token is required")

        self._store_domain = store_domain
        self._access_token = access_token
        self._retry_config = retry_config or RetryConfig()
        self._cache: dict[str, tuple[ShopifyProduct, datetime]] = {}
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        # Store URL for product links - configurable for custom domains
        self._store_url = store_url.rstrip("/") if store_url else f"https://{store_domain}"

        # Build GraphQL endpoint URL
        self._graphql_url = (
            f"https://{store_domain}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
        )

        # Initialize HTTP client with retry middleware
        self._http_client = RetryableHttpClient(
            config=self._retry_config,
            api_name="shopify",
        )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Shopify Admin API requests.

        Returns:
            Dictionary with Content-Type and X-Shopify-Access-Token headers.
        """
        return {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self._access_token,
        }

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache:
            return False
        _, cached_at = self._cache[key]
        return datetime.now(timezone.utc) - cached_at < self._cache_ttl

    def _get_from_cache(self, key: str) -> Optional[ShopifyProduct]:
        """Get product from cache if valid."""
        if self._is_cache_valid(key):
            product, _ = self._cache[key]
            logger.debug("Cache hit for %s", key)
            return product
        return None

    def _get_stale_cache(self, key: str) -> Optional[ShopifyProduct]:
        """Get stale cache for degraded operation (up to 24h old)."""
        if key not in self._cache:
            return None
        product, cached_at = self._cache[key]
        if datetime.now(timezone.utc) - cached_at < self.DEGRADED_CACHE_TTL:
            # Mark as potentially stale
            product.is_placeholder = True
            logger.warning("Using stale cache for %s", key)
            return product
        return None

    def _add_to_cache(self, key: str, product: ShopifyProduct) -> None:
        """Add product to cache."""
        self._cache[key] = (product, datetime.now(timezone.utc))
        logger.debug("Cached product %s", key)

    def _determine_novel_food_classification(self, tags: list[str]) -> str:
        """Determine if product is food or supplement from tags.

        Per EU Novel Food Regulation:
        - Chaga products MUST be classified as supplement (unauthorized as food)
        - Products tagged 'supplement' or 'kosttilskudd' follow supplement rules
        - Default to 'food' for general wellness products
        """
        tags_lower = [t.lower() for t in tags]

        # Chaga is always supplement (Novel Food unauthorized)
        if "chaga" in tags_lower:
            return "supplement"

        # Explicit supplement tags (English and Norwegian)
        if "supplement" in tags_lower or "kosttilskudd" in tags_lower:
            return "supplement"

        # Default to food for other mushroom products
        return "food"

    def _extract_benefits(self, description: str) -> list[str]:
        """Extract product benefits from HTML description.

        Looks for common benefit patterns in the description.
        Returns empty list if no structured benefits found.
        """
        # Simple extraction - can be enhanced with metafield support
        benefits = []

        # Look for bullet point lists

        # Match list items
        list_pattern = r"<li[^>]*>(.*?)</li>"
        matches = re.findall(list_pattern, description, re.IGNORECASE | re.DOTALL)

        for match in matches[:5]:  # Limit to 5 benefits
            # Strip HTML tags
            benefit = re.sub(r"<[^>]+>", "", match).strip()
            if benefit and len(benefit) < 200:
                benefits.append(benefit)

        return benefits

    def _map_to_product(self, node: dict[str, Any]) -> ShopifyProduct:
        """Map Shopify GraphQL response to ShopifyProduct dataclass."""
        tags = node.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        # Extract variants
        variants_data = []
        variant_edges = node.get("variants", {}).get("edges", [])
        for edge in variant_edges:
            variant_node = edge.get("node", {})
            variants_data.append(variant_node)

        # Get first variant price and SKU
        price = "0.00"
        currency = "NOK"
        primary_sku = None
        if variants_data:
            first_variant = variants_data[0]
            price = str(first_variant.get("price", "0.00"))
            primary_sku = first_variant.get("sku")

        # Calculate total inventory
        inventory = sum(v.get("inventoryQuantity", 0) for v in variants_data)

        # Get image URLs
        images = []
        image_edges = node.get("images", {}).get("edges", [])
        for edge in image_edges:
            url = edge.get("node", {}).get("url")
            if url:
                images.append(url)

        # Get collection handles
        collection_handles = []
        collection_edges = node.get("collections", {}).get("edges", [])
        for edge in collection_edges:
            handle = edge.get("node", {}).get("handle")
            if handle:
                collection_handles.append(handle)

        # Extract benefits from description
        description = node.get("descriptionHtml", "")
        benefits = self._extract_benefits(description)

        # Build product URL using configured store URL
        handle = node.get("handle", "")
        product_url = f"{self._store_url}/products/{handle}"

        return ShopifyProduct(
            id=node.get("id", ""),
            title=node.get("title", ""),
            description=description,
            handle=handle,
            price=price,
            currency=currency,
            variants=variants_data,
            images=images,
            inventory_quantity=inventory,
            product_type=node.get("productType", ""),
            tags=tags,
            novel_food_classification=self._determine_novel_food_classification(tags),
            sku=primary_sku,
            benefits=benefits,
            product_url=product_url,
            collection_handles=collection_handles,
            is_placeholder=False,
        )

    async def _execute_graphql(
        self, query: str, variables: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Execute GraphQL query with retry handling.

        Returns None if query fails after retries (graceful degradation).
        """
        payload = {"query": query, "variables": variables}

        result: RetryResult = await self._http_client.post(
            self._graphql_url,
            json=payload,
            headers=self._get_headers(),
        )

        if not result.success:
            logger.error(
                "Shopify GraphQL query failed after %d attempts: %s",
                result.attempts,
                result.last_error,
            )
            return None

        response = result.response
        data = response.json()

        # Check for GraphQL errors
        if "errors" in data:
            logger.error("GraphQL errors: %s", data["errors"])
            return None

        return data

    async def get_product_by_handle(self, handle: str) -> Optional[ShopifyProduct]:
        """Get product by URL handle.

        Args:
            handle: Product URL handle (e.g., "lions-mane-extract")

        Returns:
            ShopifyProduct if found, None otherwise
        """
        cache_key = f"handle:{handle}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Search by handle
        query = f"handle:{handle}"
        data = await self._execute_graphql(
            SEARCH_PRODUCTS_QUERY,
            {"query": query, "first": 1},
        )

        if data is None:
            # API failed - try stale cache
            stale = self._get_stale_cache(cache_key)
            if stale:
                return stale
            return None

        edges = data.get("data", {}).get("products", {}).get("edges", [])
        if not edges:
            return None

        product = self._map_to_product(edges[0]["node"])
        self._add_to_cache(cache_key, product)

        # Also cache by ID for cross-referencing
        self._add_to_cache(f"id:{product.id}", product)

        return product

    async def get_product_by_id(self, product_id: str) -> Optional[ShopifyProduct]:
        """Get product by Shopify ID.

        Args:
            product_id: Shopify product ID (GraphQL global ID)

        Returns:
            ShopifyProduct if found, None otherwise
        """
        cache_key = f"id:{product_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        data = await self._execute_graphql(
            PRODUCT_BY_ID_QUERY,
            {"id": product_id},
        )

        if data is None:
            # API failed - try stale cache
            stale = self._get_stale_cache(cache_key)
            if stale:
                return stale
            return None

        product_node = data.get("data", {}).get("product")
        if not product_node:
            return None

        product = self._map_to_product(product_node)
        self._add_to_cache(cache_key, product)

        # Also cache by handle for cross-referencing
        self._add_to_cache(f"handle:{product.handle}", product)

        return product

    async def search_products(
        self, query: str, limit: int = 10
    ) -> list[ShopifyProduct]:
        """Search products by query.

        Args:
            query: Search query string
            limit: Maximum number of products to return

        Returns:
            List of matching products
        """
        data = await self._execute_graphql(
            SEARCH_PRODUCTS_QUERY,
            {"query": query, "first": limit},
        )

        if data is None:
            logger.warning("Product search failed for query: %s", query)
            return []

        edges = data.get("data", {}).get("products", {}).get("edges", [])
        products = []

        for edge in edges:
            product = self._map_to_product(edge["node"])
            products.append(product)

            # Cache each product
            self._add_to_cache(f"handle:{product.handle}", product)
            self._add_to_cache(f"id:{product.id}", product)

        return products

    async def get_products_by_collection(
        self, collection_handle: str, limit: int = 50
    ) -> list[ShopifyProduct]:
        """Get products from a collection by handle.

        Args:
            collection_handle: Collection URL handle
            limit: Maximum number of products to return

        Returns:
            List of products in the collection
        """
        data = await self._execute_graphql(
            PRODUCTS_BY_COLLECTION_QUERY,
            {"handle": collection_handle, "first": limit},
        )

        if data is None:
            logger.warning("Collection query failed for: %s", collection_handle)
            return []

        collection = data.get("data", {}).get("collection")
        if not collection:
            logger.warning("Collection not found: %s", collection_handle)
            return []

        edges = collection.get("products", {}).get("edges", [])
        products = []

        for edge in edges:
            product = self._map_to_product(edge["node"])
            products.append(product)

            # Cache each product
            self._add_to_cache(f"handle:{product.handle}", product)
            self._add_to_cache(f"id:{product.id}", product)

        return products

    def clear_cache(self) -> None:
        """Clear the product cache."""
        self._cache.clear()
        logger.info("Shopify product cache cleared")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.close()

    async def __aenter__(self) -> "ShopifyClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
