"""Enrichment Scoring for Lead Enrichment.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 6: Implement Enrichment Scoring

Calculates:
- Confidence score (0-10): Data quality/completeness
- Lead score (0-100): Lead qualification score
"""

import logging
from typing import Optional

from teams.dawo.leads.enrichment.config import EnrichmentConfig
from teams.dawo.leads.enrichment.schemas import (
    EnrichmentResult,
    ScoreBreakdown,
)


logger = logging.getLogger(__name__)


# Target industries for industry match scoring
TARGET_INDUSTRIES = [
    "health",
    "wellness",
    "organic",
    "natural",
    "supplement",
    "food",
    "retail",
    "helsekost",  # Norwegian
]

# Target countries for geographic fit
TARGET_COUNTRIES = [
    "norway",
    "sweden",
    "denmark",
    "finland",
    "iceland",
]

# Company size scoring (prefer small-medium retailers)
COMPANY_SIZE_SCORES = {
    "1-10": 15,
    "11-50": 20,
    "51-200": 15,
    "201-500": 10,
    "501-1000": 5,
    "1001+": 2,
}


class EnrichmentScorer:
    """Scorer for lead enrichment results.

    Calculates two scores:
    1. Confidence score (0-10): How complete/reliable is the data
    2. Lead score (0-100): How qualified is this lead for outreach

    Accepts configuration via dependency injection.
    """

    def __init__(self, config: EnrichmentConfig) -> None:
        """Initialize the scorer.

        Args:
            config: Enrichment configuration with score weights
        """
        self._config = config

    def calculate_confidence(
        self,
        result: EnrichmentResult,
        has_verified_email: bool = False,
        has_decision_maker: bool = False,
    ) -> tuple[float, ScoreBreakdown]:
        """Calculate confidence score for enrichment result.

        Scoring components (total max = 10):
        - Verified email: +2
        - Business description: +2
        - Social media presence: +1
        - Decision maker contact: +1
        - Industry match: +1
        - Product categories: +1
        - Personalization hooks: +1
        - Website accessible: +1

        Args:
            result: Enrichment result to score
            has_verified_email: Whether a verified email exists
            has_decision_maker: Whether a decision maker contact exists

        Returns:
            Tuple of (total_score, score_breakdown)
        """
        weights = self._config.score_weights
        breakdown = ScoreBreakdown()

        # Verified email (+2)
        if has_verified_email:
            breakdown.verified_email = weights.verified_email

        # Business description (+2)
        if result.website_analysis and result.website_analysis.description:
            breakdown.business_description = weights.business_description

        # Website accessible (+1)
        if result.website_analysis and result.website_analysis.accessible:
            breakdown.website_accessible = weights.website_accessible

        # Social media presence (+1)
        if result.social_profiles:
            breakdown.social_presence = weights.social_presence

        # Decision maker contact (+1)
        if has_decision_maker:
            breakdown.decision_maker = weights.decision_maker

        # Industry match (+1)
        if result.company_enrichment and result.company_enrichment.industry:
            industry_lower = result.company_enrichment.industry.lower()
            if any(target in industry_lower for target in TARGET_INDUSTRIES):
                breakdown.industry_match = weights.industry_match

        # Product categories (+1)
        if result.business_insights and result.business_insights.product_categories:
            breakdown.product_categories = weights.product_categories

        # Personalization hooks (+1)
        if result.personalization_hooks:
            breakdown.personalization_hooks = weights.personalization_hooks

        total = breakdown.total
        return total, breakdown

    def calculate_lead_score(
        self,
        result: EnrichmentResult,
        industry: Optional[str] = None,
        country: Optional[str] = None,
        company_size: Optional[str] = None,
    ) -> float:
        """Calculate lead qualification score.

        Scoring components (total max = 100):
        - Industry relevance: 0-30
        - Company size fit: 0-20
        - Geographic fit: 0-20
        - Engagement potential: 0-15
        - Data completeness: 0-15

        Args:
            result: Enrichment result to score
            industry: Lead's industry (optional, enrichment data preferred)
            country: Lead's country (optional)
            company_size: Lead's company size (optional)

        Returns:
            Lead score from 0 to 100
        """
        weights = self._config.lead_score_weights
        score = 0.0

        # Industry relevance (0-30)
        effective_industry = industry or ""
        if result.company_enrichment and result.company_enrichment.industry:
            effective_industry = result.company_enrichment.industry

        industry_lower = effective_industry.lower()
        industry_matches = sum(
            1 for target in TARGET_INDUSTRIES if target in industry_lower
        )
        score += min(industry_matches * 10, weights.industry_relevance_max)

        # Company size fit (0-20)
        headcount = company_size
        if result.company_enrichment and result.company_enrichment.headcount:
            headcount = result.company_enrichment.headcount

        if headcount:
            for size_range, points in COMPANY_SIZE_SCORES.items():
                if size_range in headcount or headcount in size_range:
                    score += min(points, weights.company_size_max)
                    break

        # Geographic fit (0-20)
        effective_country = (country or "").lower()
        if any(target in effective_country for target in TARGET_COUNTRIES):
            score += weights.geographic_max

        # Engagement potential (0-15)
        if result.social_profiles:
            # Has social presence
            score += 5
            # Check for active presence
            active_count = sum(1 for p in result.social_profiles if p.active)
            score += min(active_count * 5, 10)

        # Data completeness (0-15)
        completeness = 0
        if result.website_analysis and result.website_analysis.accessible:
            completeness += 3
        if result.business_insights:
            completeness += 3
        if result.company_enrichment:
            completeness += 3
        if result.personalization_hooks:
            completeness += 3
        if result.social_profiles:
            completeness += 3
        score += min(completeness, weights.data_completeness_max)

        return min(score, 100.0)
