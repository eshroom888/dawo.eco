"""DAWO Team Specification - Agent Registration.

All DAWO agents MUST be registered in this file using the RegisteredAgent pattern.
The Team Builder uses this specification to compose agent teams dynamically.

Registration Pattern:
    AGENTS = [
        RegisteredAgent(
            name="agent_name",
            agent_class=AgentClass,
            capabilities=["capability1", "capability2"],
            tier="scan|generate|strategize"  # Task type, NOT model name
        )
    ]

LLM Tier System (Story 1.4):
    The `tier` field specifies the task type, which maps to an LLM tier:
    - "scan" → Haiku (high-volume research, fast classification)
    - "generate" → Sonnet (content creation, compliance checking)
    - "strategize" → Opus (complex planning, multi-step reasoning)

    Team Builder uses LLMTierResolver to convert task type to actual model ID.
    Per-agent overrides can be configured in config/dawo_llm_tiers.json.

    Example:
        # In team_spec.py - use task type
        RegisteredAgent(name="scanner", ..., tier="scan")

        # Team Builder resolves to actual model
        from teams.dawo.config import LLMTierResolver, TaskType
        tier_config = resolver.resolve_tier("scanner", TaskType.SCAN)
        # tier_config.model_id == "claude-haiku-4-5-20251001"

Anti-patterns to AVOID:
    - NEVER use @register_agent decorators
    - NEVER self-register agents
    - NEVER hardcode LLM model names like "claude-3-sonnet"

See: project-context.md#Agent-Registration for complete guidelines.
"""

from dataclasses import dataclass
from typing import Any, List, Type

# NOTE: RegisteredAgent import will be added when core.registry module is available
# from core.registry import RegisteredAgent

# Type-safe placeholder for forward compatibility
# When core.registry is available, replace with: from core.registry import RegisteredAgent
try:
    from core.registry import RegisteredAgent
except ImportError:
    # Placeholder class for development - maintains type safety until platform integration
    @dataclass
    class RegisteredAgent:
        """Placeholder for RegisteredAgent until core.registry is available.

        Matches expected interface from IMAGO.ECO platform.
        """
        name: str
        agent_class: Type[Any]
        capabilities: list[str]
        tier: str  # "scan", "generate", or "strategize"

# Agent imports
from teams.dawo.validators.eu_compliance import EUComplianceChecker
from teams.dawo.validators.brand_voice import BrandVoiceValidator

# Service imports (Research Pool - Story 2.1)
from teams.dawo.research import ResearchPublisher, ResearchPoolRepository

# Scoring imports (Research Scoring - Story 2.2)
from teams.dawo.research.scoring import (
    ResearchItemScorer,
    ResearchScoringService,
)

# Scanner imports (Reddit Scanner - Story 2.3)
from teams.dawo.scanners.reddit import (
    RedditScanner,
    RedditHarvester,
    RedditTransformer,
    RedditValidator,
    RedditResearchPipeline,
)

# Scanner imports (YouTube Scanner - Story 2.4)
from teams.dawo.scanners.youtube import (
    YouTubeScanner,
    KeyInsightExtractor,
    YouTubeHarvester,
    YouTubeTransformer,
    YouTubeValidator,
    YouTubeResearchPipeline,
)

# Scanner imports (Instagram Scanner - Story 2.5)
from teams.dawo.scanners.instagram import (
    InstagramScanner,
    ThemeExtractor,
    HealthClaimDetector,
    InstagramHarvester,
    InstagramTransformer,
    InstagramValidator,
    InstagramResearchPipeline,
)

# Scanner imports (News Scanner - Story 2.6)
from teams.dawo.scanners.news import (
    NewsScanner,
    NewsCategorizer,
    NewsPriorityScorer,
    NewsHarvester,
    NewsTransformer,
    NewsValidator,
    NewsResearchPipeline,
)

# Scanner imports (PubMed Scanner - Story 2.7)
from teams.dawo.scanners.pubmed import (
    PubMedScanner,
    PubMedClient,
    PubMedHarvester,
    FindingSummarizer,
    ClaimValidator,
    PubMedTransformer,
    PubMedValidator,
    PubMedResearchPipeline,
)

# Research Compliance Validator (Story 2.8)
from teams.dawo.validators.research_compliance import ResearchComplianceValidator

# Shopify Integration (Story 3.1)
# Use direct module import to avoid circular import with teams.dawo.middleware
from integrations.shopify.client import ShopifyClient

# Google Drive Integration (Story 3.2)
# Use direct module import for consistency
from integrations.google_drive.client import GoogleDriveClient

# Instagram Caption Generator (Story 3.3)
# Use direct module import to avoid circular import
from teams.dawo.generators.instagram_caption.agent import CaptionGenerator

# Orshot Graphics Generator (Story 3.4)
from teams.dawo.generators.orshot_graphics.agent import OrshotRenderer
from integrations.orshot import (
    OrshotClient,
    OrshotUsageTracker,
    OrshotRateLimiter,
)

# Nano Banana AI Image Generator (Story 3.5)
from teams.dawo.generators.nano_banana.agent import NanoBananaGenerator
from integrations.gemini import GeminiImageClient

# Compliance Rewrite Suggester (Story 3.6)
from teams.dawo.generators.compliance_rewrite.agent import ComplianceRewriteSuggester

# Content Quality Scorer (Story 3.7)
from teams.dawo.generators.content_quality.agent import ContentQualityScorer

# Auto-Publish Eligibility Tagger (Story 3.8)
from teams.dawo.generators.auto_publish_tagger.agent import AutoPublishTagger
from teams.dawo.generators.auto_publish_tagger.statistics import AutoPublishStatisticsService

# Asset Usage Tracker (Story 3.9)
from teams.dawo.generators.asset_usage.agent import AssetUsageTracker
from teams.dawo.generators.asset_usage.repository import AssetUsageRepository

# B2B Lead Scanner (Story 5.1)
from teams.dawo.leads import (
    B2BLeadScanner,
    LeadHarvester,
    LeadTransformer,
    LeadDuplicateChecker,
    B2BLeadPipeline,
    HunterClient,
    LeadRepository,
)

# Lead Enrichment (Story 5.2)
from teams.dawo.leads.enrichment import (
    LeadEnrichmentAgent,
    LeadEnrichmentService,
    EnrichmentPipeline,
    WebsiteAnalyzer,
    BusinessAnalyzer,
    HunterEnricher,
    SocialAnalyzer,
    EnrichmentScorer,
)

