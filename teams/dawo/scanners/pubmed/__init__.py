"""PubMed Scientific Research Scanner for DAWO research intelligence pipeline.

This module implements the FIFTH scanner in the Harvester Framework,
following the pattern established by Reddit Scanner (Story 2.3),
YouTube Scanner (Story 2.4), Instagram Scanner (Story 2.5), and News Scanner (Story 2.6).

UNIQUE to PubMed Scanner:
    - Uses Biopython's Entrez module for NCBI E-utilities
    - Has TWO LLM stages: FindingSummarizer AND ClaimValidator (both tier="generate")
    - Weekly schedule (scientific publications have slower cadence)
    - High-value content: peer-reviewed studies deserve score boost
    - Scientific metadata extraction: DOI, study type, sample size, authors
    - Claim validation specific to EU Health Claims context

Harvester Framework Pipeline (Extended for PubMed):
    [Scanner] -> [Harvester] -> [FindingSummarizer] -> [ClaimValidator] -> [Transformer] -> [Validator] -> [Scorer] -> [Publisher] -> [Research Pool]
         |           |                  |                       |                  |              |            |           |
       scan()    harvest()       summarize()          validate_claim()       transform()    validate()    score()    publish()
       tier=scan  tier=scan       tier=generate          tier=generate         tier=scan      tier=scan   tier=scan   tier=scan

Components:
    - PubMedScanner: Main agent class for scan stage
    - PubMedClient: Entrez API client using Biopython
    - PubMedHarvester: Parses articles and extracts metadata
    - FindingSummarizer: LLM stage for plain-language summaries (tier="generate")
    - ClaimValidator: LLM stage for EU claim assessment (tier="generate")
    - PubMedTransformer: Standardizes data for Research Pool
    - PubMedValidator: EU compliance validation
    - PubMedResearchPipeline: Orchestrates full pipeline

Configuration:
    - EntrezConfig: NCBI E-utilities credentials
    - PubMedScannerConfig: Scanner behavior settings

Schemas:
    - RawPubMedArticle: Raw data from Entrez
    - HarvestedArticle: Article with parsed metadata
    - FindingSummary: LLM-generated summary
    - ClaimValidationResult: EU claim assessment
    - ValidatedResearch: Post-compliance data
    - ScanResult: Scanner output with stats
    - PipelineResult: Full pipeline result
    - PipelineStatus: Pipeline status enum
    - ContentPotential: Content usage categories
    - StudyType: Study type classification

Exceptions:
    - PubMedScanError: Scanner-level errors
    - PubMedSearchError: Search failures
    - PubMedFetchError: Fetch failures
    - HarvesterError: Harvester stage errors
    - SummarizationError: Summarizer stage errors
    - ClaimValidationError: Claim validator errors
    - TransformerError: Transformer stage errors
    - ValidatorError: Validator stage errors
    - PipelineError: Pipeline orchestration errors

Usage:
    from teams.dawo.scanners.pubmed import (
        PubMedScanner,
        PubMedClient,
        PubMedScannerConfig,
        PubMedResearchPipeline,
    )

    # Components are created and wired by Team Builder
    pipeline = PubMedResearchPipeline(
        scanner, harvester, summarizer, claim_validator,
        transformer, validator, scorer, publisher
    )
    result = await pipeline.execute()

Registration:
    All components registered in teams/dawo/team_spec.py
    - Scanner, Harvester, Transformer, Validator: tier="scan"
    - FindingSummarizer, ClaimValidator: tier="generate"
"""

from .agent import PubMedScanner, PubMedScanError
from .tools import (
    PubMedClient,
    PubMedSearchError,
    PubMedFetchError,
    extract_sample_size,
    classify_study_type,
)
from .config import (
    EntrezConfig,
    PubMedScannerConfig,
    # Config constants
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MAX_RESULTS_PER_QUERY,
    DEFAULT_BATCH_SIZE,
    RATE_LIMIT_NO_KEY,
    RATE_LIMIT_WITH_KEY,
)
from .schemas import (
    RawPubMedArticle,
    HarvestedArticle,
    FindingSummary,
    ClaimValidationResult,
    ContentPotential,
    StudyType,
    ValidatedResearch,
    ScanResult,
    ScanStatistics,
    PipelineResult,
    PipelineStatistics,
    PipelineStatus,
)
from .prompts import (
    FINDING_SUMMARIZATION_PROMPT,
    CLAIM_VALIDATION_PROMPT,
    SAMPLE_SIZE_PATTERNS,
    STUDY_TYPE_MAPPINGS,
)

# Pipeline stages
from .harvester import PubMedHarvester, HarvesterError
from .finding_summarizer import FindingSummarizer, SummarizationError
from .claim_validator import ClaimValidator, ClaimValidationError
from .transformer import PubMedTransformer, TransformerError
from .validator import PubMedValidator, ValidatorError
from .pipeline import PubMedResearchPipeline, PipelineError

__all__ = [
    # Main agent
    "PubMedScanner",
    # Client
    "PubMedClient",
    # Config
    "EntrezConfig",
    "PubMedScannerConfig",
    # Config constants
    "DEFAULT_LOOKBACK_DAYS",
    "DEFAULT_MAX_RESULTS_PER_QUERY",
    "DEFAULT_BATCH_SIZE",
    "RATE_LIMIT_NO_KEY",
    "RATE_LIMIT_WITH_KEY",
    # Schemas
    "RawPubMedArticle",
    "HarvestedArticle",
    "FindingSummary",
    "ClaimValidationResult",
    "ContentPotential",
    "StudyType",
    "ValidatedResearch",
    "ScanResult",
    "ScanStatistics",
    "PipelineResult",
    "PipelineStatistics",
    "PipelineStatus",
    # Prompts
    "FINDING_SUMMARIZATION_PROMPT",
    "CLAIM_VALIDATION_PROMPT",
    "SAMPLE_SIZE_PATTERNS",
    "STUDY_TYPE_MAPPINGS",
    # Utility functions
    "extract_sample_size",
    "classify_study_type",
    # Exceptions
    "PubMedScanError",
    "PubMedSearchError",
    "PubMedFetchError",
    "HarvesterError",
    "SummarizationError",
    "ClaimValidationError",
    "TransformerError",
    "ValidatorError",
    "PipelineError",
    # Pipeline stages
    "PubMedHarvester",
    "FindingSummarizer",
    "ClaimValidator",
    "PubMedTransformer",
    "PubMedValidator",
    "PubMedResearchPipeline",
]
