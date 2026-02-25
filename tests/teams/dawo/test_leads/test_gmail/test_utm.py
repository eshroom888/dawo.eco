"""Tests for UTM Parameter Injector.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 4: UTM Parameter Injection
"""

import pytest
from uuid import uuid4, UUID
from urllib.parse import urlparse, parse_qs

from teams.dawo.leads.gmail.utm import UTMInjector


@pytest.fixture
def utm_injector() -> UTMInjector:
    """Provide UTMInjector instance."""
    return UTMInjector()


@pytest.fixture
def sample_lead_id() -> UUID:
    """Provide consistent test lead ID."""
    return uuid4()


class TestUTMInjection:
    """Tests for UTM parameter injection."""

    def test_inject_utm_single_url(
        self, utm_injector: UTMInjector, sample_lead_id: UUID
    ) -> None:
        """Test UTM injection into a single URL."""
        body = "Check out https://dawo.no/products for our range."
        result = utm_injector.inject_utm(body, sample_lead_id)

        assert "utm_source=email" in result
        assert "utm_medium=outreach" in result
        assert "utm_campaign=b2b_outreach" in result
        assert f"utm_content={sample_lead_id}" in result

    def test_inject_utm_multiple_urls(
        self, utm_injector: UTMInjector, sample_lead_id: UUID
    ) -> None:
        """Test UTM injection into multiple URLs."""
        body = (
            "Visit https://dawo.no and also https://shop.dawo.no/catalog"
        )
        result = utm_injector.inject_utm(body, sample_lead_id)

        assert result.count("utm_source=email") == 2

    def test_inject_utm_preserves_existing_params(
        self, utm_injector: UTMInjector, sample_lead_id: UUID
    ) -> None:
        """Test UTM injection preserves existing query parameters."""
        body = "See https://dawo.no/page?ref=partner for details."
        result = utm_injector.inject_utm(body, sample_lead_id)

        assert "ref=partner" in result
        assert "utm_source=email" in result

    def test_inject_utm_skips_mailto_links(
        self, utm_injector: UTMInjector, sample_lead_id: UUID
    ) -> None:
        """Test UTM injection skips mailto: links."""
        body = "Email us at mailto:info@dawo.no or visit https://dawo.no"
        result = utm_injector.inject_utm(body, sample_lead_id)

        # mailto should NOT have UTM params
        assert "mailto:info@dawo.no" in result or "utm" not in result.split("mailto")[1].split()[0]
        # https URL should have UTM params
        assert "utm_source=email" in result

    def test_inject_utm_custom_campaign(
        self, utm_injector: UTMInjector, sample_lead_id: UUID
    ) -> None:
        """Test UTM injection with custom campaign name."""
        body = "Visit https://dawo.no"
        result = utm_injector.inject_utm(
            body, sample_lead_id, campaign="winter_2026"
        )
        assert "utm_campaign=winter_2026" in result

    def test_inject_utm_no_urls(
        self, utm_injector: UTMInjector, sample_lead_id: UUID
    ) -> None:
        """Test UTM injection with no URLs in body."""
        body = "This email has no URLs at all."
        result = utm_injector.inject_utm(body, sample_lead_id)
        assert result == body

    def test_inject_utm_url_with_fragment(
        self, utm_injector: UTMInjector, sample_lead_id: UUID
    ) -> None:
        """Test UTM injection with URL containing fragment."""
        body = "See https://dawo.no/page#section for details."
        result = utm_injector.inject_utm(body, sample_lead_id)
        assert "utm_source=email" in result


class TestBuildUTMParams:
    """Tests for UTM parameter building."""

    def test_build_utm_params(self, utm_injector: UTMInjector) -> None:
        """Test building UTM parameter dict."""
        lead_id = uuid4()
        params = utm_injector.build_utm_params(lead_id)
        assert params["utm_source"] == "email"
        assert params["utm_medium"] == "outreach"
        assert params["utm_campaign"] == "b2b_outreach"
        assert params["utm_content"] == str(lead_id)

    def test_build_utm_params_custom_campaign(
        self, utm_injector: UTMInjector
    ) -> None:
        """Test building UTM params with custom campaign."""
        lead_id = uuid4()
        params = utm_injector.build_utm_params(lead_id, campaign="custom")
        assert params["utm_campaign"] == "custom"
