"""Integration tests for health claim extraction pipeline.

Story 6-6, Task 12: End-to-end integration tests.

Tests the full flow from config → pattern matcher → LLM classifier →
engine → repository → event emission, verifying all components
work together correctly.
"""

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.regulatory.events import RegulatoryEventType
from teams.dawo.scanners.claim_extraction.config import (
    ClaimPattern,
    HealthClaimExtractionConfig,
)
from teams.dawo.scanners.claim_extraction.engine import HealthClaimExtractionEngine
from teams.dawo.scanners.claim_extraction.llm_classifier import ClaimLLMClassifier
from teams.dawo.scanners.claim_extraction.pattern_matcher import ClaimPatternMatcher
from teams.dawo.scanners.claim_extraction.schemas import (
    ClaimExtractionResult,
    ExtractionBatchResult,
)


@pytest.fixture
def full_config() -> HealthClaimExtractionConfig:
    """Realistic config with EN + NO patterns."""
    return HealthClaimExtractionConfig(
        prohibited_patterns=(
            ClaimPattern(pattern="cures cancer", category="treatment", language="en"),
            ClaimPattern(pattern="prevents diabetes", category="prevention", language="en"),
            ClaimPattern(pattern="kurerer kreft", category="treatment", language="no"),
        ),
        borderline_patterns=(
            ClaimPattern(pattern="boosts immunity", category="enhancement", language="en"),
            ClaimPattern(pattern="supports digestion", category="general_wellness", language="en"),
            ClaimPattern(pattern="styrker immunforsvaret", category="enhancement", language="no"),
        ),
        permitted_patterns=(
            ClaimPattern(pattern="contains vitamin", category="general_wellness", language="en"),
        ),
        batch_size=20,
        confidence_threshold=70,
        max_claims_per_content=10,
        use_llm=True,
        eu_article_mapping={
            "treatment": "prohibited",
            "prevention": "prohibited",
            "enhancement": "13.1",
            "general_wellness": "13.1",
        },
    )


@pytest.fixture
def real_pattern_matcher(full_config) -> ClaimPatternMatcher:
    """Real pattern matcher with full config patterns."""
    return ClaimPatternMatcher(config=full_config)


@pytest.fixture
def mock_competitor_repo():
    repo = AsyncMock()
    repo.get_pending_extraction = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_claim_repo():
    repo = AsyncMock()
    repo.save_claims = AsyncMock(return_value=0)
    repo.update_extraction_status = AsyncMock()
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_event_emitter():
    emitter = AsyncMock()
    emitter.emit = AsyncMock()
    return emitter


@pytest.fixture
def make_content():
    """Factory for mock CompetitorContent objects."""
    def _make(content_text="Some content", content_id=None):
        content = MagicMock()
        content.id = content_id or uuid4()
        content.content_text = content_text
        content.competitor_name = "TestCompetitor"
        content.source_type = "website"
        content.extraction_status = "pending"
        return content
    return _make


