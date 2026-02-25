"""Health Claim Extraction Engine package.

Epic 6, Story 6-6: Health Claim Extraction Engine.

Hybrid regex+LLM extraction pipeline for detecting health claims
in competitor content. Stages: regex pre-filter -> LLM classification
-> claim storage -> event emission.

Public API:
    HealthClaimExtractionEngine: Main extraction pipeline.
    ClaimPatternMatcher: Regex pre-filter.
    ClaimLLMClassifier: LLM-based claim classifier.
    HealthClaimRepository: Claim storage repository.
    HealthClaimExtractionConfig: Extraction configuration.
    ClaimPattern: Single pattern definition.
    build_health_claim_extraction_config: Config builder from dict.
"""

from teams.dawo.scanners.claim_extraction.config import (
    ClaimPattern,
    HealthClaimExtractionConfig,
    build_health_claim_extraction_config,
)
from teams.dawo.scanners.claim_extraction.engine import HealthClaimExtractionEngine
from teams.dawo.scanners.claim_extraction.llm_classifier import ClaimLLMClassifier
from teams.dawo.scanners.claim_extraction.pattern_matcher import ClaimPatternMatcher
from teams.dawo.scanners.claim_extraction.repository import HealthClaimRepository
from teams.dawo.scanners.claim_extraction.schemas import (
    ClaimExtractionResult,
    ContentExtractionResult,
    ExtractionBatchResult,
    LLMExtractionRequest,
    LLMExtractionResponse,
    PatternMatch,
)

__all__ = [
    "ClaimPattern",
    "HealthClaimExtractionConfig",
    "build_health_claim_extraction_config",
    "HealthClaimExtractionEngine",
    "ClaimLLMClassifier",
    "ClaimPatternMatcher",
    "HealthClaimRepository",
    "ClaimExtractionResult",
    "ContentExtractionResult",
    "ExtractionBatchResult",
    "LLMExtractionRequest",
    "LLMExtractionResponse",
    "PatternMatch",
]
