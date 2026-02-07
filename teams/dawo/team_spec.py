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
]