class TestFullPipelineWithRealPatternMatcher:
    """12.1: Full flow pattern matcher → engine → claims saved."""

    @pytest.mark.asyncio
    async def test_english_prohibited_claim_detected(
        self,
        full_config,
        real_pattern_matcher,
        mock_competitor_repo,
        mock_claim_repo,
        mock_event_emitter,
        make_content,
    ):
        """English prohibited pattern → regex match → LLM confirms → saved."""
        content = make_content(
            "Our mushroom extract cures cancer and prevents diabetes."
        )
        mock_competitor_repo.get_pending_extraction.return_value = [content]

        # Mock LLM to confirm the regex findings with high confidence
        mock_llm = AsyncMock()
        mock_llm.classify_claims = AsyncMock(return_value=[
            ClaimExtractionResult(
                claim_text="cures cancer",
                surrounding_context="extract cures cancer and",
                claim_category="treatment",
                confidence_score=95,
                language_detected="en",
                extraction_method="hybrid",
                eu_article_reference="prohibited",
            ),
            ClaimExtractionResult(
                claim_text="prevents diabetes",
                surrounding_context="cancer and prevents diabetes",
                claim_category="prevention",
                confidence_score=92,
                language_detected="en",
                extraction_method="hybrid",
                eu_article_reference="prohibited",
            ),
        ])
        mock_claim_repo.save_claims.return_value = 2

        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=real_pattern_matcher,
            llm_classifier=mock_llm,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        result = await engine.execute()

        assert isinstance(result, ExtractionBatchResult)
        assert result.total_processed == 1
        assert result.total_claims_extracted == 2
        assert result.items_with_claims == 1

        # Real pattern matcher should have found 2 matches
        mock_llm.classify_claims.assert_awaited_once()
        call_args = mock_llm.classify_claims.call_args
        matches = call_args[0][1]  # second positional arg
        assert len(matches) == 2

        # 1 HEALTH_CLAIM_EXTRACTED + 2 HIGH_CONFIDENCE_CLAIM_DETECTED
        assert mock_event_emitter.emit.await_count == 3
        assert result.high_confidence_claims == 2

    @pytest.mark.asyncio
    async def test_norwegian_claim_detected(
        self,
        full_config,
        real_pattern_matcher,
        mock_competitor_repo,
        mock_claim_repo,
        mock_event_emitter,
        make_content,
    ):
        """Norwegian pattern → regex match → classified correctly."""
        content = make_content(
            "Produktet styrker immunforsvaret og kurerer kreft."
        )
        mock_competitor_repo.get_pending_extraction.return_value = [content]

        mock_llm = AsyncMock()
        mock_llm.classify_claims = AsyncMock(return_value=[
            ClaimExtractionResult(
                claim_text="styrker immunforsvaret",
                surrounding_context="Produktet styrker immunforsvaret og",
                claim_category="enhancement",
                confidence_score=88,
                language_detected="no",
                extraction_method="hybrid",
            ),
            ClaimExtractionResult(
                claim_text="kurerer kreft",
                surrounding_context="og kurerer kreft",
                claim_category="treatment",
                confidence_score=95,
                language_detected="no",
                extraction_method="hybrid",
            ),
        ])
        mock_claim_repo.save_claims.return_value = 2

        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=real_pattern_matcher,
            llm_classifier=mock_llm,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        result = await engine.execute()

        assert result.total_claims_extracted == 2
        # Verify language detection passed to LLM
        call_args = mock_llm.classify_claims.call_args
        language_hint = call_args[0][2]  # third positional arg
        assert language_hint == "no"


class TestRegexOnlyPipeline:
    """12.2: Regex-only mode (no LLM) with real pattern matcher."""

    @pytest.mark.asyncio
    async def test_regex_only_extracts_claims(
        self,
        full_config,
        real_pattern_matcher,
        mock_competitor_repo,
        mock_claim_repo,
        mock_event_emitter,
        make_content,
    ):
        """Regex-only mode → claims with confidence 60, extraction_method='regex'."""
        config_no_llm = HealthClaimExtractionConfig(
            prohibited_patterns=full_config.prohibited_patterns,
            borderline_patterns=full_config.borderline_patterns,
            use_llm=False,
            eu_article_mapping=full_config.eu_article_mapping,
        )
        content = make_content("Our product boosts immunity naturally.")
        mock_competitor_repo.get_pending_extraction.return_value = [content]
        mock_claim_repo.save_claims.return_value = 1

        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=real_pattern_matcher,
            llm_classifier=None,
            event_emitter=mock_event_emitter,
            config=config_no_llm,
        )

        result = await engine.execute()

        assert result.total_claims_extracted == 1
        # Check the claims passed to save_claims
        save_args = mock_claim_repo.save_claims.call_args
        claims = save_args[0][1]
        assert len(claims) == 1
        assert claims[0].extraction_method == "regex"
        assert claims[0].confidence_score == 60
        assert claims[0].eu_article_reference == "13.1"  # enhancement mapping


