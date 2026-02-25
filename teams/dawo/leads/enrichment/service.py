"""Lead Enrichment Service for B2B Sales Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 7: Implement Lead Enrichment Service

Orchestrates all enrichment components:
- Website analysis
- LLM-based business insights
- Hunter.io company enrichment
- Social media analysis
- Confidence and lead scoring
"""

import logging
from typing import Any, Optional, Protocol
from urllib.parse import urlparse

from teams.dawo.leads.enrichment.config import EnrichmentConfig, MIN_CONFIDENCE_THRESHOLD
from teams.dawo.leads.enrichment.schemas import (
    EnrichmentResult,
    WebsiteAnalysis,
    BusinessInsights,
    CompanyEnrichment,
    SocialProfile,
    PersonalizationHook,
    ScoreBreakdown,
)
from core.leads.models import LeadStatus


logger = logging.getLogger(__name__)


class WebsiteAnalyzerProtocol(Protocol):
    """Protocol for website analyzer dependency."""

    async def analyze(self, url: str) -> WebsiteAnalysis:
        """Analyze a website URL."""
        ...


class BusinessAnalyzerProtocol(Protocol):
    """Protocol for business analyzer dependency."""

    async def analyze_business(
        self,
        website_content: str,
        company_name: str,
    ) -> BusinessInsights:
        """Analyze business from website content."""
        ...

    async def identify_hooks(
        self,
        website_content: str,
        company_name: str,
    ) -> list[PersonalizationHook]:
        """Identify personalization hooks."""
        ...

    async def detect_existing_customer(
        self,
        website_content: str,
    ) -> bool:
        """Detect if company is existing DAWO customer."""
        ...


class HunterEnricherProtocol(Protocol):
    """Protocol for Hunter.io enricher dependency."""

    async def enrich_company(self, domain: str) -> CompanyEnrichment:
        """Enrich company data from Hunter.io."""
        ...

    async def find_decision_makers(self, domain: str) -> list[Any]:
        """Find decision-maker contacts."""
        ...


class SocialAnalyzerProtocol(Protocol):
    """Protocol for social analyzer dependency."""

    async def analyze_instagram(self, handle: str) -> Optional[SocialProfile]:
        """Analyze Instagram profile."""
        ...

    async def analyze_linkedin(
        self,
        url: str,
        company_data: Optional[dict[str, Any]] = None,
    ) -> Optional[SocialProfile]:
        """Analyze LinkedIn company page."""
        ...


class ScorerProtocol(Protocol):
    """Protocol for enrichment scorer dependency."""

    def calculate_confidence(
        self,
        result: EnrichmentResult,
    ) -> tuple[float, ScoreBreakdown]:
        """Calculate confidence score."""
        ...

    def calculate_lead_score(
        self,
        result: EnrichmentResult,
        industry: Optional[str] = None,
        country: Optional[str] = None,
        company_size: Optional[str] = None,
    ) -> float:
        """Calculate lead score."""
        ...