# Outreach Draft Generator (Story 5.3)
from teams.dawo.leads.outreach import (
    OutreachDraftAgent,
    OutreachService,
    OutreachPipeline,
    OutreachDraftGenerator,
    PersonalizationEngine,
    LeadTypeClassifier,
    OutreachValidator,
    OutreachApprovalIntegration,
    OutreachTemplateRegistry,
)

# Pipeline Service (Story 5.5)
from teams.dawo.leads.pipeline import PipelineService, CSVExporter

# Gmail Sender (Story 5.4)
from teams.dawo.leads.gmail import (
    GmailSendService,
    GmailRateLimitConfig,
    GmailConfig,
)
from teams.dawo.leads.gmail.agent import GmailSenderAgent
from teams.dawo.leads.gmail.client import GmailClient
from teams.dawo.leads.gmail.credentials_manager import GmailCredentialsManager
from teams.dawo.leads.gmail.pipeline import GmailSendPipeline
from teams.dawo.leads.gmail.gdpr_validator import GDPRPreSendValidator
from teams.dawo.leads.gmail.utm import UTMInjector
from teams.dawo.leads.gmail.signature import SignatureBuilder
from teams.dawo.leads.gmail.rate_limiter import GmailRateLimiter

# Health Claims Monitor (Story 6.1)
from teams.dawo.scanners.health_claims import (
    HealthClaimsClient,
    HealthClaimsMonitorPipeline,
    HealthClaimsRepository,
    RegisterParser,
    RelevanceFilter,
    ChangeDetector,
)

# Novel Food Catalogue Monitor (Story 6.2)
from teams.dawo.scanners.novel_food.client import NovelFoodCatalogueClient
from teams.dawo.scanners.novel_food.parser import CatalogueParser
from teams.dawo.scanners.novel_food.change_detector import NovelFoodChangeDetector
from teams.dawo.scanners.novel_food.repository import NovelFoodRepository
from teams.dawo.scanners.novel_food.pipeline import NovelFoodMonitorPipeline
from teams.dawo.scanners.mattilsynet.client import MattilsynetClient
from teams.dawo.scanners.mattilsynet.feed_parser import MattilsynetFeedParser
from teams.dawo.scanners.mattilsynet.page_parser import MattilsynetPageParser
from teams.dawo.scanners.mattilsynet.keyword_matcher import NorwegianKeywordMatcher
from teams.dawo.scanners.mattilsynet.change_detector import PageChangeDetector
from teams.dawo.scanners.mattilsynet.repository import MattilsynetRepository
from teams.dawo.scanners.mattilsynet.pipeline import MattilsynetMonitorPipeline

# Claims Alerts (Story 6.4)
from teams.dawo.scanners.claims_alerts import (
    ClaimsAlertConfig,
    ClaimsAlertFormatter,
    ClaimsAlertBatcher,
    DAWORelevanceFilter,
    ClaimsAlertService,
    RegulatoryAlertSubscriber,
)

# Health Claim Extraction Engine (Story 6.6)
from teams.dawo.scanners.claim_extraction import (
    HealthClaimExtractionEngine,
    ClaimPatternMatcher,
    ClaimLLMClassifier,
    HealthClaimRepository,
)

# Competitor Content Scanner (Story 6.5)
from teams.dawo.scanners.competitor import (
    CompetitorScanPipeline,
    WebsiteScraperClient,
    CompetitorContentParser,
    CompetitorDuplicateChecker,
    CompetitorRepository,
)

# Violation Detection (Story 6.7)
from teams.dawo.scanners.violation_detection import (
    ViolationDetector,
    ViolationClassifier,
    ViolationRepository,
)

# Instagram Analytics (Story 7.1)
from core.analytics import (
    InstagramMetricsCollector,
    InstagramMetricsRepository,
    MetricsQueryService,
)

# UTM Click-Through Tracking (Story 7.2)
from core.analytics import (
    ClickAnalyticsService,
    ShortLinkService,
    UTMRepository,
)

# Shopify Sales Attribution (Story 7.3)
from core.analytics.attribution_repository import AttributionRepository
from core.analytics.attribution_service import AttributionService
from core.analytics.revenue_analytics import RevenueAnalyticsService

# Post-Publish Quality Scoring (Story 7.4)
from core.analytics.comment_sentiment import CommentSentimentScorer
from core.analytics.quality_scoring_repository import QualityScoringRepository
from core.analytics.quality_scoring_service import PostPublishScoringService
from core.analytics.quality_scoring_analyzer import VarianceAnalyzer

# Performance Feedback Loop (Story 7.5)
from core.analytics.feedback_loop_repository import FeedbackLoopRepository
from core.analytics.content_performance_analyzer import ContentPerformanceAnalyzer
from core.analytics.weight_adjuster import WeightAdjuster
from core.analytics.feedback_loop_service import FeedbackLoopService

# Agent Schedule Configuration (Story 7.6)
from core.scheduling.schedule_repository import AgentScheduleRepository
from core.scheduling.schedule_service import AgentScheduleService

# Manual Trigger Service (Story 7.7)
from core.scheduling.manual_trigger_service import ManualTriggerService

# Execution Dashboard (Story 7.8)
from core.scheduling.execution_log_repository import ExecutionLogRepository
from core.scheduling.execution_log_service import ExecutionLogService

# Calendar Sync (Story 7.9)
from integrations.google_calendar.sync_service import CalendarSyncService

# Evidence Collection (Story 6.8, 6.10)
from teams.dawo.scanners.evidence_collection import (
    EvidenceCollector,
    EvidenceDownloadService,
    EvidenceRepository,
    EvidenceStorageService,
    PlaywrightScreenshotService,
    ReportStorageService,
    WeasyPrintPDFGenerator,
)

# Graceful Degradation (Story 7.10)
from core.degradation import (
    DegradationAlertService,
    RecoveryProcessor,
    ServiceHealthRegistry,
)

# Tier values - use these string constants for type safety
# These map to TaskType enum values in teams.dawo.config.llm_tiers
TIER_SCAN = "scan"          # → Haiku (high-volume, fast)
TIER_GENERATE = "generate"  # → Sonnet (quality, judgment)
TIER_STRATEGIZE = "strategize"  # → Opus (complex reasoning)

