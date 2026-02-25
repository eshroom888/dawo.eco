"""Tests for claim extraction DTOs/schemas.

Story 6-6, Task 11: Schema validation tests.
"""

from uuid import uuid4

import pytest

from teams.dawo.scanners.claim_extraction.schemas import (
    ClaimExtractionResult,
    ContentExtractionResult,
    ExtractionBatchResult,
    LLMExtractionRequest,
    LLMExtractionResponse,
    PatternMatch,
)


class TestPatternMatch:
    """Tests for PatternMatch dataclass."""

    def test_create_minimal(self) -> None:
        match = PatternMatch(
            matched_text="boosts immunity",
            pattern="boosts immunity",
            category="enhancement",
            language="en",
            start_pos=0,
            end_pos=15,
            surrounding_context="boosts immunity naturally",
        )
        assert match.matched_text == "boosts immunity"
        assert match.category == "enhancement"
        assert match.language == "en"
        assert match.start_pos == 0
        assert match.end_pos == 15

    def test_fields_are_accessible(self) -> None:
        match = PatternMatch(
            matched_text="cures cancer",
            pattern=r"cures?\s+cancer",
            category="treatment",
            language="en",
            start_pos=10,
            end_pos=22,
            surrounding_context="product cures cancer guaranteed",
        )
        assert match.pattern == r"cures?\s+cancer"
        assert match.surrounding_context == "product cures cancer guaranteed"


class TestClaimExtractionResult:
    """Tests for ClaimExtractionResult dataclass."""

    def test_create_with_required_fields(self) -> None:
        result = ClaimExtractionResult(
            claim_text="boosts immunity",
            surrounding_context="product boosts immunity",
            claim_category="enhancement",
            confidence_score=90,
            language_detected="en",
            extraction_method="hybrid",
        )
        assert result.claim_text == "boosts immunity"
        assert result.confidence_score == 90
        assert result.extraction_method == "hybrid"
        assert result.eu_article_reference is None
        assert result.matched_pattern is None
        assert result.llm_reasoning is None

    def test_create_with_all_fields(self) -> None:
        result = ClaimExtractionResult(
            claim_text="cures cancer",
            surrounding_context="our product cures cancer",
            claim_category="treatment",
            confidence_score=95,
            language_detected="en",
            extraction_method="hybrid",
            eu_article_reference="prohibited",
            matched_pattern=r"cures?\s+cancer",
            llm_reasoning="Explicit treatment claim",
        )
        assert result.eu_article_reference == "prohibited"
        assert result.matched_pattern == r"cures?\s+cancer"
        assert result.llm_reasoning == "Explicit treatment claim"

    def test_defaults_for_optional_fields(self) -> None:
        result = ClaimExtractionResult(
            claim_text="test",
            surrounding_context="test context",
            claim_category="general_wellness",
            confidence_score=60,
            language_detected="no",
            extraction_method="regex",
        )
        assert result.eu_article_reference is None
        assert result.matched_pattern is None
        assert result.llm_reasoning is None


class TestContentExtractionResult:
    """Tests for ContentExtractionResult dataclass."""

    def test_defaults(self) -> None:
        content_id = uuid4()
        result = ContentExtractionResult(competitor_content_id=content_id)
        assert result.competitor_content_id == content_id
        assert result.claims == []
        assert result.extraction_status == "no_claims"
        assert result.error_message is None

    def test_with_claims(self) -> None:
        claim = ClaimExtractionResult(
            claim_text="boosts immunity",
            surrounding_context="",
            claim_category="enhancement",
            confidence_score=80,
            language_detected="en",
            extraction_method="hybrid",
        )
        result = ContentExtractionResult(
            competitor_content_id=uuid4(),
            claims=[claim],
            extraction_status="extracted",
        )
        assert len(result.claims) == 1
        assert result.extraction_status == "extracted"


class TestExtractionBatchResult:
    """Tests for ExtractionBatchResult dataclass."""

    def test_defaults_all_zero(self) -> None:
        batch = ExtractionBatchResult()
        assert batch.total_processed == 0
        assert batch.total_claims_extracted == 0
        assert batch.items_with_claims == 0
        assert batch.items_no_claims == 0
        assert batch.items_error == 0
        assert batch.high_confidence_claims == 0
        assert batch.manual_review_claims == 0

    def test_mutable_counters(self) -> None:
        batch = ExtractionBatchResult()
        batch.total_processed += 5
        batch.total_claims_extracted += 3
        batch.items_error += 1
        assert batch.total_processed == 5
        assert batch.total_claims_extracted == 3
        assert batch.items_error == 1


class TestLLMExtractionRequest:
    """Tests for LLMExtractionRequest dataclass."""

    def test_defaults(self) -> None:
        req = LLMExtractionRequest(content_text="Some content here")
        assert req.content_text == "Some content here"
        assert req.pre_filter_matches == []
        assert req.language_hint is None

    def test_with_matches(self) -> None:
        req = LLMExtractionRequest(
            content_text="boosts immunity",
            pre_filter_matches=[{"text": "boosts immunity", "category": "enhancement"}],
            language_hint="en",
        )
        assert len(req.pre_filter_matches) == 1
        assert req.language_hint == "en"


class TestLLMExtractionResponse:
    """Tests for LLMExtractionResponse dataclass."""

    def test_defaults(self) -> None:
        resp = LLMExtractionResponse()
        assert resp.claims == []
        assert resp.raw_response == ""

    def test_with_data(self) -> None:
        resp = LLMExtractionResponse(
            claims=[{"claim_text": "boosts immunity"}],
            raw_response='{"claims": []}',
        )
        assert len(resp.claims) == 1
        assert resp.raw_response == '{"claims": []}'
