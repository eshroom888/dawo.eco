"""Tests for HealthClaimExtractionEngine.

Story 6-6, Task 8: Extraction engine/pipeline.
"""

from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from teams.dawo.scanners.claim_extraction.config import (
    HealthClaimExtractionConfig,
    ClaimPattern,
)
from teams.dawo.scanners.claim_extraction.engine import HealthClaimExtractionEngine
from teams.dawo.scanners.claim_extraction.schemas import (
    ClaimExtractionResult,
    ExtractionBatchResult,
    PatternMatch,
)


@pytest.fixture
def config() -> HealthClaimExtractionConfig:
    return HealthClaimExtractionConfig(
        prohibited_patterns=(
            ClaimPattern(pattern="cures cancer", category="treatment", language="en"),
        ),
        borderline_patterns=(
            ClaimPattern(pattern="boosts immunity", category="enhancement", language="en"),
        ),
        batch_size=20,
        confidence_threshold=70,
        max_claims_per_content=10,
        use_llm=True,
    )


@pytest.fixture
def mock_competitor_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_pending_extraction = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_claim_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.save_claims = AsyncMock(return_value=0)
    repo.update_extraction_status = AsyncMock()
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_pattern_matcher() -> MagicMock:
    matcher = MagicMock()
    matcher.find_matches = MagicMock(return_value=[])
    matcher.detect_language = MagicMock(return_value="en")
    return matcher


@pytest.fixture
def mock_llm_classifier() -> AsyncMock:
    classifier = AsyncMock()
    classifier.classify_claims = AsyncMock(return_value=[])
    return classifier


@pytest.fixture
def mock_event_emitter() -> AsyncMock:
    emitter = AsyncMock()
    emitter.emit = AsyncMock()
    return emitter


@pytest.fixture
def make_content():
    """Factory for mock CompetitorContent objects."""
    def _make(content_text="Some content", has_health_language=True):
        content = MagicMock()
        content.id = uuid4()
        content.content_text = content_text
        content.competitor_name = "TestCompetitor"
        content.source_type = "website"
        content.has_health_language = has_health_language
        content.extraction_status = "pending"
        return content
    return _make


@pytest.fixture
def engine(
    config: HealthClaimExtractionConfig,
    mock_competitor_repo: AsyncMock,
    mock_claim_repo: AsyncMock,
    mock_pattern_matcher: MagicMock,
    mock_llm_classifier: AsyncMock,
    mock_event_emitter: AsyncMock,
) -> HealthClaimExtractionEngine:
    return HealthClaimExtractionEngine(
        competitor_repository=mock_competitor_repo,
        claim_repository=mock_claim_repo,
        pattern_matcher=mock_pattern_matcher,
        llm_classifier=mock_llm_classifier,
        event_emitter=mock_event_emitter,
        config=config,
    )


