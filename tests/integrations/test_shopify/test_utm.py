"""Unit tests for UTM parameter builder."""

import pytest

from integrations.shopify.utm import (
    UTMParams,
    build_utm_url,
    get_product_url_with_utm,
)


class TestUTMParams:
    """Test UTMParams dataclass."""

    def test_default_values(self):
        """UTMParams has sensible defaults."""
        params = UTMParams()
        assert params.source == "instagram"
        assert params.medium == "post"
        assert params.campaign == ""
        assert params.content == ""
        assert params.term == ""

    def test_to_dict_excludes_empty(self):
        """to_dict excludes empty string values."""
        params = UTMParams(source="instagram", medium="story")
        result = params.to_dict()

        assert "utm_source" in result
        assert "utm_medium" in result
        assert "utm_campaign" not in result
        assert "utm_content" not in result
        assert "utm_term" not in result

    def test_to_dict_includes_all_set_values(self):
        """to_dict includes all non-empty values."""
        params = UTMParams(
            source="instagram",
            medium="reel",
            campaign="feed_post",
            content="post123",
            term="mushrooms",
        )
        result = params.to_dict()

        assert result["utm_source"] == "instagram"
        assert result["utm_medium"] == "reel"
        assert result["utm_campaign"] == "feed_post"
        assert result["utm_content"] == "post123"
        assert result["utm_term"] == "mushrooms"


class TestBuildUtmUrl:
    """Test build_utm_url function."""

    def test_simple_url(self):
        """Build UTM URL from simple base URL."""
        result = build_utm_url(
            base_url="https://dawo.no/products/lions-mane",
            content_type="feed_post",
            post_id="abc123",
        )

        assert "utm_source=instagram" in result
        assert "utm_medium=post" in result
        assert "utm_campaign=feed_post" in result
        assert "utm_content=abc123" in result

    def test_custom_source_and_medium(self):
        """Custom source and medium override defaults."""
        result = build_utm_url(
            base_url="https://dawo.no/products/lions-mane",
            content_type="story",
            post_id="story456",
            source="facebook",
            medium="story",
        )

        assert "utm_source=facebook" in result
        assert "utm_medium=story" in result

    def test_preserves_existing_query_params(self):
        """Existing query params are preserved."""
        result = build_utm_url(
            base_url="https://dawo.no/products/lions-mane?variant=123",
            content_type="feed_post",
            post_id="abc123",
        )

        assert "variant=123" in result
        assert "utm_source=instagram" in result

    def test_url_encodes_special_characters(self):
        """Special characters in content_type and post_id are URL-encoded."""
        result = build_utm_url(
            base_url="https://dawo.no/products/lions-mane",
            content_type="feed post",
            post_id="abc/123",
        )

        # Spaces and slashes should be encoded
        assert "feed+post" in result or "feed%20post" in result
        assert "abc%2F123" in result

    def test_preserves_fragment(self):
        """URL fragment is preserved."""
        result = build_utm_url(
            base_url="https://dawo.no/products/lions-mane#reviews",
            content_type="feed_post",
            post_id="abc123",
        )

        assert result.endswith("#reviews")

    def test_handles_url_without_scheme(self):
        """URL without scheme is handled correctly."""
        result = build_utm_url(
            base_url="//dawo.no/products/lions-mane",
            content_type="feed_post",
            post_id="abc123",
        )

        assert "utm_source=instagram" in result


class TestGetProductUrlWithUtm:
    """Test get_product_url_with_utm convenience function."""

    def test_uses_instagram_defaults(self):
        """Uses Instagram as default source."""
        result = get_product_url_with_utm(
            product_url="https://dawo.no/products/lions-mane",
            content_type="feed_post",
            post_id="abc123",
        )

        assert "utm_source=instagram" in result
        assert "utm_medium=post" in result

    def test_includes_campaign_and_content(self):
        """Includes content_type as campaign and post_id as content."""
        result = get_product_url_with_utm(
            product_url="https://dawo.no/products/chaga-elixir",
            content_type="story",
            post_id="story789",
        )

        assert "utm_campaign=story" in result
        assert "utm_content=story789" in result
