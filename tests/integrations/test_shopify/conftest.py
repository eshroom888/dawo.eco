"""Test fixtures for Shopify integration tests."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.middleware.retry import RetryConfig, RetryResult


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for Shopify tests."""
    client = AsyncMock()
    return client


@pytest.fixture
def retry_config():
    """Default retry config for tests."""
    return RetryConfig(
        max_retries=3,
        base_delay=0.01,  # Fast tests
        backoff_multiplier=2.0,
        timeout=5.0,
    )


@pytest.fixture
def lions_mane_graphql_response():
    """GraphQL response for Lion's Mane product."""
    return {
        "data": {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/123",
                            "title": "Lion's Mane Extract",
                            "handle": "lions-mane-extract",
                            "descriptionHtml": "<p>Premium lion's mane mushroom extract</p>",
                            "productType": "Extract",
                            "tags": ["lions_mane", "nootropic", "focus"],
                            "variants": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/ProductVariant/456",
                                            "sku": "LM-EXT-60",
                                            "price": "299.00",
                                            "inventoryQuantity": 50,
                                        }
                                    },
                                    {
                                        "node": {
                                            "id": "gid://shopify/ProductVariant/457",
                                            "sku": "LM-EXT-120",
                                            "price": "499.00",
                                            "inventoryQuantity": 30,
                                        }
                                    },
                                ]
                            },
                            "images": {
                                "edges": [
                                    {"node": {"url": "https://cdn.shopify.com/lions-mane.jpg"}}
                                ]
                            },
                            "collections": {
                                "edges": [
                                    {"node": {"handle": "mushroom-extracts"}},
                                    {"node": {"handle": "focus-support"}},
                                ]
                            },
                        }
                    }
                ]
            }
        }
    }


@pytest.fixture
def chaga_graphql_response():
    """GraphQL response for Chaga product (must be classified as supplement)."""
    return {
        "data": {
            "products": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Product/789",
                            "title": "Chaga Elixir",
                            "handle": "chaga-elixir",
                            "descriptionHtml": "<p>Wild-harvested chaga from Siberia</p>",
                            "productType": "Elixir",
                            "tags": ["chaga", "antioxidant", "immune"],
                            "variants": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/ProductVariant/790",
                                            "sku": "CHA-ELX-30",
                                            "price": "349.00",
                                            "inventoryQuantity": 25,
                                        }
                                    }
                                ]
                            },
                            "images": {"edges": []},
                            "collections": {
                                "edges": [{"node": {"handle": "supplements"}}]
                            },
                        }
                    }
                ]
            }
        }
    }


@pytest.fixture
def empty_products_response():
    """GraphQL response with no products."""
    return {"data": {"products": {"edges": []}}}


@pytest.fixture
def collection_response():
    """GraphQL response for collection lookup."""
    return {
        "data": {
            "collectionByHandle": {
                "id": "gid://shopify/Collection/100",
                "handle": "mushroom-extracts",
                "title": "Mushroom Extracts",
            }
        }
    }


@pytest.fixture
def products_by_collection_response():
    """GraphQL response for products in a collection."""
    return {
        "data": {
            "collection": {
                "products": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Product/123",
                                "title": "Lion's Mane Extract",
                                "handle": "lions-mane-extract",
                                "descriptionHtml": "<p>Premium extract</p>",
                                "productType": "Extract",
                                "tags": ["lions_mane"],
                                "variants": {"edges": []},
                                "images": {"edges": []},
                                "collections": {"edges": []},
                            }
                        },
                        {
                            "node": {
                                "id": "gid://shopify/Product/124",
                                "title": "Reishi Extract",
                                "handle": "reishi-extract",
                                "descriptionHtml": "<p>Premium reishi</p>",
                                "productType": "Extract",
                                "tags": ["reishi"],
                                "variants": {"edges": []},
                                "images": {"edges": []},
                                "collections": {"edges": []},
                            }
                        },
                    ]
                }
            }
        }
    }