# Agent Registration List
# All DAWO agents are registered here for Team Builder discovery
AGENTS: List[RegisteredAgent] = [
    RegisteredAgent(
        name="eu_compliance_checker",
        agent_class=EUComplianceChecker,
        capabilities=["eu_compliance", "content_validation"],
        tier=TIER_GENERATE,  # Uses Sonnet for accurate judgment
    ),
    RegisteredAgent(
        name="brand_voice_validator",
        agent_class=BrandVoiceValidator,
        capabilities=["brand_voice", "content_validation"],
        tier=TIER_GENERATE,  # Uses Sonnet for judgment quality
    ),
    # Reddit Scanner (Story 2.3)
    RegisteredAgent(
        name="reddit_scanner",
        agent_class=RedditScanner,
        capabilities=["reddit_research", "research_scanning"],
        tier=TIER_SCAN,  # Uses scan tier for high-volume research
    ),
    # YouTube Scanner (Story 2.4)
    RegisteredAgent(
        name="youtube_scanner",
        agent_class=YouTubeScanner,
        capabilities=["youtube_research", "research_scanning"],
        tier=TIER_SCAN,  # Uses scan tier for video discovery
    ),
    RegisteredAgent(
        name="key_insight_extractor",
        agent_class=KeyInsightExtractor,
        capabilities=["youtube_research", "insight_extraction"],
        tier=TIER_GENERATE,  # Uses generate tier (Sonnet) for quality summarization
    ),
    # Instagram Scanner (Story 2.5)
    RegisteredAgent(
        name="instagram_scanner",
        agent_class=InstagramScanner,
        capabilities=["instagram_research", "research_scanning", "trend_monitoring"],
        tier=TIER_SCAN,  # Uses scan tier for post discovery
    ),
    RegisteredAgent(
        name="theme_extractor",
        agent_class=ThemeExtractor,
        capabilities=["instagram_research", "theme_extraction", "content_analysis"],
        tier=TIER_GENERATE,  # Uses generate tier (Sonnet) for quality theme analysis
    ),
    RegisteredAgent(
        name="health_claim_detector",
        agent_class=HealthClaimDetector,
        capabilities=["instagram_research", "claim_detection", "compliance_screening"],
        tier=TIER_GENERATE,  # Uses generate tier (Sonnet) for accurate claim detection
    ),
    # News Scanner (Story 2.6)
    RegisteredAgent(
        name="news_scanner",
        agent_class=NewsScanner,
        capabilities=["news_research", "research_scanning", "regulatory_monitoring"],
        tier=TIER_SCAN,  # Rule-based, no actual LLM calls
    ),
    # PubMed Scanner (Story 2.7)
    RegisteredAgent(
        name="pubmed_scanner",
        agent_class=PubMedScanner,
        capabilities=["pubmed_research", "research_scanning", "scientific_research"],
        tier=TIER_SCAN,  # Uses scan tier for article discovery
    ),
    RegisteredAgent(
        name="finding_summarizer",
        agent_class=FindingSummarizer,
        capabilities=["pubmed_research", "scientific_summarization", "content_generation"],
        tier=TIER_GENERATE,  # Uses generate tier (Sonnet) for quality scientific summarization
    ),
    RegisteredAgent(
        name="claim_validator",
        agent_class=ClaimValidator,
        capabilities=["pubmed_research", "claim_validation", "eu_compliance"],
        tier=TIER_GENERATE,  # Uses generate tier (Sonnet) for accurate claim assessment
    ),
    # Instagram Caption Generator (Story 3.3)
    RegisteredAgent(
        name="instagram_caption_generator",
        agent_class=CaptionGenerator,
        capabilities=["caption_generation", "content_generation", "norwegian"],
        tier=TIER_GENERATE,  # Uses generate tier (Sonnet) for quality content creation
    ),
    # Orshot Graphics Generator (Story 3.4)
    RegisteredAgent(
        name="orshot_renderer",
        agent_class=OrshotRenderer,
        capabilities=["graphics_generation", "branded_graphics", "instagram_graphics"],
        tier=TIER_GENERATE,  # Uses generate tier for quality template selection
    ),
    # Nano Banana AI Image Generator (Story 3.5)
    RegisteredAgent(
        name="nano_banana_generator",
        agent_class=NanoBananaGenerator,
        capabilities=["image_generation", "gemini", "visual_content", "ai_art"],
        tier=TIER_GENERATE,  # Uses generate tier for image generation API
    ),
    # Compliance Rewrite Suggester (Story 3.6)
    RegisteredAgent(
        name="compliance_rewrite_suggester",
        agent_class=ComplianceRewriteSuggester,
        capabilities=["compliance_rewrite", "content_rewrite", "eu_compliance"],
        tier=TIER_GENERATE,  # Uses generate tier for quality rewrites
    ),
    # Content Quality Scorer (Story 3.7)
    RegisteredAgent(
        name="content_quality_scorer",
        agent_class=ContentQualityScorer,
        capabilities=["content_quality", "quality_scoring", "content_evaluation"],
        tier=TIER_GENERATE,  # Uses generate tier for AI detectability analysis
    ),
    # Auto-Publish Eligibility Tagger (Story 3.8)
    RegisteredAgent(
        name="auto_publish_tagger",
        agent_class=AutoPublishTagger,
        capabilities=["auto_publish", "content_tagging", "approval_eligibility"],
        tier=TIER_GENERATE,  # Uses generate tier for future LLM enhancements
    ),
    # Asset Usage Tracker (Story 3.9)
    RegisteredAgent(
        name="asset_usage_tracker",
        agent_class=AssetUsageTracker,
        capabilities=["asset_tracking", "usage_analytics", "performance_metrics"],
        tier=TIER_GENERATE,  # Uses generate tier for future LLM enhancements
    ),
    # B2B Lead Scanner (Story 5.1)
    RegisteredAgent(
        name="b2b_lead_scanner",
        agent_class=B2BLeadScanner,
        capabilities=["b2b_lead_research", "lead_discovery", "b2b_sales"],
        tier=TIER_SCAN,  # Uses scan tier for high-volume lead discovery
    ),
    # Lead Enrichment Agent (Story 5.2)
    RegisteredAgent(
        name="lead_enrichment_agent",
        agent_class=LeadEnrichmentAgent,
        capabilities=["lead_enrichment", "business_analysis", "b2b_sales"],
        tier=TIER_GENERATE,  # Uses generate tier (Sonnet) for LLM analysis
    ),
    # Outreach Draft Agent (Story 5.3)
    RegisteredAgent(
        name="outreach_draft_agent",
        agent_class=OutreachDraftAgent,
        capabilities=["lead_outreach", "email_generation", "b2b_sales"],
        tier=TIER_GENERATE,  # Uses generate tier (Sonnet) for LLM draft generation
    ),
    # Gmail Sender Agent (Story 5.4)
    RegisteredAgent(
        name="gmail_sender_agent",
        agent_class=GmailSenderAgent,
        capabilities=["email_send", "gmail_integration"],
        tier=TIER_SCAN,  # Lightweight orchestration, no LLM needed
    ),
    # Health Claim Extraction Engine (Story 6.6)
    RegisteredAgent(
        name="health_claim_extraction_engine",
        agent_class=HealthClaimExtractionEngine,
        capabilities=["competitor_monitoring", "claim_extraction"],
        tier=TIER_GENERATE,  # Orchestrates LLM classification pipeline
    ),
    # Violation Detector (Story 6.7)
    RegisteredAgent(
        name="violation_detector",
        agent_class=ViolationDetector,
        capabilities=["competitor_monitoring", "violation_detection"],
        tier=TIER_GENERATE,  # Orchestrates classification + register cross-reference
    ),
    # Evidence Collector (Story 6.8)
    RegisteredAgent(
        name="evidence_collector",
        agent_class=EvidenceCollector,
        capabilities=["competitor_monitoring", "evidence_collection", "screenshot_capture"],
        tier=TIER_SCAN,  # No LLM needed — capture + store
    ),
]