class LeadEnrichmentService:
    """Orchestrates lead enrichment from multiple sources.

    Coordinates all enrichment components to build a complete
    profile for B2B leads. Handles failures gracefully with
    partial results.

    Attributes:
        _config: Enrichment configuration
        _website_analyzer: Website content analyzer
        _business_analyzer: LLM-based business insights
        _hunter_enricher: Hunter.io company data
        _social_analyzer: Social media presence
        _scorer: Confidence and lead scoring
    """

    def __init__(
        self,
        config: EnrichmentConfig,
        website_analyzer: WebsiteAnalyzerProtocol,
        business_analyzer: BusinessAnalyzerProtocol,
        hunter_enricher: HunterEnricherProtocol,
        social_analyzer: SocialAnalyzerProtocol,
        scorer: ScorerProtocol,
    ) -> None:
        """Initialize the enrichment service.

        Args:
            config: Enrichment configuration
            website_analyzer: Website content analyzer
            business_analyzer: LLM-based business insights
            hunter_enricher: Hunter.io company data
            social_analyzer: Social media presence analyzer
            scorer: Confidence and lead scoring calculator
        """
        self._config = config
        self._website_analyzer = website_analyzer
        self._business_analyzer = business_analyzer
        self._hunter_enricher = hunter_enricher
        self._social_analyzer = social_analyzer
        self._scorer = scorer

    async def enrich_lead(self, lead: Any) -> EnrichmentResult:
        """Enrich a lead with data from all sources.

        Orchestrates calls to all analyzers and aggregates results.
        Handles failures gracefully - partial results are returned
        if some analyzers fail.

        Args:
            lead: Lead object with id, website_url, company, etc.

        Returns:
            EnrichmentResult with all gathered data
        """
        errors: list[str] = []
        result = EnrichmentResult(lead_id=lead.id)

        # Extract domain from website URL
        domain = self._extract_domain(getattr(lead, "website_url", None))

        # 1. Website analysis
        website_analysis = await self._analyze_website(lead, errors)
        result.website_analysis = website_analysis

        # 2. Business insights (requires website content)
        if website_analysis and website_analysis.content:
            business_insights = await self._analyze_business(
                website_analysis.content,
                getattr(lead, "company", ""),
                errors,
            )
            result.business_insights = business_insights

            # Personalization hooks
            hooks = await self._identify_hooks(
                website_analysis.content,
                getattr(lead, "company", ""),
                errors,
            )
            result.personalization_hooks = hooks

            # Check for existing customer
            result.is_existing_customer = await self._detect_existing_customer(
                website_analysis.content,
                errors,
            )

        # 3. Hunter.io enrichment
        if domain:
            company_enrichment = await self._enrich_company(domain, errors)
            result.company_enrichment = company_enrichment

            # Decision makers
            decision_makers = await self._find_decision_makers(domain, errors)
            result.decision_makers = decision_makers

        # 4. Social media analysis
        social_profiles = await self._analyze_social(lead, result, errors)
        result.social_profiles = social_profiles

        # 5. Calculate scores
        confidence_score, score_breakdown = self._scorer.calculate_confidence(result)
        result.confidence_score = confidence_score
        result.score_breakdown = score_breakdown

        lead_score = self._scorer.calculate_lead_score(
            result,
            industry=getattr(lead, "industry", None),
            country=getattr(lead, "country", None),
            company_size=getattr(lead, "company_size", None),
        )
        result.lead_score = lead_score

        # Store errors
        result.errors = errors

        return result

    def determine_status(
        self,
        result: EnrichmentResult,
        is_existing_customer: bool = False,
    ) -> LeadStatus:
        """Determine lead status based on enrichment results.

        Status logic:
        - CONVERTED: Existing DAWO customer
        - QUALIFIED: Confidence score >= threshold (5)
        - RESEARCHING: Confidence score < threshold

        Args:
            result: Enrichment result with confidence score
            is_existing_customer: Whether lead is existing customer

        Returns:
            LeadStatus enum value
        """
        if is_existing_customer:
            return LeadStatus.CONVERTED

        if result.confidence_score >= MIN_CONFIDENCE_THRESHOLD:
            return LeadStatus.QUALIFIED

        return LeadStatus.RESEARCHING

    def get_missing_fields(self, result: EnrichmentResult) -> list[str]:
        """Identify missing enrichment data fields.

        Checks which enrichment components returned no data.
        Useful for determining if re-enrichment is needed.

        Args:
            result: Enrichment result to check

        Returns:
            List of missing field names
        """
        missing = []

        if result.website_analysis is None:
            missing.append("website_analysis")

        if result.business_insights is None:
            missing.append("business_insights")

        if result.company_enrichment is None:
            missing.append("company_enrichment")

        if not result.social_profiles:
            missing.append("social_profiles")

        if not result.personalization_hooks:
            missing.append("personalization_hooks")

        return missing

    def format_enrichment_data(self, result: EnrichmentResult) -> dict[str, Any]:
        """Format enrichment result for JSONB storage.

        Converts the enrichment result to a dict suitable
        for storing in the Lead.enrichment_data JSONB field.

        Args:
            result: Enrichment result to format

        Returns:
            Dict suitable for JSONB storage
        """
        return result.to_dict()

    def _extract_domain(self, url: Optional[str]) -> Optional[str]:
        """Extract domain from URL.

        Args:
            url: Full URL (e.g., "https://example.com/page")

        Returns:
            Domain (e.g., "example.com") or None
        """
        if not url:
            return None

        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove www. prefix if present
            if domain.startswith("www."):
                domain = domain[4:]
            return domain if domain else None
        except Exception:
            return None

    async def _analyze_website(
        self,
        lead: Any,
        errors: list[str],
    ) -> Optional[WebsiteAnalysis]:
        """Analyze website with error handling.

        Args:
            lead: Lead with website_url
            errors: List to append errors to

        Returns:
            WebsiteAnalysis or None on failure
        """
        url = getattr(lead, "website_url", None)
        if not url:
            return None

        try:
            return await self._website_analyzer.analyze(url)
        except Exception as e:
            error_msg = f"Website analysis failed: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            return None

    async def _analyze_business(
        self,
        content: str,
        company_name: str,
        errors: list[str],
    ) -> Optional[BusinessInsights]:
        """Analyze business with error handling.

        Args:
            content: Website content
            company_name: Company name
            errors: List to append errors to

        Returns:
            BusinessInsights or None on failure
        """
        try:
            return await self._business_analyzer.analyze_business(content, company_name)
        except Exception as e:
            error_msg = f"Business analysis failed: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            return None

    async def _identify_hooks(
        self,
        content: str,
        company_name: str,
        errors: list[str],
    ) -> list[PersonalizationHook]:
        """Identify hooks with error handling.

        Args:
            content: Website content
            company_name: Company name
            errors: List to append errors to

        Returns:
            List of PersonalizationHook (empty on failure)
        """
        try:
            return await self._business_analyzer.identify_hooks(content, company_name)
        except Exception as e:
            error_msg = f"Hook identification failed: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            return []

    async def _detect_existing_customer(
        self,
        content: str,
        errors: list[str],
    ) -> bool:
        """Detect existing customer with error handling.

        Args:
            content: Website content
            errors: List to append errors to

        Returns:
            True if existing customer, False otherwise
        """
        try:
            return await self._business_analyzer.detect_existing_customer(content)
        except Exception as e:
            error_msg = f"Existing customer detection failed: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            return False

    async def _enrich_company(
        self,
        domain: str,
        errors: list[str],
    ) -> Optional[CompanyEnrichment]:
        """Enrich company with error handling.

        Args:
            domain: Company domain
            errors: List to append errors to

        Returns:
            CompanyEnrichment or None on failure
        """
        try:
            return await self._hunter_enricher.enrich_company(domain)
        except Exception as e:
            error_msg = f"Company enrichment failed: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            return None

    async def _find_decision_makers(
        self,
        domain: str,
        errors: list[str],
    ) -> list[Any]:
        """Find decision makers with error handling.

        Args:
            domain: Company domain
            errors: List to append errors to

        Returns:
            List of decision makers (empty on failure)
        """
        try:
            return await self._hunter_enricher.find_decision_makers(domain)
        except Exception as e:
            error_msg = f"Decision maker search failed: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            return []

    async def _analyze_social(
        self,
        lead: Any,
        result: EnrichmentResult,
        errors: list[str],
    ) -> list[SocialProfile]:
        """Analyze social media presence.

        Args:
            lead: Lead with social URLs
            result: Current enrichment result (for company data)
            errors: List to append errors to

        Returns:
            List of SocialProfile
        """
        profiles = []

        # Instagram
        instagram_handle = getattr(lead, "instagram_handle", None)
        if instagram_handle:
            try:
                profile = await self._social_analyzer.analyze_instagram(instagram_handle)
                if profile:
                    profiles.append(profile)
            except Exception as e:
                error_msg = f"Instagram analysis failed: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # LinkedIn
        linkedin_url = getattr(lead, "linkedin_url", None)
        if linkedin_url:
            try:
                company_data = None
                if result.company_enrichment:
                    company_data = {
                        "headcount": result.company_enrichment.headcount,
                    }
                profile = await self._social_analyzer.analyze_linkedin(
                    linkedin_url,
                    company_data,
                )
                if profile:
                    profiles.append(profile)
            except Exception as e:
                error_msg = f"LinkedIn analysis failed: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        return profiles
