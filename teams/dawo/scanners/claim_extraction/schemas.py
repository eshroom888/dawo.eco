"""DTOs for Health Claim Extraction Engine.

Epic 6, Story 6-6: Health Claim Extraction Engine.

Data transfer objects for the extraction pipeline stages.

Classes:
    PatternMatch: Result from regex pre-filter.
    ClaimExtractionResult: Single extracted claim.
    ContentExtractionResult: All claims from one content item.
    ExtractionBatchResult: Statistics for a batch run.
    LLMExtractionRequest: Input to LLM classifier.
    LLMExtractionResponse: Output from LLM classifier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class PatternMatch:
    """Result of a regex pattern match.

    Attributes:
        matched_text: The text that was matched.
        pattern: The regex pattern string that matched.
        category: Claim category from the pattern config.
        language: Language code from the pattern config.
        start_pos: Start position in source text.
        end_pos: End position in source text.
        surrounding_context: Text around the match for context.
    """

    matched_text: str
    pattern: str
    category: str
    language: str
    start_pos: int
    end_pos: int
    surrounding_context: str


@dataclass
class ClaimExtractionResult:
    """Single extracted health claim.

    Attributes:
        claim_text: Exact extracted phrase.
        surrounding_context: Text around the claim for context.
        claim_category: Category (treatment/prevention/enhancement/general_wellness).
        confidence_score: Confidence 0-100.
        language_detected: Language code ("en", "no", "unknown").
        extraction_method: Method ("regex", "llm", "hybrid").
        eu_article_reference: EU article (e.g. "13.1", "prohibited"). None if unknown.
        matched_pattern: Regex pattern that matched. None if LLM-only.
        llm_reasoning: LLM reasoning text. None if regex-only.
    """

    claim_text: str
    surrounding_context: str
    claim_category: str
    confidence_score: int
    language_detected: str
    extraction_method: str
    eu_article_reference: str | None = None
    matched_pattern: str | None = None
    llm_reasoning: str | None = None


@dataclass
class ContentExtractionResult:
    """Extraction results for one content item.

    Attributes:
        competitor_content_id: UUID of the source CompetitorContent.
        claims: List of extracted claims.
        extraction_status: Result status ("extracted", "no_claims", "error").
        error_message: Error details if status is "error".
    """

    competitor_content_id: UUID
    claims: list[ClaimExtractionResult] = field(default_factory=list)
    extraction_status: str = "no_claims"
    error_message: str | None = None


@dataclass
class ExtractionBatchResult:
    """Statistics for a batch extraction run.

    Attributes:
        total_processed: Number of content items processed.
        total_claims_extracted: Total claims found across all items.
        items_with_claims: Items that had at least one claim.
        items_no_claims: Items with no health claims.
        items_error: Items that failed extraction.
        high_confidence_claims: Claims above confidence threshold.
        manual_review_claims: Claims below confidence threshold.
    """

    total_processed: int = 0
    total_claims_extracted: int = 0
    items_with_claims: int = 0
    items_no_claims: int = 0
    items_error: int = 0
    high_confidence_claims: int = 0
    manual_review_claims: int = 0


@dataclass
class LLMExtractionRequest:
    """Input for LLM claim classification.

    Attributes:
        content_text: Full content text to analyze.
        pre_filter_matches: Regex matches as hints for LLM.
        language_hint: Detected language hint ("en", "no", None).
    """

    content_text: str
    pre_filter_matches: list[dict] = field(default_factory=list)
    language_hint: str | None = None


@dataclass
class LLMExtractionResponse:
    """Output from LLM claim classification.

    Attributes:
        claims: List of claim dicts from LLM response.
        raw_response: Raw LLM response string.
    """

    claims: list[dict] = field(default_factory=list)
    raw_response: str = ""


__all__ = [
    "PatternMatch",
    "ClaimExtractionResult",
    "ContentExtractionResult",
    "ExtractionBatchResult",
    "LLMExtractionRequest",
    "LLMExtractionResponse",
]