class TestHealthClaimExtractionEngine:
    """Tests for HealthClaimExtractionEngine."""

    @pytest.mark.asyncio
    async def test_full_pipeline_hybrid(
        self,
        engine: HealthClaimExtractionEngine,
        mock_competitor_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_llm_classifier: AsyncMock,
        mock_claim_repo: AsyncMock,
        make_content,
    ) -> None:
        content = make_content("Our product boosts immunity and cures cancer.")
        mock_competitor_repo.get_pending_extraction.return_value = [content]

        mock_pattern_matcher.find_matches.return_value = [
            PatternMatch(
                matched_text="boosts immunity",
                pattern="boosts immunity",
                category="enhancement",
                language="en",
                start_pos=12, end_pos=27,
                surrounding_context="product boosts immunity and c",
            ),
        ]

        mock_llm_classifier.classify_claims.return_value = [
            ClaimExtractionResult(
                claim_text="boosts immunity",
                surrounding_context="product boosts immunity",
                claim_category="enhancement",
                confidence_score=90,
                language_detected="en",
                extraction_method="hybrid",
            ),
        ]
        mock_claim_repo.save_claims.return_value = 1

        result = await engine.execute()
        assert isinstance(result, ExtractionBatchResult)
        assert result.total_processed == 1
        assert result.total_claims_extracted == 1
        assert result.items_with_claims == 1
        mock_claim_repo.update_extraction_status.assert_awaited()

    @pytest.mark.asyncio
    async def test_regex_only_mode(
        self,
        config: HealthClaimExtractionConfig,
        mock_competitor_repo: AsyncMock,
        mock_claim_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_event_emitter: AsyncMock,
        make_content,
    ) -> None:
        # llm_classifier=None means regex-only mode
        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=mock_pattern_matcher,
            llm_classifier=None,
            event_emitter=mock_event_emitter,
            config=config,
        )
        content = make_content("boosts immunity naturally")
        mock_competitor_repo.get_pending_extraction.return_value = [content]
        mock_pattern_matcher.find_matches.return_value = [
            PatternMatch(
                matched_text="boosts immunity",
                pattern="boosts immunity",
                category="enhancement",
                language="en",
                start_pos=0, end_pos=15,
                surrounding_context="boosts immunity naturally",
            ),
        ]
        mock_claim_repo.save_claims.return_value = 1

        result = await engine.execute()
        assert result.total_claims_extracted == 1

    @pytest.mark.asyncio
    async def test_no_matches_in_content(
        self,
        engine: HealthClaimExtractionEngine,
        mock_competitor_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_claim_repo: AsyncMock,
        make_content,
    ) -> None:
        content = make_content("Delicious mushroom recipes.")
        mock_competitor_repo.get_pending_extraction.return_value = [content]
        mock_pattern_matcher.find_matches.return_value = []

        result = await engine.execute()
        assert result.items_no_claims == 1
        assert result.total_claims_extracted == 0
        mock_claim_repo.update_extraction_status.assert_awaited()

    @pytest.mark.asyncio
    async def test_llm_disabled_in_config(
        self,
        mock_competitor_repo: AsyncMock,
        mock_claim_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_llm_classifier: AsyncMock,
        mock_event_emitter: AsyncMock,
        make_content,
    ) -> None:
        config = HealthClaimExtractionConfig(
            prohibited_patterns=(
                ClaimPattern(pattern="test", category="treatment", language="en"),
            ),
            use_llm=False,
        )
        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=mock_pattern_matcher,
            llm_classifier=mock_llm_classifier,
            event_emitter=mock_event_emitter,
            config=config,
        )
        content = make_content("test product")
        mock_competitor_repo.get_pending_extraction.return_value = [content]
        mock_pattern_matcher.find_matches.return_value = [
            PatternMatch(
                matched_text="test",
                pattern="test",
                category="treatment",
                language="en",
                start_pos=0, end_pos=4,
                surrounding_context="test product",
            ),
        ]
        mock_claim_repo.save_claims.return_value = 1

        result = await engine.execute()
        # LLM classifier should NOT be called
        mock_llm_classifier.classify_claims.assert_not_awaited()
        assert result.total_claims_extracted == 1

    @pytest.mark.asyncio
    async def test_per_item_error_handling(
        self,
        engine: HealthClaimExtractionEngine,
        mock_competitor_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_claim_repo: AsyncMock,
        make_content,
    ) -> None:
        good = make_content("Good content")
        bad = make_content("Bad content")
        mock_competitor_repo.get_pending_extraction.return_value = [bad, good]

        # First call raises, second returns empty
        mock_pattern_matcher.find_matches.side_effect = [
            RuntimeError("Parse error"),
            [],
        ]

        result = await engine.execute()
        assert result.items_error == 1
        assert result.items_no_claims == 1
        assert result.total_processed == 2

    @pytest.mark.asyncio
    async def test_batch_size_limiting(
        self,
        engine: HealthClaimExtractionEngine,
        mock_competitor_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        make_content,
    ) -> None:
        mock_competitor_repo.get_pending_extraction.return_value = []
        await engine.execute()
        # Verify the repo was called (batch_size limit is handled by repo query)
        mock_competitor_repo.get_pending_extraction.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_claims_capped_per_content(
        self,
        mock_competitor_repo: AsyncMock,
        mock_claim_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_llm_classifier: AsyncMock,
        mock_event_emitter: AsyncMock,
        make_content,
    ) -> None:
        config = HealthClaimExtractionConfig(
            prohibited_patterns=(
                ClaimPattern(pattern="test", category="treatment", language="en"),
            ),
            max_claims_per_content=2,
        )
        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=mock_pattern_matcher,
            llm_classifier=mock_llm_classifier,
            event_emitter=mock_event_emitter,
            config=config,
        )
        content = make_content("lots of claims")
        mock_competitor_repo.get_pending_extraction.return_value = [content]
        mock_pattern_matcher.find_matches.return_value = [
            PatternMatch(matched_text=f"claim {i}", pattern="test", category="treatment",
                        language="en", start_pos=i*10, end_pos=i*10+5, surrounding_context=f"claim {i}")
            for i in range(5)
        ]
        # LLM returns more claims
        mock_llm_classifier.classify_claims.return_value = [
            ClaimExtractionResult(
                claim_text=f"claim {i}", surrounding_context="",
                claim_category="treatment", confidence_score=80,
                language_detected="en", extraction_method="hybrid",
            )
            for i in range(5)
        ]

        await engine.execute()
        # save_claims should receive at most max_claims_per_content
        save_args = mock_claim_repo.save_claims.call_args
        assert len(save_args[0][1]) <= 2

    @pytest.mark.asyncio
    async def test_events_emitted_for_high_confidence(
        self,
        engine: HealthClaimExtractionEngine,
        mock_competitor_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_llm_classifier: AsyncMock,
        mock_claim_repo: AsyncMock,
        mock_event_emitter: AsyncMock,
        make_content,
    ) -> None:
        content = make_content("boosts immunity")
        mock_competitor_repo.get_pending_extraction.return_value = [content]
        mock_pattern_matcher.find_matches.return_value = [
            PatternMatch(
                matched_text="boosts immunity", pattern="boosts immunity",
                category="enhancement", language="en",
                start_pos=0, end_pos=15, surrounding_context="boosts immunity",
            ),
        ]
        mock_llm_classifier.classify_claims.return_value = [
            ClaimExtractionResult(
                claim_text="boosts immunity", surrounding_context="",
                claim_category="enhancement", confidence_score=90,
                language_detected="en", extraction_method="hybrid",
            ),
        ]
        mock_claim_repo.save_claims.return_value = 1

        await engine.execute()
        # High confidence (90 >= 70) should trigger event emission
        mock_event_emitter.emit.assert_awaited()

    @pytest.mark.asyncio
    async def test_confidence_threshold_passed_to_save_claims(
        self,
        engine: HealthClaimExtractionEngine,
        mock_competitor_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_llm_classifier: AsyncMock,
        mock_claim_repo: AsyncMock,
        make_content,
    ) -> None:
        """Engine passes confidence_threshold to repository for review_status."""
        content = make_content("boosts immunity")
        mock_competitor_repo.get_pending_extraction.return_value = [content]
        mock_pattern_matcher.find_matches.return_value = [
            PatternMatch(
                matched_text="boosts immunity", pattern="boosts immunity",
                category="enhancement", language="en",
                start_pos=0, end_pos=15, surrounding_context="boosts immunity",
            ),
        ]
        mock_llm_classifier.classify_claims.return_value = [
            ClaimExtractionResult(
                claim_text="boosts immunity", surrounding_context="",
                claim_category="enhancement", confidence_score=90,
                language_detected="en", extraction_method="hybrid",
            ),
        ]
        mock_claim_repo.save_claims.return_value = 1

        await engine.execute()
        save_call = mock_claim_repo.save_claims.call_args
        # Third positional arg is confidence_threshold
        assert save_call[0][2] == 70  # config default

    @pytest.mark.asyncio
    async def test_high_confidence_counted_correctly(
        self,
        engine: HealthClaimExtractionEngine,
        mock_competitor_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_llm_classifier: AsyncMock,
        mock_claim_repo: AsyncMock,
        make_content,
    ) -> None:
        """High-confidence claim increments high_confidence_claims counter."""
        content = make_content("boosts immunity")
        mock_competitor_repo.get_pending_extraction.return_value = [content]
        mock_pattern_matcher.find_matches.return_value = [
            PatternMatch(
                matched_text="boosts immunity", pattern="boosts immunity",
                category="enhancement", language="en",
                start_pos=0, end_pos=15, surrounding_context="boosts immunity",
            ),
        ]
        mock_llm_classifier.classify_claims.return_value = [
            ClaimExtractionResult(
                claim_text="boosts immunity", surrounding_context="",
                claim_category="enhancement", confidence_score=90,
                language_detected="en", extraction_method="hybrid",
            ),
        ]
        mock_claim_repo.save_claims.return_value = 1

        result = await engine.execute()
        assert result.high_confidence_claims == 1
        assert result.manual_review_claims == 0

    @pytest.mark.asyncio
    async def test_low_confidence_counted_as_manual_review(
        self,
        engine: HealthClaimExtractionEngine,
        mock_competitor_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_llm_classifier: AsyncMock,
        mock_claim_repo: AsyncMock,
        make_content,
    ) -> None:
        """Low-confidence claim increments manual_review_claims counter."""
        content = make_content("maybe boosts immunity")
        mock_competitor_repo.get_pending_extraction.return_value = [content]
        mock_pattern_matcher.find_matches.return_value = [
            PatternMatch(
                matched_text="boosts immunity", pattern="boosts immunity",
                category="enhancement", language="en",
                start_pos=6, end_pos=21, surrounding_context="maybe boosts immunity",
            ),
        ]
        mock_llm_classifier.classify_claims.return_value = [
            ClaimExtractionResult(
                claim_text="boosts immunity",
                surrounding_context="maybe boosts immunity",
                claim_category="enhancement",
                confidence_score=55,
                language_detected="en",
                extraction_method="hybrid",
            ),
        ]
        mock_claim_repo.save_claims.return_value = 1

        result = await engine.execute()
        assert result.manual_review_claims == 1
        assert result.high_confidence_claims == 0

    @pytest.mark.asyncio
    async def test_health_claim_extracted_event_emitted(
        self,
        engine: HealthClaimExtractionEngine,
        mock_competitor_repo: AsyncMock,
        mock_pattern_matcher: MagicMock,
        mock_llm_classifier: AsyncMock,
        mock_claim_repo: AsyncMock,
        mock_event_emitter: AsyncMock,
        make_content,
    ) -> None:
        """HEALTH_CLAIM_EXTRACTED event emitted after saving claims."""
        from core.regulatory.events import RegulatoryEventType

        content = make_content("boosts immunity")
        mock_competitor_repo.get_pending_extraction.return_value = [content]
        mock_pattern_matcher.find_matches.return_value = [
            PatternMatch(
                matched_text="boosts immunity", pattern="boosts immunity",
                category="enhancement", language="en",
                start_pos=0, end_pos=15, surrounding_context="boosts immunity",
            ),
        ]
        mock_llm_classifier.classify_claims.return_value = [
            ClaimExtractionResult(
                claim_text="boosts immunity", surrounding_context="",
                claim_category="enhancement", confidence_score=90,
                language_detected="en", extraction_method="hybrid",
            ),
        ]
        mock_claim_repo.save_claims.return_value = 1

        await engine.execute()
        # Should have 2 events: HEALTH_CLAIM_EXTRACTED + HIGH_CONFIDENCE_CLAIM_DETECTED
        assert mock_event_emitter.emit.await_count == 2
        event_types = [
            call[0][0].event_type
            for call in mock_event_emitter.emit.call_args_list
        ]
        assert RegulatoryEventType.HEALTH_CLAIM_EXTRACTED in event_types
        assert RegulatoryEventType.HIGH_CONFIDENCE_CLAIM_DETECTED in event_types
