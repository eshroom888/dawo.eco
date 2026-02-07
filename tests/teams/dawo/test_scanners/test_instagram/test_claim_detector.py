"""Tests for HealthClaimDetector.

Tests the health claim detection stage with mocked LLM responses.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.instagram import (
    HealthClaimDetector,
    ClaimDetectionError,
    ClaimDetectionResult,
    DetectedClaim,
    ClaimCategory,
    HarvestedPost,
)


class TestHealthClaimDetector:
    """Test suite for HealthClaimDetector."""

    @pytest.fixture
    def mock_llm_client_with_claims(self):
        """Mock LLM client that returns claims."""
        client = AsyncMock()
        client.generate.return_value = json.dumps({
            "claims_detected": [
                {
                    "claim_text": "boosts brain power",
                    "category": "enhancement",
                    "confidence": 0.9,
                    "severity": "medium"
                }
            ],
            "requires_cleanmarket_review": True,
            "overall_risk_level": "medium",
            "summary": "Enhancement claim detected"
        })
        return client

    @pytest.fixture
    def mock_llm_client_no_claims(self):
        """Mock LLM client that returns no claims."""
        client = AsyncMock()
        client.generate.return_value = json.dumps({
            "claims_detected": [],
            "requires_cleanmarket_review": False,
            "overall_risk_level": "none",
            "summary": ""
        })
        return client

    @pytest.fixture
    def detector_with_claims(self, mock_llm_client_with_claims):
        """Create detector that will find claims."""
        return HealthClaimDetector(llm_client=mock_llm_client_with_claims)

    @pytest.fixture
    def detector_no_claims(self, mock_llm_client_no_claims):
        """Create detector that will find no claims."""
        return HealthClaimDetector(llm_client=mock_llm_client_no_claims)

    @pytest.mark.asyncio
    async def test_detect_claims_returns_result(self, detector_with_claims):
        """Test that detect_claims returns ClaimDetectionResult."""
        result = await detector_with_claims.detect_claims(
            caption="This boosts brain power!",
            account_name="competitor_brand",
            is_competitor=True,
        )

        assert isinstance(result, ClaimDetectionResult)

    @pytest.mark.asyncio
    async def test_detect_claims_finds_claims(self, detector_with_claims):
        """Test that claims are properly detected and parsed."""
        result = await detector_with_claims.detect_claims(
            caption="This boosts brain power!",
            account_name="competitor_brand",
            is_competitor=True,
        )

        assert len(result.claims_detected) == 1
        assert result.claims_detected[0].claim_text == "boosts brain power"
        assert result.claims_detected[0].category == ClaimCategory.ENHANCEMENT
        assert result.requires_cleanmarket_review == True
        assert result.overall_risk_level == "medium"

    @pytest.mark.asyncio
    async def test_detect_claims_no_claims(self, detector_no_claims):
        """Test clean content with no claims."""
        result = await detector_no_claims.detect_claims(
            caption="Enjoying my morning routine!",
            account_name="user",
            is_competitor=False,
        )

        assert len(result.claims_detected) == 0
        assert result.requires_cleanmarket_review == False
        assert result.overall_risk_level == "none"

    @pytest.mark.asyncio
    async def test_detect_claims_empty_caption(self, detector_with_claims):
        """Test empty caption returns clean result."""
        result = await detector_with_claims.detect_claims(
            caption="",
            account_name="user",
            is_competitor=False,
        )

        assert len(result.claims_detected) == 0
        assert result.requires_cleanmarket_review == False

    @pytest.mark.asyncio
    async def test_detect_claims_handles_json_error(self, detector_with_claims, mock_llm_client_with_claims):
        """Test that invalid JSON response returns default result."""
        mock_llm_client_with_claims.generate.return_value = "Not valid JSON"

        result = await detector_with_claims.detect_claims(
            caption="Some content",
            account_name="user",
            is_competitor=False,
        )

        assert len(result.claims_detected) == 0

    @pytest.mark.asyncio
    async def test_detect_claims_batch(self, detector_with_claims):
        """Test batch claim detection."""
        posts = [
            HarvestedPost(
                media_id="post1",
                permalink="https://example.com/1",
                caption="Boosts brain power!",
                hashtags=["lionsmane"],
                likes=100,
                comments=10,
                media_type="IMAGE",
                account_name="competitor",
                account_type="business",
                timestamp=datetime.now(timezone.utc),
                is_competitor=True,
            ),
        ]

        results = await detector_with_claims.detect_claims_batch(posts)

        assert "post1" in results
        assert isinstance(results["post1"], ClaimDetectionResult)


class TestDetectedClaim:
    """Test suite for DetectedClaim dataclass."""

    def test_valid_claim(self):
        """Test creating valid DetectedClaim."""
        claim = DetectedClaim(
            claim_text="boosts immunity",
            category=ClaimCategory.ENHANCEMENT,
            confidence=0.9,
            severity="medium",
        )

        assert claim.claim_text == "boosts immunity"
        assert claim.category == ClaimCategory.ENHANCEMENT

    def test_invalid_confidence(self):
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="confidence must be 0-1"):
            DetectedClaim(
                claim_text="test",
                category=ClaimCategory.ENHANCEMENT,
                confidence=1.5,  # Invalid
                severity="medium",
            )

    def test_invalid_severity(self):
        """Test that invalid severity raises ValueError."""
        with pytest.raises(ValueError, match="severity must be high/medium/low"):
            DetectedClaim(
                claim_text="test",
                category=ClaimCategory.ENHANCEMENT,
                confidence=0.5,
                severity="invalid",  # Invalid
            )


class TestClaimDetectionResult:
    """Test suite for ClaimDetectionResult dataclass."""

    def test_valid_result(self):
        """Test creating valid ClaimDetectionResult."""
        result = ClaimDetectionResult(
            claims_detected=[],
            requires_cleanmarket_review=False,
            overall_risk_level="none",
            summary="",
        )

        assert result.overall_risk_level == "none"

    def test_invalid_risk_level(self):
        """Test that invalid risk level raises ValueError."""
        with pytest.raises(ValueError, match="overall_risk_level must be one of"):
            ClaimDetectionResult(
                claims_detected=[],
                requires_cleanmarket_review=False,
                overall_risk_level="invalid",  # Invalid
                summary="",
            )


class TestClaimCategory:
    """Test suite for ClaimCategory enum."""

    def test_category_values(self):
        """Test that all expected categories exist."""
        assert ClaimCategory.TREATMENT.value == "treatment"
        assert ClaimCategory.PREVENTION.value == "prevention"
        assert ClaimCategory.ENHANCEMENT.value == "enhancement"
        assert ClaimCategory.GENERAL_WELLNESS.value == "wellness"
