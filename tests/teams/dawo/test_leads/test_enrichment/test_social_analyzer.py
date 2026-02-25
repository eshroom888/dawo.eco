"""Tests for SocialAnalyzer.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 5: Implement Social Media Analyzer
"""

import pytest
from unittest.mock import AsyncMock


class TestSocialAnalyzerInit:
    """Tests for SocialAnalyzer initialization."""

    def test_creates_instance(self) -> None:
        """Test SocialAnalyzer can be instantiated."""
        from teams.dawo.leads.enrichment.social_analyzer import SocialAnalyzer

        analyzer = SocialAnalyzer()
        assert analyzer is not None


class TestAnalyzeInstagram:
    """Tests for analyze_instagram method."""

    @pytest.mark.asyncio
    async def test_analyze_instagram_returns_profile(self) -> None:
        """Test Instagram analysis returns profile data."""
        from teams.dawo.leads.enrichment.social_analyzer import SocialAnalyzer

        analyzer = SocialAnalyzer()
        result = await analyzer.analyze_instagram("@healthstore_no")

        # Returns a SocialProfile even if minimal data
        assert result is not None
        assert result.platform == "instagram"
        assert result.handle == "@healthstore_no"

    @pytest.mark.asyncio
    async def test_analyze_instagram_returns_none_for_empty_handle(self) -> None:
        """Test returns None for empty handle."""
        from teams.dawo.leads.enrichment.social_analyzer import SocialAnalyzer

        analyzer = SocialAnalyzer()
        result = await analyzer.analyze_instagram("")

        assert result is None


class TestAnalyzeLinkedin:
    """Tests for analyze_linkedin method."""

    @pytest.mark.asyncio
    async def test_analyze_linkedin_returns_profile(self) -> None:
        """Test LinkedIn analysis returns profile data."""
        from teams.dawo.leads.enrichment.social_analyzer import SocialAnalyzer

        analyzer = SocialAnalyzer()
        result = await analyzer.analyze_linkedin("linkedin.com/company/healthstore")

        assert result is not None
        assert result.platform == "linkedin"
        assert result.url == "linkedin.com/company/healthstore"

    @pytest.mark.asyncio
    async def test_analyze_linkedin_with_company_data(self) -> None:
        """Test LinkedIn analysis with Hunter.io company data."""
        from teams.dawo.leads.enrichment.social_analyzer import SocialAnalyzer

        analyzer = SocialAnalyzer()
        result = await analyzer.analyze_linkedin(
            "linkedin.com/company/healthstore",
            company_data={"headcount": "11-50"},
        )

        assert result.employees == "11-50"


class TestAnalyzeFacebook:
    """Tests for analyze_facebook method."""

    @pytest.mark.asyncio
    async def test_analyze_facebook_returns_profile(self) -> None:
        """Test Facebook analysis returns profile data."""
        from teams.dawo.leads.enrichment.social_analyzer import SocialAnalyzer

        analyzer = SocialAnalyzer()
        result = await analyzer.analyze_facebook("facebook.com/healthstoreno")

        assert result is not None
        assert result.platform == "facebook"


class TestPresenceScore:
    """Tests for presence score calculation."""

    @pytest.mark.asyncio
    async def test_calculate_presence_score_with_all_platforms(self) -> None:
        """Test presence score with all platforms present."""
        from teams.dawo.leads.enrichment.social_analyzer import SocialAnalyzer
        from teams.dawo.leads.enrichment.schemas import SocialProfile

        analyzer = SocialAnalyzer()

        profiles = [
            SocialProfile(platform="instagram", followers=5000, active=True),
            SocialProfile(platform="linkedin", employees="50-100"),
            SocialProfile(platform="facebook", active=True),
        ]

        score = analyzer.calculate_presence_score(profiles)

        # With all platforms and good engagement, should be high
        assert score >= 6.0

    @pytest.mark.asyncio
    async def test_calculate_presence_score_empty_list(self) -> None:
        """Test presence score with no profiles."""
        from teams.dawo.leads.enrichment.social_analyzer import SocialAnalyzer

        analyzer = SocialAnalyzer()
        score = analyzer.calculate_presence_score([])

        assert score == 0.0

    @pytest.mark.asyncio
    async def test_calculate_presence_score_single_platform(self) -> None:
        """Test presence score with single platform."""
        from teams.dawo.leads.enrichment.social_analyzer import SocialAnalyzer
        from teams.dawo.leads.enrichment.schemas import SocialProfile

        analyzer = SocialAnalyzer()

        profiles = [
            SocialProfile(platform="instagram", followers=1000, active=True),
        ]

        score = analyzer.calculate_presence_score(profiles)

        # Single platform should give partial score
        assert 2.0 <= score <= 5.0
