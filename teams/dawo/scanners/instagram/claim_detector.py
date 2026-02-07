"""Health Claim Detector - LLM-powered health claim detection for CleanMarket integration.

Implements the claim detection stage of the Harvester Framework:
    Scanner -> Harvester -> ThemeExtractor -> [ClaimDetector] -> Transformer -> Validator -> Publisher -> Research Pool

The HealthClaimDetector:
    1. Takes harvested posts
    2. Uses LLM (tier="generate") to detect health claims
    3. Classifies claims per EU Health Claims Regulation (EC 1924/2006)
    4. Flags posts for CleanMarket review (Epic 6 integration)

Registration: team_spec.py with tier="generate" (maps to Sonnet at runtime)

Usage:
    # Created by Team Builder with injected dependencies
    detector = HealthClaimDetector(llm_client, compliance_patterns)

    # Execute claim detection
    result = await detector.detect_claims(caption, account_name, is_competitor)
"""

import json
import logging
from typing import Any, Optional, Protocol

from .schemas import (
    HarvestedPost,
    DetectedClaim,
    ClaimDetectionResult,
    ClaimCategory,
)
from .prompts import HEALTH_CLAIM_DETECTION_PROMPT


# Module logger
logger = logging.getLogger(__name__)


class LLMClientProtocol(Protocol):
    """Protocol for LLM client dependency injection."""

    async def generate(self, prompt: str, max_tokens: int = 800) -> str:
        """Generate response from LLM.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens in response

        Returns:
            LLM response text
        """
        ...


class ClaimDetectionError(Exception):
    """Exception raised for claim detection errors.

    Attributes:
        message: Error description
        post_id: Media ID of the post that failed
    """

    def __init__(
        self,
        message: str,
        post_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.post_id = post_id


class HealthClaimDetector:
    """LLM-powered health claim detection for CleanMarket integration.

    Uses tier="generate" (Sonnet) for accurate claim detection.
    Flags competitor content containing health claims for Epic 6 review.

    Categories:
        - TREATMENT: Claims product treats/cures conditions (HIGH severity)
        - PREVENTION: Claims product prevents conditions (HIGH severity)
        - ENHANCEMENT: Claims product improves body functions (MEDIUM severity)
        - GENERAL_WELLNESS: Vague wellness language (LOW severity)

    Features:
        - EU Health Claims Regulation compliance detection
        - Claim severity classification
        - CleanMarket flag generation
        - Competitor content prioritization

    All dependencies are injected via constructor - NEVER loads files directly.

    Attributes:
        _llm: LLM client for claim detection
        _patterns: Compliance patterns from config (optional)
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        compliance_patterns: Optional[dict[str, Any]] = None,
    ):
        """Initialize health claim detector with injected dependencies.

        Args:
            llm_client: LLM client configured for tier="generate"
            compliance_patterns: Optional compliance patterns from config
        """
        self._llm = llm_client
        self._patterns = compliance_patterns or {}

    async def detect_claims(
        self,
        caption: str,
        account_name: str,
        is_competitor: bool,
    ) -> ClaimDetectionResult:
        """Detect potential health claims in Instagram caption.

        Args:
            caption: Full post caption text
            account_name: Instagram account name
            is_competitor: Whether this is a monitored competitor

        Returns:
            ClaimDetectionResult with detected claims and flags

        Raises:
            ClaimDetectionError: If detection fails
        """
        if not caption or not caption.strip():
            # Return clean result for empty captions
            return ClaimDetectionResult(
                claims_detected=[],
                requires_cleanmarket_review=False,
                overall_risk_level="none",
                summary="",
            )

        # Format prompt
        formatted_prompt = HEALTH_CLAIM_DETECTION_PROMPT.format(
            account_name=account_name,
            is_competitor=str(is_competitor).lower(),
            caption=caption[:5000],  # Truncate very long captions
        )

        try:
            # Call LLM
            response = await self._llm.generate(
                prompt=formatted_prompt,
                max_tokens=800,
            )

            # Parse JSON response
            return self._parse_response(response)

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM response as JSON: %s", e)
            # Return clean result on parse failure
            return self._default_result()
        except Exception as e:
            logger.error("Claim detection failed: %s", e)
            raise ClaimDetectionError(f"Failed to detect claims: {e}")

    async def detect_claims_batch(
        self,
        posts: list[HarvestedPost],
    ) -> dict[str, ClaimDetectionResult]:
        """Detect claims for multiple posts.

        Args:
            posts: List of harvested posts

        Returns:
            Dict mapping media_id to ClaimDetectionResult
        """
        results: dict[str, ClaimDetectionResult] = {}

        for post in posts:
            try:
                result = await self.detect_claims(
                    caption=post.caption,
                    account_name=post.account_name,
                    is_competitor=post.is_competitor,
                )
                results[post.media_id] = result
            except ClaimDetectionError as e:
                logger.warning("Claim detection failed for %s: %s", post.media_id, e)
                results[post.media_id] = self._default_result()

        return results

    def _parse_response(self, response: str) -> ClaimDetectionResult:
        """Parse LLM response into ClaimDetectionResult.

        Args:
            response: Raw LLM response text

        Returns:
            ClaimDetectionResult parsed from response
        """
        # Try to extract JSON from response
        try:
            # Handle potential markdown code blocks
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            data = json.loads(text)

            # Parse detected claims
            claims = []
            for claim_data in data.get("claims_detected", []):
                try:
                    category_str = claim_data.get("category", "wellness").lower()
                    category = self._parse_category(category_str)

                    claim = DetectedClaim(
                        claim_text=claim_data.get("claim_text", ""),
                        category=category,
                        confidence=min(1.0, max(0.0, claim_data.get("confidence", 0.5))),
                        severity=claim_data.get("severity", "low"),
                    )
                    claims.append(claim)
                except (ValueError, KeyError) as e:
                    logger.warning("Failed to parse claim: %s", e)
                    continue

            return ClaimDetectionResult(
                claims_detected=claims,
                requires_cleanmarket_review=data.get("requires_cleanmarket_review", len(claims) > 0),
                overall_risk_level=data.get("overall_risk_level", self._determine_risk_level(claims)),
                summary=data.get("summary", ""),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse claim response: %s", e)
            return self._default_result()

    def _parse_category(self, category_str: str) -> ClaimCategory:
        """Parse category string to enum.

        Args:
            category_str: Category string from LLM

        Returns:
            ClaimCategory enum value
        """
        category_map = {
            "treatment": ClaimCategory.TREATMENT,
            "prevention": ClaimCategory.PREVENTION,
            "enhancement": ClaimCategory.ENHANCEMENT,
            "wellness": ClaimCategory.GENERAL_WELLNESS,
            "general_wellness": ClaimCategory.GENERAL_WELLNESS,
        }
        return category_map.get(category_str.lower(), ClaimCategory.GENERAL_WELLNESS)

    def _determine_risk_level(self, claims: list[DetectedClaim]) -> str:
        """Determine overall risk level from claims.

        Args:
            claims: List of detected claims

        Returns:
            Risk level: none, low, medium, high
        """
        if not claims:
            return "none"

        # Check for high severity claims
        severities = [c.severity for c in claims]
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"

    def _default_result(self) -> ClaimDetectionResult:
        """Create default ClaimDetectionResult for failed detections.

        Returns:
            Default ClaimDetectionResult with no claims
        """
        return ClaimDetectionResult(
            claims_detected=[],
            requires_cleanmarket_review=False,
            overall_risk_level="none",
            summary="",
        )