class TestNoClaimsFlow:
    """12.3: Content without health claims → no_claims status."""

    @pytest.mark.asyncio
    async def test_neutral_content_no_claims(
        self,
        full_config,
        real_pattern_matcher,
        mock_competitor_repo,
        mock_claim_repo,
        mock_event_emitter,
        make_content,
    ):
        """Neutral content → pattern matcher finds nothing → no_claims."""
        content = make_content("Delicious mushroom soup recipe with garlic.")
        mock_competitor_repo.get_pending_extraction.return_value = [content]

        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=real_pattern_matcher,
            llm_classifier=None,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        result = await engine.execute()

        assert result.total_processed == 1
        assert result.items_no_claims == 1
        assert result.total_claims_extracted == 0
        mock_claim_repo.update_extraction_status.assert_awaited_with(
            content.id, "no_claims"
        )
        mock_event_emitter.emit.assert_not_called()


class TestEventEmissionIntegration:
    """12.4: Events emitted correctly for different confidence levels."""

    @pytest.mark.asyncio
    async def test_high_confidence_treatment_emits_high_severity(
        self,
        full_config,
        real_pattern_matcher,
        mock_competitor_repo,
        mock_claim_repo,
        mock_event_emitter,
        make_content,
    ):
        """Treatment claim with high confidence → high severity event."""
        content = make_content("This product cures cancer guaranteed.")
        mock_competitor_repo.get_pending_extraction.return_value = [content]

        mock_llm = AsyncMock()
        mock_llm.classify_claims = AsyncMock(return_value=[
            ClaimExtractionResult(
                claim_text="cures cancer",
                surrounding_context="product cures cancer guaranteed",
                claim_category="treatment",
                confidence_score=95,
                language_detected="en",
                extraction_method="hybrid",
            ),
        ])
        mock_claim_repo.save_claims.return_value = 1

        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=real_pattern_matcher,
            llm_classifier=mock_llm,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        await engine.execute()

        # 1 HEALTH_CLAIM_EXTRACTED + 1 HIGH_CONFIDENCE_CLAIM_DETECTED
        assert mock_event_emitter.emit.await_count == 2
        # Last event is the HIGH_CONFIDENCE one
        event = mock_event_emitter.emit.call_args[0][0]
        assert event.event_type == RegulatoryEventType.HIGH_CONFIDENCE_CLAIM_DETECTED
        assert event.severity == "high"  # treatment → high
        assert event.data["claim_category"] == "treatment"
        assert event.data["confidence_score"] == 95

    @pytest.mark.asyncio
    async def test_enhancement_claim_emits_medium_severity(
        self,
        full_config,
        real_pattern_matcher,
        mock_competitor_repo,
        mock_claim_repo,
        mock_event_emitter,
        make_content,
    ):
        """Enhancement claim → medium severity event."""
        content = make_content("This supplement boosts immunity.")
        mock_competitor_repo.get_pending_extraction.return_value = [content]

        mock_llm = AsyncMock()
        mock_llm.classify_claims = AsyncMock(return_value=[
            ClaimExtractionResult(
                claim_text="boosts immunity",
                surrounding_context="supplement boosts immunity",
                claim_category="enhancement",
                confidence_score=85,
                language_detected="en",
                extraction_method="hybrid",
            ),
        ])
        mock_claim_repo.save_claims.return_value = 1

        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=real_pattern_matcher,
            llm_classifier=mock_llm,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        await engine.execute()

        event = mock_event_emitter.emit.call_args[0][0]
        assert event.severity == "medium"  # enhancement → medium


