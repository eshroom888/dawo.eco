"""Lead Enrichment module for B2B Sales Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment

Provides lead enrichment capabilities:
- Website analysis for business information
- LLM-based business insights extraction
- Hunter.io extended enrichment
- Social media presence analysis
- Enrichment scoring and qualification

Exports:
    Schemas:
        - EnrichmentResult: Complete enrichment output
        - PersonalizationHook: Outreach personalization data
        - PersonalizationHookType: Hook type enum
        - WebsiteAnalysis: Website content analysis
        - BusinessInsights: LLM-extracted insights
        - SocialProfile: Social media presence
        - CompanyEnrichment: Hunter.io company data
        - ScoreBreakdown: Confidence score components

    Config:
        - EnrichmentConfig: Enrichment service configuration
        - ConfidenceScoreWeights: Score weight configuration
        - LeadScoreWeights: Lead score weight configuration
"""

from teams.dawo.leads.enrichment.schemas import (
    # Enums
    PersonalizationHookType,
    # Dataclasses
    PersonalizationHook,
    WebsiteAnalysis,
    BusinessInsights,
    SocialProfile,
    CompanyEnrichment,
    EnrichmentResult,
    ScoreBreakdown,
)

from teams.dawo.leads.enrichment.config import (
    # Config
    EnrichmentConfig,
    ConfidenceScoreWeights,
    LeadScoreWeights,
    # Constants
    MIN_CONFIDENCE_THRESHOLD,
    DEFAULT_BATCH_SIZE,
    DEFAULT_WEBSITE_TIMEOUT,
)

from teams.dawo.leads.enrichment.website_analyzer import WebsiteAnalyzer
from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
from teams.dawo.leads.enrichment.hunter_enricher import HunterEnricher
from teams.dawo.leads.enrichment.social_analyzer import SocialAnalyzer
from teams.dawo.leads.enrichment.scorer import EnrichmentScorer
from teams.dawo.leads.enrichment.service import LeadEnrichmentService
from teams.dawo.leads.enrichment.pipeline import (
    EnrichmentPipeline,
    PipelineResult,
    PipelineStatus,
    LeadNotFoundError,
)
from teams.dawo.leads.enrichment.agent import (
    LeadEnrichmentAgent,
    AgentResult,
)


__all__ = [
    # Agent
    "LeadEnrichmentAgent",
    "AgentResult",
    # Service
    "LeadEnrichmentService",
    # Pipeline
    "EnrichmentPipeline",
    "PipelineResult",
    "PipelineStatus",
    "LeadNotFoundError",
    # Analyzers
    "WebsiteAnalyzer",
    "BusinessAnalyzer",
    "HunterEnricher",
    "SocialAnalyzer",
    "EnrichmentScorer",
    # Enums
    "PersonalizationHookType",
    # Dataclasses
    "PersonalizationHook",
    "WebsiteAnalysis",
    "BusinessInsights",
    "SocialProfile",
    "CompanyEnrichment",
    "EnrichmentResult",
    "ScoreBreakdown",
    # Config
    "EnrichmentConfig",
    "ConfidenceScoreWeights",
    "LeadScoreWeights",
    # Constants
    "MIN_CONFIDENCE_THRESHOLD",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_WEBSITE_TIMEOUT",
]
