"""Tests for BusinessAnalyzer.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 3: Implement LLM-based Business Analyzer
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4


class TestBusinessAnalyzerInit:
    """Tests for BusinessAnalyzer initialization."""

    def test_accepts_llm_client_via_injection(self) -> None:
        """Test BusinessAnalyzer accepts LLM client via DI."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        llm_client = AsyncMock()
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)

        assert analyzer._llm is llm_client
        assert analyzer._config is config


class TestAnalyzeBusiness:
    """Tests for analyze_business method."""

    @pytest.mark.asyncio
    async def test_analyze_business_extracts_focus_areas(self) -> None:
        """Test analysis extracts business focus areas."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        # Mock LLM response
        llm_response = {
            "focus_areas": ["organic products", "health foods", "local producers"],
            "target_demographics": "health-conscious consumers, 25-55",
            "product_categories": ["supplements", "organic groceries", "wellness"],
            "wellness_positioning": "strong",
        }

        llm_client = AsyncMock()
        llm_client.generate_json.return_value = llm_response
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)
        result = await analyzer.analyze_business(
            content="We sell organic health foods and supplements...",
            company="Health Store AS",
        )

        assert "organic products" in result.focus_areas
        assert result.wellness_positioning == "strong"

    @pytest.mark.asyncio
    async def test_analyze_business_detects_product_categories(self) -> None:
        """Test analysis detects product categories."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        llm_response = {
            "focus_areas": ["wellness"],
            "target_demographics": "adults",
            "product_categories": ["mushroom supplements", "adaptogens", "vitamins"],
            "wellness_positioning": "strong",
        }

        llm_client = AsyncMock()
        llm_client.generate_json.return_value = llm_response
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)
        result = await analyzer.analyze_business(
            content="Specializing in mushroom supplements and adaptogens...",
            company="Wellness Shop",
        )

        assert "mushroom supplements" in result.product_categories
        assert "adaptogens" in result.product_categories

    @pytest.mark.asyncio
    async def test_analyze_business_handles_llm_error(self) -> None:
        """Test graceful handling of LLM errors."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        llm_client = AsyncMock()
        llm_client.generate_json.side_effect = Exception("LLM unavailable")
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)
        result = await analyzer.analyze_business(
            content="Some content",
            company="Test Company",
        )

        # Should return empty insights, not raise
        assert result.focus_areas == []
        assert result.wellness_positioning is None

    @pytest.mark.asyncio
    async def test_analyze_business_passes_correct_prompt(self) -> None:
        """Test correct prompt is passed to LLM."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        llm_response = {
            "focus_areas": [],
            "target_demographics": None,
            "product_categories": [],
            "wellness_positioning": None,
        }

        llm_client = AsyncMock()
        llm_client.generate_json.return_value = llm_response
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)
        await analyzer.analyze_business(
            content="Test content about the business",
            company="Test Company",
        )

        # Verify LLM was called with expected content
        call_args = llm_client.generate_json.call_args
        assert "Test Company" in str(call_args)


class TestIdentifyHooks:
    """Tests for identify_hooks method."""

    @pytest.mark.asyncio
    async def test_identify_hooks_finds_competitor_hook(self) -> None:
        """Test identification of competitor product hooks."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import BusinessInsights

        llm_response = [
            {"type": "competitor", "detail": "Carries HealthWorks mushroom products"},
            {"type": "focus", "detail": "Strong organic focus"},
        ]

        llm_client = AsyncMock()
        llm_client.generate_json.return_value = llm_response
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)

        insights = BusinessInsights(
            focus_areas=["organic products"],
            product_categories=["mushroom supplements"],
        )

        lead_data = {"company": "Health Store", "country": "Norway"}

        hooks = await analyzer.identify_hooks(insights, lead_data)

        assert len(hooks) >= 1
        hook_types = [h.hook_type.value for h in hooks]
        assert "competitor" in hook_types

    @pytest.mark.asyncio
    async def test_identify_hooks_finds_focus_hook(self) -> None:
        """Test identification of business focus hooks."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import BusinessInsights

        llm_response = [
            {"type": "focus", "detail": "Strong organic and sustainable focus"},
            {"type": "values", "detail": "Nordic wellness community"},
        ]

        llm_client = AsyncMock()
        llm_client.generate_json.return_value = llm_response
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)

        insights = BusinessInsights(
            focus_areas=["organic", "sustainable"],
            wellness_positioning="strong",
        )

        hooks = await analyzer.identify_hooks(insights, {"company": "Eco Store"})

        hook_types = [h.hook_type.value for h in hooks]
        assert "focus" in hook_types

    @pytest.mark.asyncio
    async def test_identify_hooks_returns_empty_on_error(self) -> None:
        """Test graceful handling when LLM fails."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import BusinessInsights

        llm_client = AsyncMock()
        llm_client.generate_json.side_effect = Exception("LLM error")
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)
        hooks = await analyzer.identify_hooks(
            BusinessInsights(), {"company": "Test"}
        )

        assert hooks == []


class TestDetectExistingCustomer:
    """Tests for detect_existing_customer method."""

    def test_detects_dawo_keyword(self) -> None:
        """Test detection of DAWO brand mentions."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        llm_client = AsyncMock()
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)

        content = "We proudly carry DAWO mushroom supplements in our store."
        result = analyzer.detect_existing_customer(content)

        assert result is True

    def test_detects_dawo_product_names(self) -> None:
        """Test detection of DAWO product names."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        llm_client = AsyncMock()
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)

        content = "Featured products: Lion's Mane DAWO, organic supplements..."
        result = analyzer.detect_existing_customer(content)

        assert result is True

    def test_detects_dawo_eco_domain(self) -> None:
        """Test detection of dawo.eco domain reference."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        llm_client = AsyncMock()
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)

        content = "Visit our partners at dawo.eco for more information."
        result = analyzer.detect_existing_customer(content)

        assert result is True

    def test_no_detection_without_dawo(self) -> None:
        """Test no false positive when DAWO not mentioned."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        llm_client = AsyncMock()
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)

        content = "We sell lion's mane and reishi mushroom supplements."
        result = analyzer.detect_existing_customer(content)

        assert result is False

    def test_case_insensitive_detection(self) -> None:
        """Test case insensitive keyword detection."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        llm_client = AsyncMock()
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)

        # Various case variations
        assert analyzer.detect_existing_customer("DAWO products") is True
        assert analyzer.detect_existing_customer("dawo supplements") is True
        assert analyzer.detect_existing_customer("Dawo.Eco") is True

    def test_handles_empty_content(self) -> None:
        """Test handling of empty content."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        llm_client = AsyncMock()
        config = EnrichmentConfig()

        analyzer = BusinessAnalyzer(llm_client=llm_client, config=config)

        assert analyzer.detect_existing_customer("") is False
        assert analyzer.detect_existing_customer(None) is False


class TestLLMClientProtocol:
    """Tests for LLM client protocol."""

    def test_protocol_defines_generate_json(self) -> None:
        """Test protocol defines expected method."""
        from teams.dawo.leads.enrichment.business_analyzer import LLMClientProtocol

        # Protocol should define generate_json method
        assert hasattr(LLMClientProtocol, "generate_json")