class TestMultiItemBatchProcessing:
    """12.5: Batch with mixed content types processes correctly."""

    @pytest.mark.asyncio
    async def test_batch_mixed_content(
        self,
        full_config,
        real_pattern_matcher,
        mock_competitor_repo,
        mock_claim_repo,
        mock_event_emitter,
        make_content,
    ):
        """Batch: claim content + neutral content + error content."""
        claim_content = make_content("Our product boosts immunity daily.")
        neutral_content = make_content("Beautiful mushroom photography.")
        error_content = make_content("This product cures cancer for sure.")

        mock_competitor_repo.get_pending_extraction.return_value = [
            claim_content, neutral_content, error_content,
        ]

        mock_llm = AsyncMock()

        # First call returns claims, second not reached (no matches),
        # third raises error
        mock_llm.classify_claims = AsyncMock(side_effect=[
            [
                ClaimExtractionResult(
                    claim_text="boosts immunity",
                    surrounding_context="product boosts immunity daily",
                    claim_category="enhancement",
                    confidence_score=85,
                    language_detected="en",
                    extraction_method="hybrid",
                ),
            ],
            RuntimeError("LLM API timeout"),
        ])

        # save_claims succeeds for first, fails for third (error in classify)
        mock_claim_repo.save_claims.return_value = 1

        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=real_pattern_matcher,
            llm_classifier=mock_llm,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        result = await engine.execute()

        assert result.total_processed == 3
        assert result.items_with_claims == 1   # claim_content
        assert result.items_no_claims == 1     # neutral_content
        assert result.items_error == 1         # error_content
        mock_claim_repo.commit.assert_awaited_once()


class TestMaxClaimsPerContentIntegration:
    """12.6: Max claims cap works end-to-end."""

    @pytest.mark.asyncio
    async def test_claims_capped_at_max(
        self,
        real_pattern_matcher,
        mock_competitor_repo,
        mock_claim_repo,
        mock_event_emitter,
        make_content,
    ):
        """Config max_claims_per_content=2 → only top 2 saved."""
        config = HealthClaimExtractionConfig(
            prohibited_patterns=(
                ClaimPattern(pattern="cures cancer", category="treatment", language="en"),
                ClaimPattern(pattern="prevents diabetes", category="prevention", language="en"),
            ),
            borderline_patterns=(
                ClaimPattern(pattern="boosts immunity", category="enhancement", language="en"),
            ),
            max_claims_per_content=2,
            use_llm=True,
        )
        matcher = ClaimPatternMatcher(config=config)

        content = make_content(
            "This product cures cancer, prevents diabetes, and boosts immunity."
        )
        mock_competitor_repo.get_pending_extraction.return_value = [content]

        mock_llm = AsyncMock()
        mock_llm.classify_claims = AsyncMock(return_value=[
            ClaimExtractionResult(
                claim_text="cures cancer", surrounding_context="",
                claim_category="treatment", confidence_score=95,
                language_detected="en", extraction_method="hybrid",
            ),
            ClaimExtractionResult(
                claim_text="prevents diabetes", surrounding_context="",
                claim_category="prevention", confidence_score=90,
                language_detected="en", extraction_method="hybrid",
            ),
            ClaimExtractionResult(
                claim_text="boosts immunity", surrounding_context="",
                claim_category="enhancement", confidence_score=80,
                language_detected="en", extraction_method="hybrid",
            ),
        ])
        mock_claim_repo.save_claims.return_value = 2

        engine = HealthClaimExtractionEngine(
            competitor_repository=mock_competitor_repo,
            claim_repository=mock_claim_repo,
            pattern_matcher=matcher,
            llm_classifier=mock_llm,
            event_emitter=mock_event_emitter,
            config=config,
        )

        await engine.execute()

        # Only top 2 by confidence should be saved
        save_args = mock_claim_repo.save_claims.call_args
        saved_claims = save_args[0][1]
        assert len(saved_claims) == 2
        # Highest confidence first
        assert saved_claims[0].confidence_score >= saved_claims[1].confidence_score