# Service Registration (non-LLM components)
# These are registered for Team Builder discovery via capability tags
# Unlike agents, services don't have LLM tiers - they are pure Python classes
@dataclass
class RegisteredService:
    """Registration entry for non-agent services.

    Services are resolved by capability and instantiated with dependency injection.
    The Team Builder injects required dependencies (sessions, configs, etc.).
    """
    name: str
    service_class: type
    capabilities: list[str]
    requires_session: bool = False  # If True, Team Builder injects AsyncSession


SERVICES: list[RegisteredService] = [
    RegisteredService(
        name="research_pool_repository",
        service_class=ResearchPoolRepository,
        capabilities=["research_storage", "research_query"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="research_publisher",
        service_class=ResearchPublisher,
        capabilities=["research_storage", "research_publish"],
        requires_session=False,  # Receives repository, not session directly
    ),
    # Scoring Engine (Story 2.2)
    RegisteredService(
        name="research_item_scorer",
        service_class=ResearchItemScorer,
        capabilities=["research_scoring"],
        requires_session=False,  # Receives component scorers via injection
    ),
    RegisteredService(
        name="research_scoring_service",
        service_class=ResearchScoringService,
        capabilities=["research_scoring", "research_storage"],
        requires_session=False,  # Receives repository and scorer via injection
    ),
    # Research Compliance Validator (Story 2.8)
    # Shared validation service used by all scanner validators
    RegisteredService(
        name="research_compliance_validator",
        service_class=ResearchComplianceValidator,
        capabilities=["research_compliance", "content_validation", "eu_compliance"],
        requires_session=False,  # Receives EUComplianceChecker via injection
    ),
    # Reddit Scanner Services (Story 2.3)
    RegisteredService(
        name="reddit_harvester",
        service_class=RedditHarvester,
        capabilities=["reddit_research"],
        requires_session=False,  # Receives RedditClient via injection
    ),
    RegisteredService(
        name="reddit_transformer",
        service_class=RedditTransformer,
        capabilities=["reddit_research"],
        requires_session=False,  # Pure transformation, no external dependencies
    ),
    RegisteredService(
        name="reddit_validator",
        service_class=RedditValidator,
        capabilities=["reddit_research", "content_validation"],
        requires_session=False,  # Receives ResearchComplianceValidator via injection
    ),
    RegisteredService(
        name="reddit_research_pipeline",
        service_class=RedditResearchPipeline,
        capabilities=["reddit_research", "research_pipeline"],
        requires_session=False,  # Receives all stage components via injection
    ),
    # YouTube Scanner Services (Story 2.4)
    RegisteredService(
        name="youtube_harvester",
        service_class=YouTubeHarvester,
        capabilities=["youtube_research"],
        requires_session=False,  # Receives YouTubeClient and TranscriptClient via injection
    ),
    RegisteredService(
        name="youtube_transformer",
        service_class=YouTubeTransformer,
        capabilities=["youtube_research"],
        requires_session=False,  # Receives KeyInsightExtractor via injection
    ),
    RegisteredService(
        name="youtube_validator",
        service_class=YouTubeValidator,
        capabilities=["youtube_research", "content_validation"],
        requires_session=False,  # Receives ResearchComplianceValidator via injection
    ),
    RegisteredService(
        name="youtube_research_pipeline",
        service_class=YouTubeResearchPipeline,
        capabilities=["youtube_research", "research_pipeline"],
        requires_session=False,  # Receives all stage components via injection
    ),
    # Instagram Scanner Services (Story 2.5)
    RegisteredService(
        name="instagram_harvester",
        service_class=InstagramHarvester,
        capabilities=["instagram_research"],
        requires_session=False,  # Receives InstagramClient via injection
    ),
    RegisteredService(
        name="instagram_transformer",
        service_class=InstagramTransformer,
        capabilities=["instagram_research"],
        requires_session=False,  # Receives ThemeExtractor and HealthClaimDetector via injection
    ),
    RegisteredService(
        name="instagram_validator",
        service_class=InstagramValidator,
        capabilities=["instagram_research", "content_validation"],
        requires_session=False,  # Receives ResearchComplianceValidator via injection
    ),
    RegisteredService(
        name="instagram_research_pipeline",
        service_class=InstagramResearchPipeline,
        capabilities=["instagram_research", "research_pipeline"],
        requires_session=False,  # Receives all stage components via injection
    ),
    # News Scanner Services (Story 2.6)
    RegisteredService(
        name="news_categorizer",
        service_class=NewsCategorizer,
        capabilities=["news_research", "categorization"],
        requires_session=False,  # Rule-based, no external dependencies
    ),
    RegisteredService(
        name="news_priority_scorer",
        service_class=NewsPriorityScorer,
        capabilities=["news_research", "scoring"],
        requires_session=False,  # Rule-based, no external dependencies
    ),
    RegisteredService(
        name="news_harvester",
        service_class=NewsHarvester,
        capabilities=["news_research"],
        requires_session=False,  # Pure transformation, no external dependencies
    ),
    RegisteredService(
        name="news_transformer",
        service_class=NewsTransformer,
        capabilities=["news_research"],
        requires_session=False,  # Receives NewsCategorizer and NewsPriorityScorer via injection
    ),
    RegisteredService(
        name="news_validator",
        service_class=NewsValidator,
        capabilities=["news_research", "content_validation"],
        requires_session=False,  # Receives ResearchComplianceValidator via injection
    ),
    RegisteredService(
        name="news_research_pipeline",
        service_class=NewsResearchPipeline,
        capabilities=["news_research", "research_pipeline"],
        requires_session=False,  # Receives all stage components via injection
    ),
    # PubMed Scanner Services (Story 2.7)
    RegisteredService(
        name="pubmed_client",
        service_class=PubMedClient,
        capabilities=["pubmed_research", "entrez_api"],
        requires_session=False,  # Receives EntrezConfig and retry middleware via injection
    ),
    RegisteredService(
        name="pubmed_harvester",
        service_class=PubMedHarvester,
        capabilities=["pubmed_research"],
        requires_session=False,  # Stateless, no external dependencies
    ),
    RegisteredService(
        name="pubmed_transformer",
        service_class=PubMedTransformer,
        capabilities=["pubmed_research"],
        requires_session=False,  # Stateless, no external dependencies
    ),
    RegisteredService(
        name="pubmed_validator",
        service_class=PubMedValidator,
        capabilities=["pubmed_research", "content_validation"],
        requires_session=False,  # Receives ResearchComplianceValidator via injection
    ),
    RegisteredService(
        name="pubmed_research_pipeline",
        service_class=PubMedResearchPipeline,
        capabilities=["pubmed_research", "research_pipeline", "scientific_research"],
        requires_session=False,  # Receives all stage components via injection
    ),
    # Shopify Integration (Story 3.1)
    RegisteredService(
        name="shopify_client",
        service_class=ShopifyClient,
        capabilities=["product_data", "shopify"],
        requires_session=False,  # Receives store_domain and access_token via injection
    ),
    # Google Drive Integration (Story 3.2)
    RegisteredService(
        name="google_drive_client",
        service_class=GoogleDriveClient,
        capabilities=["asset_storage", "google_drive"],
        requires_session=False,  # Receives credentials_path and root_folder_id via injection
    ),
    # Orshot Integration (Story 3.4)
    RegisteredService(
        name="orshot_client",
        service_class=OrshotClient,
        capabilities=["graphics_generation", "orshot"],
        requires_session=False,  # Receives api_key via injection
    ),
    RegisteredService(
        name="orshot_usage_tracker",
        service_class=OrshotUsageTracker,
        capabilities=["usage_tracking", "orshot"],
        requires_session=False,  # Receives Redis client via injection
    ),
    RegisteredService(
        name="orshot_rate_limiter",
        service_class=OrshotRateLimiter,
        capabilities=["rate_limiting", "orshot"],
        requires_session=False,  # Receives Redis client via injection (optional)
    ),
    # Gemini Integration (Story 3.5)
    RegisteredService(
        name="gemini_image_client",
        service_class=GeminiImageClient,
        capabilities=["image_generation", "gemini"],
        requires_session=False,  # Receives api_key via injection
    ),
    # Auto-Publish Statistics Service (Story 3.8)
    RegisteredService(
        name="auto_publish_statistics_service",
        service_class=AutoPublishStatisticsService,
        capabilities=["auto_publish", "statistics_tracking"],
        requires_session=False,  # In-memory storage, future database persistence via Protocol
    ),
    # Asset Usage Repository (Story 3.9)
    RegisteredService(
        name="asset_usage_repository",
        service_class=AssetUsageRepository,
        capabilities=["asset_tracking", "usage_storage"],
        requires_session=False,  # In-memory storage, future database persistence via Protocol
    ),
    # B2B Lead Scanner Services (Story 5.1)
    RegisteredService(
        name="hunter_client",
        service_class=HunterClient,
        capabilities=["b2b_lead_research", "hunter_io"],
        requires_session=False,  # Receives HunterClientConfig via injection
    ),
    RegisteredService(
        name="lead_harvester",
        service_class=LeadHarvester,
        capabilities=["b2b_lead_research", "lead_enrichment"],
        requires_session=False,  # Receives HunterClient via injection
    ),
    RegisteredService(
        name="lead_transformer",
        service_class=LeadTransformer,
        capabilities=["b2b_lead_research"],
        requires_session=False,  # Receives LeadScannerConfig via injection
    ),
    RegisteredService(
        name="lead_duplicate_checker",
        service_class=LeadDuplicateChecker,
        capabilities=["b2b_lead_research", "duplicate_detection"],
        requires_session=False,  # Receives LeadRepository via injection
    ),
    RegisteredService(
        name="b2b_lead_pipeline",
        service_class=B2BLeadPipeline,
        capabilities=["b2b_lead_research", "lead_pipeline"],
        requires_session=False,  # Receives all stage components via injection
    ),
    RegisteredService(
        name="lead_repository",
        service_class=LeadRepository,
        capabilities=["lead_storage", "b2b_lead_research"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    # Lead Enrichment Services (Story 5.2)
    RegisteredService(
        name="website_analyzer",
        service_class=WebsiteAnalyzer,
        capabilities=["lead_enrichment", "website_analysis"],
        requires_session=False,  # Receives httpx.AsyncClient via injection
    ),
    RegisteredService(
        name="business_analyzer",
        service_class=BusinessAnalyzer,
        capabilities=["lead_enrichment", "business_analysis"],
        requires_session=False,  # Receives LLMClient via injection
    ),
    RegisteredService(
        name="hunter_enricher",
        service_class=HunterEnricher,
        capabilities=["lead_enrichment", "hunter_io"],
        requires_session=False,  # Receives HunterClient via injection
    ),
    RegisteredService(
        name="social_analyzer",
        service_class=SocialAnalyzer,
        capabilities=["lead_enrichment", "social_media_analysis"],
        requires_session=False,  # No external dependencies
    ),
    RegisteredService(
        name="enrichment_scorer",
        service_class=EnrichmentScorer,
        capabilities=["lead_enrichment", "lead_scoring"],
        requires_session=False,  # Receives EnrichmentConfig via injection
    ),
    RegisteredService(
        name="lead_enrichment_service",
        service_class=LeadEnrichmentService,
        capabilities=["lead_enrichment"],
        requires_session=False,  # Receives all analyzers via injection
    ),
    RegisteredService(
        name="enrichment_pipeline",
        service_class=EnrichmentPipeline,
        capabilities=["lead_enrichment", "lead_pipeline"],
        requires_session=False,  # Receives LeadRepository and LeadEnrichmentService via injection
    ),
    # Outreach Draft Generator Services (Story 5.3)
    RegisteredService(
        name="outreach_template_registry",
        service_class=OutreachTemplateRegistry,
        capabilities=["lead_outreach", "template_management"],
        requires_session=False,  # No external dependencies, manages templates in-memory
    ),
    RegisteredService(
        name="outreach_service",
        service_class=OutreachService,
        capabilities=["lead_outreach", "email_generation"],
        requires_session=False,  # Receives all outreach components via injection
    ),
    RegisteredService(
        name="outreach_draft_generator",
        service_class=OutreachDraftGenerator,
        capabilities=["lead_outreach", "draft_generation"],
        requires_session=False,  # Receives LLM, PersonalizationEngine, TemplateRegistry via injection
    ),
    RegisteredService(
        name="personalization_engine",
        service_class=PersonalizationEngine,
        capabilities=["lead_outreach", "personalization"],
        requires_session=False,  # Receives config via injection
    ),
    RegisteredService(
        name="lead_type_classifier",
        service_class=LeadTypeClassifier,
        capabilities=["lead_outreach", "lead_classification"],
        requires_session=False,  # Receives LLMClient via injection
    ),
    RegisteredService(
        name="outreach_validator",
        service_class=OutreachValidator,
        capabilities=["lead_outreach", "brand_voice_validation"],
        requires_session=False,  # Receives BrandVoiceValidator via injection
    ),
    RegisteredService(
        name="outreach_pipeline",
        service_class=OutreachPipeline,
        capabilities=["lead_outreach", "lead_pipeline"],
        requires_session=False,  # Receives LeadRepository and OutreachService via injection
    ),
    RegisteredService(
        name="outreach_approval_integration",
        service_class=OutreachApprovalIntegration,
        capabilities=["lead_outreach", "approval_queue"],
        requires_session=False,  # No external dependencies
    ),
    # Gmail Sender Services (Story 5.4)
    RegisteredService(
        name="gmail_client",
        service_class=GmailClient,
        capabilities=["gmail_integration", "email_send"],
        requires_session=False,  # Receives GmailCredentialsManager via injection
    ),
    RegisteredService(
        name="gmail_credentials_manager",
        service_class=GmailCredentialsManager,
        capabilities=["gmail_integration", "credential_management"],
        requires_session=False,  # Receives GmailConfig via injection
    ),
    RegisteredService(
        name="gmail_send_service",
        service_class=GmailSendService,
        capabilities=["email_send", "gmail_integration"],
        requires_session=False,  # Receives all Gmail components via injection
    ),
    RegisteredService(
        name="gmail_send_pipeline",
        service_class=GmailSendPipeline,
        capabilities=["email_send", "lead_pipeline"],
        requires_session=False,  # Receives LeadRepository and GmailSendService via injection
    ),
    RegisteredService(
        name="gdpr_pre_send_validator",
        service_class=GDPRPreSendValidator,
        capabilities=["gdpr_validation", "email_send"],
        requires_session=False,  # No external dependencies
    ),
    RegisteredService(
        name="utm_injector",
        service_class=UTMInjector,
        capabilities=["utm_tracking", "email_send"],
        requires_session=False,  # No external dependencies
    ),
    RegisteredService(
        name="signature_builder",
        service_class=SignatureBuilder,
        capabilities=["email_signature", "email_send"],
        requires_session=False,  # Receives GmailConfig via injection
    ),
    RegisteredService(
        name="gmail_rate_limiter",
        service_class=GmailRateLimiter,
        capabilities=["rate_limiting", "email_send"],
        requires_session=False,  # Receives GmailRateLimitConfig via injection
    ),
    # Pipeline Service (Story 5.5)
    RegisteredService(
        name="pipeline_service",
        service_class=PipelineService,
        capabilities=["pipeline_dashboard", "lead_status_tracking"],
        requires_session=False,  # Receives LeadRepository via injection
    ),
    RegisteredService(
        name="csv_exporter",
        service_class=CSVExporter,
        capabilities=["pipeline_export", "csv_generation"],
        requires_session=False,  # Receives LeadRepository via injection
    ),
    # Health Claims Monitor Services (Story 6.1)
    RegisteredService(
        name="health_claims_monitor",
        service_class=HealthClaimsMonitorPipeline,
        capabilities=["regulatory_monitoring", "health_claims"],
        requires_session=True,  # Pipeline uses repository which requires session
    ),
    RegisteredService(
        name="health_claims_client",
        service_class=HealthClaimsClient,
        capabilities=["eu_data_access"],
        requires_session=False,  # Receives httpx.AsyncClient and RetryMiddleware via injection
    ),
    RegisteredService(
        name="health_claims_repository",
        service_class=HealthClaimsRepository,
        capabilities=["regulatory_storage"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="register_parser",
        service_class=RegisterParser,
        capabilities=["regulatory_monitoring", "data_parsing"],
        requires_session=False,  # Stateless parser
    ),
    RegisteredService(
        name="relevance_filter",
        service_class=RelevanceFilter,
        capabilities=["regulatory_monitoring", "relevance_filtering"],
        requires_session=False,  # Receives keyword config via injection
    ),
    RegisteredService(
        name="change_detector",
        service_class=ChangeDetector,
        capabilities=["regulatory_monitoring", "change_detection"],
        requires_session=False,  # Receives keyword config via injection
    ),
    # Novel Food Catalogue Monitor Services (Story 6.2)
    RegisteredService(
        name="novel_food_monitor",
        service_class=NovelFoodMonitorPipeline,
        capabilities=["regulatory_monitoring", "novel_food"],
        requires_session=True,  # Pipeline uses repository which requires session
    ),
    RegisteredService(
        name="novel_food_client",
        service_class=NovelFoodCatalogueClient,
        capabilities=["eu_data_access", "novel_food"],
        requires_session=False,  # Receives httpx.AsyncClient and RetryMiddleware via injection
    ),
    RegisteredService(
        name="novel_food_repository",
        service_class=NovelFoodRepository,
        capabilities=["regulatory_storage", "novel_food"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="catalogue_parser",
        service_class=CatalogueParser,
        capabilities=["regulatory_monitoring", "data_parsing", "novel_food"],
        requires_session=False,  # Stateless parser
    ),
    RegisteredService(
        name="novel_food_change_detector",
        service_class=NovelFoodChangeDetector,
        capabilities=["regulatory_monitoring", "change_detection", "novel_food"],
        requires_session=False,  # Receives species config via injection
    ),
    # Mattilsynet Regulatory Monitor Services (Story 6.3)
    RegisteredService(
        name="mattilsynet_monitor",
        service_class=MattilsynetMonitorPipeline,
        capabilities=["regulatory_monitoring", "mattilsynet"],
        requires_session=True,  # Pipeline uses repository which requires session
    ),
    RegisteredService(
        name="mattilsynet_client",
        service_class=MattilsynetClient,
        capabilities=["norwegian_data_access"],
        requires_session=False,  # Receives httpx.AsyncClient and RetryMiddleware via injection
    ),
    RegisteredService(
        name="mattilsynet_repository",
        service_class=MattilsynetRepository,
        capabilities=["regulatory_storage"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="mattilsynet_feed_parser",
        service_class=MattilsynetFeedParser,
        capabilities=["regulatory_monitoring", "data_parsing"],
        requires_session=False,  # Stateless parser
    ),
    RegisteredService(
        name="mattilsynet_page_parser",
        service_class=MattilsynetPageParser,
        capabilities=["regulatory_monitoring", "data_parsing"],
        requires_session=False,  # Stateless parser
    ),
    RegisteredService(
        name="norwegian_keyword_matcher",
        service_class=NorwegianKeywordMatcher,
        capabilities=["text_analysis"],
        requires_session=False,  # Receives keyword config via injection
    ),
    RegisteredService(
        name="page_change_detector",
        service_class=PageChangeDetector,
        capabilities=["change_detection"],
        requires_session=False,  # Stateless detector
    ),
    # Claims Alert Services (Story 6.4)
    RegisteredService(
        name="claims_alert_service",
        service_class=ClaimsAlertService,
        capabilities=["regulatory_alerting", "claims_alerts", "discord_notifications"],
        requires_session=False,  # No database — event processing only
    ),
    RegisteredService(
        name="claims_alert_formatter",
        service_class=ClaimsAlertFormatter,
        capabilities=["regulatory_alerting", "notification_formatting"],
        requires_session=False,
    ),
    RegisteredService(
        name="dawo_relevance_filter",
        service_class=DAWORelevanceFilter,
        capabilities=["regulatory_alerting", "relevance_filtering"],
        requires_session=False,
    ),
    RegisteredService(
        name="claims_alert_batcher",
        service_class=ClaimsAlertBatcher,
        capabilities=["regulatory_alerting", "notification_batching"],
        requires_session=False,
    ),
    RegisteredService(
        name="regulatory_alert_subscriber",
        service_class=RegulatoryAlertSubscriber,
        capabilities=["regulatory_alerting", "event_subscription"],
        requires_session=False,
    ),
    # Competitor Content Scanner Services (Story 6.5)
    RegisteredService(
        name="competitor_scan_pipeline",
        service_class=CompetitorScanPipeline,
        capabilities=["competitor_monitoring", "content_scanning"],
        requires_session=True,  # Pipeline uses repository which requires session
    ),
    RegisteredService(
        name="website_scraper_client",
        service_class=WebsiteScraperClient,
        capabilities=["competitor_monitoring", "web_scraping"],
        requires_session=False,  # Receives httpx.AsyncClient and RetryMiddleware via injection
    ),
    RegisteredService(
        name="competitor_content_parser",
        service_class=CompetitorContentParser,
        capabilities=["competitor_monitoring", "content_parsing"],
        requires_session=False,  # Receives health_language_keywords via injection
    ),
    RegisteredService(
        name="competitor_duplicate_checker",
        service_class=CompetitorDuplicateChecker,
        capabilities=["competitor_monitoring", "deduplication"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="competitor_repository",
        service_class=CompetitorRepository,
        capabilities=["competitor_monitoring", "competitor_storage"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    # Health Claim Extraction Services (Story 6.6)
    RegisteredService(
        name="claim_pattern_matcher",
        service_class=ClaimPatternMatcher,
        capabilities=["health_claim_extraction", "pattern_matching"],
        requires_session=False,  # Receives config via injection
    ),
    RegisteredService(
        name="claim_llm_classifier",
        service_class=ClaimLLMClassifier,
        capabilities=["health_claim_extraction", "llm_classification"],
        requires_session=False,  # Receives LLMClient and RetryMiddleware via injection
    ),
    RegisteredService(
        name="health_claim_repository",
        service_class=HealthClaimRepository,
        capabilities=["health_claim_extraction", "claim_storage"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    # Violation Detection Services (Story 6.7)
    RegisteredService(
        name="violation_classifier",
        service_class=ViolationClassifier,
        capabilities=["competitor_monitoring", "violation_classification"],
        requires_session=False,  # Receives ViolationDetectionConfig via injection
    ),
    RegisteredService(
        name="violation_repository",
        service_class=ViolationRepository,
        capabilities=["competitor_monitoring", "violation_storage"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    # Evidence Collection Services (Story 6.8)
    RegisteredService(
        name="playwright_screenshot_service",
        service_class=PlaywrightScreenshotService,
        capabilities=["competitor_monitoring", "screenshot_capture"],
        requires_session=False,  # Receives EvidenceCollectionConfig via injection
    ),
    RegisteredService(
        name="evidence_storage_service",
        service_class=EvidenceStorageService,
        capabilities=["competitor_monitoring", "evidence_storage"],
        requires_session=False,  # Receives EvidenceCollectionConfig via injection
    ),
    RegisteredService(
        name="evidence_repository",
        service_class=EvidenceRepository,
        capabilities=["competitor_monitoring", "evidence_storage"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    # Evidence Download Service (Story 6.9)
    RegisteredService(
        name="evidence_download_service",
        service_class=EvidenceDownloadService,
        capabilities=["competitor_monitoring", "evidence_download"],
        requires_session=False,  # Receives EvidenceStorageService via injection
    ),
    # Violation Report Generator (Story 6.10)
    RegisteredService(
        name="weasyprint_pdf_generator",
        service_class=WeasyPrintPDFGenerator,
        capabilities=["competitor_monitoring", "violation_reports"],
        requires_session=True,  # Requires AsyncSession for audit logging
    ),
    RegisteredService(
        name="report_storage_service",
        service_class=ReportStorageService,
        capabilities=["competitor_monitoring", "report_storage"],
        requires_session=False,  # Receives ViolationReportConfig via injection
    ),
    # Instagram Analytics Services (Story 7.1)
    RegisteredService(
        name="instagram_metrics_repository",
        service_class=InstagramMetricsRepository,
        capabilities=["instagram_analytics", "metrics_storage"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="instagram_metrics_collector",
        service_class=InstagramMetricsCollector,
        capabilities=["instagram_analytics", "metrics_collection"],
        requires_session=False,  # Receives client, repository, config via injection
    ),
    RegisteredService(
        name="metrics_query_service",
        service_class=MetricsQueryService,
        capabilities=["instagram_analytics", "metrics_query", "performance_comparison"],
        requires_session=False,  # Receives repository via injection
    ),
    # UTM Click-Through Tracking Services (Story 7.2)
    RegisteredService(
        name="utm_repository",
        service_class=UTMRepository,
        capabilities=["utm_tracking", "click_tracking", "link_management"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="short_link_service",
        service_class=ShortLinkService,
        capabilities=["utm_tracking", "link_generation", "click_tracking"],
        requires_session=False,  # Receives UTMRepository and UTMConfig via injection
    ),
    RegisteredService(
        name="click_analytics_service",
        service_class=ClickAnalyticsService,
        capabilities=["utm_tracking", "click_analytics", "performance_comparison"],
        requires_session=False,  # Receives UTMRepository and MetricsQueryService via injection
    ),
    # Shopify Sales Attribution Services (Story 7.3)
    RegisteredService(
        name="attribution_repository",
        service_class=AttributionRepository,
        capabilities=["shopify_attribution", "revenue_data"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="attribution_service",
        service_class=AttributionService,
        capabilities=["shopify_attribution", "order_processing"],
        requires_session=False,  # Receives AttributionRepository, UTMRepository, AttributionConfig via injection
    ),
    RegisteredService(
        name="revenue_analytics_service",
        service_class=RevenueAnalyticsService,
        capabilities=["shopify_attribution", "revenue_analytics", "combined_analytics"],
        requires_session=False,  # Receives AttributionRepository, ClickAnalyticsService, MetricsQueryService via injection
    ),
    # Post-Publish Quality Scoring Services (Story 7.4)
    RegisteredService(
        name="quality_scoring_repository",
        service_class=QualityScoringRepository,
        capabilities=["quality_scoring", "scoring_storage"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="comment_sentiment_scorer",
        service_class=CommentSentimentScorer,
        capabilities=["quality_scoring", "sentiment_analysis"],
        requires_session=False,  # Pure Python keyword scoring, no external deps
    ),
    RegisteredService(
        name="post_publish_scoring_service",
        service_class=PostPublishScoringService,
        capabilities=["quality_scoring", "post_scoring", "performance_analysis"],
        requires_session=False,  # Receives all analytics services + repository via injection
    ),
    RegisteredService(
        name="variance_analyzer",
        service_class=VarianceAnalyzer,
        capabilities=["quality_scoring", "variance_analysis", "correlation_analysis"],
        requires_session=False,  # Receives QualityScoringRepository via injection
    ),
    # Performance Feedback Loop (Story 7.5)
    RegisteredService(
        name="feedback_loop_repository",
        service_class=FeedbackLoopRepository,
        capabilities=["analytics", "feedback_storage"],
        requires_session=True,
    ),
    RegisteredService(
        name="content_performance_analyzer",
        service_class=ContentPerformanceAnalyzer,
        capabilities=["analytics", "performance_analysis"],
        requires_session=False,  # Receives repos via injection
    ),
    RegisteredService(
        name="weight_adjuster",
        service_class=WeightAdjuster,
        capabilities=["analytics", "weight_management"],
        requires_session=False,  # Receives analyzer + repo + config via injection
    ),
    RegisteredService(
        name="feedback_loop_service",
        service_class=FeedbackLoopService,
        capabilities=["analytics", "feedback_loop"],
        requires_session=False,  # Receives all deps via injection
    ),
    # Agent Schedule Configuration Services (Story 7.6)
    RegisteredService(
        name="agent_schedule_repository",
        service_class=AgentScheduleRepository,
        capabilities=["scheduling", "schedule_storage"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="agent_schedule_service",
        service_class=AgentScheduleService,
        capabilities=["scheduling", "schedule_management"],
        requires_session=False,  # Receives repository and config via injection
    ),
    # Manual Trigger Service (Story 7.7)
    RegisteredService(
        name="manual_trigger_service",
        service_class=ManualTriggerService,
        capabilities=["scheduling", "manual_trigger", "team_trigger"],
        requires_session=False,  # Receives repository and config via injection
    ),
    # Execution Dashboard Services (Story 7.8)
    RegisteredService(
        name="execution_log_repository",
        service_class=ExecutionLogRepository,
        capabilities=["scheduling", "execution_logs"],
        requires_session=True,  # Requires AsyncSession injection
    ),
    RegisteredService(
        name="execution_log_service",
        service_class=ExecutionLogService,
        capabilities=["scheduling", "execution_dashboard"],
        requires_session=False,  # Receives repos via injection
    ),
    # Calendar Sync Service (Story 7.9)
    RegisteredService(
        name="calendar_sync_service",
        service_class=CalendarSyncService,
        capabilities=["calendar", "content_sync"],
        requires_session=False,  # Receives CalendarClient, EventBuilder, CalendarConfig via injection
    ),
    # Graceful Degradation Services (Story 7.10)
    RegisteredService(
        name="service_health_registry",
        service_class=ServiceHealthRegistry,
        capabilities=["health_monitoring", "degradation"],
        requires_session=False,  # Receives DegradationConfig + Redis via injection
    ),
    RegisteredService(
        name="recovery_processor",
        service_class=RecoveryProcessor,
        capabilities=["recovery", "degradation"],
        requires_session=False,  # Receives config, registry, queue, enqueuer via injection
    ),
    RegisteredService(
        name="degradation_alert_service",
        service_class=DegradationAlertService,
        capabilities=["alerts", "degradation"],
        requires_session=False,  # Receives config, registry, discord, redis via injection
    ),
]
