"""Data schemas for Lead Enrichment.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment

Defines data structures for the enrichment pipeline:
- PersonalizationHook: Outreach personalization data
- WebsiteAnalysis: Website content analysis
- BusinessInsights: LLM-extracted business insights
- SocialProfile: Social media presence data
- CompanyEnrichment: Hunter.io company data
- EnrichmentResult: Complete enrichment output
- ScoreBreakdown: Confidence score components
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Optional
from uuid import UUID


class PersonalizationHookType(str, Enum):
    """Types of personalization hooks for outreach.

    Values:
        COMPETITOR: Carries competitor products
        FOCUS: Business focus alignment
        AUDIENCE: Target audience match
        LOCATION: Geographic relevance
        PRODUCT: Product category fit
        VALUES: Shared values (organic, sustainable)
        GROWTH: Expansion/growth indicators
    """

    COMPETITOR = "competitor"
    FOCUS = "focus"
    AUDIENCE = "audience"
    LOCATION = "location"
    PRODUCT = "product"
    VALUES = "values"
    GROWTH = "growth"


@dataclass
class PersonalizationHook:
    """Personalization hook for outreach messages.

    Represents a specific detail that can be used to personalize
    B2B outreach communications.

    Attributes:
        hook_type: Type of personalization hook
        detail: Specific detail for personalization
    """

    hook_type: PersonalizationHookType
    detail: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "type": self.hook_type.value,
            "detail": self.detail,
        }


@dataclass
class WebsiteAnalysis:
    """Website content analysis result.

    Contains extracted information from a company website.

    Attributes:
        domain: Website domain analyzed
        accessible: Whether website was accessible
        description: Extracted business description
        content: Raw text content for LLM analysis
        mushroom_keywords_found: Detected mushroom-related keywords
        supplement_section: Whether supplements section was found
    """

    domain: str
    accessible: bool = False
    description: Optional[str] = None
    content: Optional[str] = None
    mushroom_keywords_found: list[str] = field(default_factory=list)
    supplement_section: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "accessible": self.accessible,
            "description": self.description,
            "mushroom_keywords_found": self.mushroom_keywords_found,
            "supplement_section": self.supplement_section,
        }


@dataclass
class BusinessInsights:
    """LLM-extracted business insights.

    Contains structured insights about a business extracted
    by LLM analysis of website content.

    Attributes:
        focus_areas: Business focus areas
        target_demographics: Target customer demographics
        product_categories: Product categories carried
        wellness_positioning: Wellness positioning strength
    """

    focus_areas: list[str] = field(default_factory=list)
    target_demographics: Optional[str] = None
    product_categories: list[str] = field(default_factory=list)
    wellness_positioning: Optional[str] = None  # weak/moderate/strong

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "focus_areas": self.focus_areas,
            "target_demographics": self.target_demographics,
            "product_categories": self.product_categories,
            "wellness_positioning": self.wellness_positioning,
        }


@dataclass
class SocialProfile:
    """Social media presence data.

    Contains information about a company's social media presence.

    Attributes:
        platform: Social media platform name
        handle: Profile handle/username
        url: Profile URL
        followers: Follower count (if available)
        employees: Employee count indicator (LinkedIn)
        active: Whether profile is actively maintained
    """

    platform: str
    handle: Optional[str] = None
    url: Optional[str] = None
    followers: Optional[int] = None
    employees: Optional[str] = None
    active: Optional[bool] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        result = {"platform": self.platform}
        if self.handle:
            result["handle"] = self.handle
        if self.url:
            result["url"] = self.url
        if self.followers is not None:
            result["followers"] = self.followers
        if self.employees:
            result["employees"] = self.employees
        if self.active is not None:
            result["active"] = self.active
        return result


@dataclass
class CompanyEnrichment:
    """Hunter.io company enrichment data.

    Contains company information from Hunter.io API.

    Attributes:
        domain: Company domain
        organization: Organization name
        headcount: Employee count range
        industry: Industry classification
        email_patterns: Common email patterns at company
    """

    domain: str
    organization: Optional[str] = None
    headcount: Optional[str] = None
    industry: Optional[str] = None
    email_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "domain": self.domain,
            "organization": self.organization,
            "headcount": self.headcount,
            "industry": self.industry,
            "email_patterns": self.email_patterns,
        }


@dataclass
class ScoreBreakdown:
    """Confidence score breakdown by component.

    Tracks individual scoring components for transparency.

    Attributes:
        verified_email: Score for verified email (+2)
        business_description: Score for business description (+2)
        social_presence: Score for social media presence (+1)
        decision_maker: Score for decision maker contact (+1)
        industry_match: Score for industry match (+1)
        product_categories: Score for product categories (+1)
        personalization_hooks: Score for personalization hooks (+1)
        website_accessible: Score for accessible website (+1)
    """

    verified_email: float = 0.0
    business_description: float = 0.0
    social_presence: float = 0.0
    decision_maker: float = 0.0
    industry_match: float = 0.0
    product_categories: float = 0.0
    personalization_hooks: float = 0.0
    website_accessible: float = 0.0

    @property
    def total(self) -> float:
        """Calculate total confidence score."""
        return (
            self.verified_email
            + self.business_description
            + self.social_presence
            + self.decision_maker
            + self.industry_match
            + self.product_categories
            + self.personalization_hooks
            + self.website_accessible
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "verified_email": self.verified_email,
            "business_description": self.business_description,
            "social_presence": self.social_presence,
            "decision_maker": self.decision_maker,
            "industry_match": self.industry_match,
            "product_categories": self.product_categories,
            "personalization_hooks": self.personalization_hooks,
            "website_accessible": self.website_accessible,
        }


@dataclass
class EnrichmentResult:
    """Complete enrichment result for a lead.

    Aggregates all enrichment data from various sources.

    Attributes:
        lead_id: UUID of the lead being enriched
        confidence_score: Overall confidence score (0-10)
        lead_score: Lead qualification score (0-100)
        score_breakdown: Detailed score components
        website_analysis: Website analysis results
        business_insights: LLM-extracted insights
        company_enrichment: Hunter.io company data
        social_profiles: Social media presence data
        personalization_hooks: Identified personalization hooks
        decision_makers: Decision-maker contacts from Hunter.io
        is_existing_customer: Whether lead is existing DAWO customer
        errors: Errors encountered during enrichment
        enriched_at: Timestamp of enrichment
    """

    lead_id: UUID
    confidence_score: float = 0.0
    lead_score: float = 0.0
    score_breakdown: Optional[ScoreBreakdown] = None
    website_analysis: Optional[WebsiteAnalysis] = None
    business_insights: Optional[BusinessInsights] = None
    company_enrichment: Optional[CompanyEnrichment] = None
    social_profiles: list[SocialProfile] = field(default_factory=list)
    personalization_hooks: list[PersonalizationHook] = field(default_factory=list)
    decision_makers: list[Any] = field(default_factory=list)
    is_existing_customer: bool = False
    errors: list[str] = field(default_factory=list)
    enriched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSONB storage.

        Returns:
            Dict matching the enrichment_data schema in Lead model.
        """
        result = {
            "enriched_at": self.enriched_at.isoformat(),
            "confidence_score": self.confidence_score,
            "lead_score": self.lead_score,
        }

        if self.score_breakdown:
            result["score_breakdown"] = self.score_breakdown.to_dict()

        if self.website_analysis:
            result["website_analysis"] = self.website_analysis.to_dict()

        if self.business_insights:
            result["business_insights"] = self.business_insights.to_dict()

        if self.company_enrichment:
            result["company_enrichment"] = self.company_enrichment.to_dict()

        if self.social_profiles:
            result["social_presence"] = {
                profile.platform: profile.to_dict()
                for profile in self.social_profiles
            }

        if self.personalization_hooks:
            result["personalization_hooks"] = [
                hook.to_dict() for hook in self.personalization_hooks
            ]

        if self.decision_makers:
            result["decision_makers"] = [
                dm.to_dict() if hasattr(dm, "to_dict") else dm
                for dm in self.decision_makers
            ]

        result["is_existing_customer"] = self.is_existing_customer

        if self.errors:
            result["errors"] = self.errors

        return result
