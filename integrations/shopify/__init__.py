"""Shopify integration module with MCP caching layer.

Provides product data retrieval, caching, and UTM parameter generation
for content generators per FR48 requirements.

Note: Imports are lazy to avoid circular imports with teams.dawo.middleware.
Import directly: `from integrations.shopify.client import ShopifyClient`
"""

# UTM utilities don't have circular import issues - load immediately
from integrations.shopify.utm import (
    UTMParams,
    build_short_link_url,
    build_utm_url,
    get_product_url_with_utm,
)


def __getattr__(name: str):
    """Lazy import to avoid circular imports with teams.dawo.middleware."""
    _client_names = {"ShopifyClient", "ShopifyClientProtocol", "ShopifyProduct", "ProductPlaceholder"}
    _order_names = {"ShopifyOrder", "OrderLineItem", "CustomerVisit", "OrderAttribution"}

    if name in _client_names:
        from integrations.shopify.client import (
            ShopifyClient,
            ShopifyClientProtocol,
            ShopifyProduct,
            ProductPlaceholder,
        )
        return {
            "ShopifyClient": ShopifyClient,
            "ShopifyClientProtocol": ShopifyClientProtocol,
            "ShopifyProduct": ShopifyProduct,
            "ProductPlaceholder": ProductPlaceholder,
        }[name]
    if name in _order_names:
        from integrations.shopify.orders import (
            ShopifyOrder,
            OrderLineItem,
            CustomerVisit,
            OrderAttribution,
        )
        return {
            "ShopifyOrder": ShopifyOrder,
            "OrderLineItem": OrderLineItem,
            "CustomerVisit": CustomerVisit,
            "OrderAttribution": OrderAttribution,
        }[name]
    raise AttributeError(f"module 'integrations.shopify' has no attribute '{name}'")


__all__ = [
    # Client
    "ShopifyClient",
    "ShopifyClientProtocol",
    # Data models
    "ShopifyProduct",
    "ProductPlaceholder",
    # Order DTOs (Story 7-3)
    "ShopifyOrder",
    "OrderLineItem",
    "CustomerVisit",
    "OrderAttribution",
    # UTM utilities
    "UTMParams",
    "build_short_link_url",
    "build_utm_url",
    "get_product_url_with_utm",
]
