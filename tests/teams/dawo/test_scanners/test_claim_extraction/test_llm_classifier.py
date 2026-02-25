"""Tests for ClaimLLMClassifier.

Story 6-6, Task 6: LLM-based claim classification.
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.claim_extraction.config import (
    HealthClaimExtractionConfig,
    ClaimPattern,
)
from teams.dawo.scanners.claim_extraction.llm_classifier import ClaimLLMClassifier
from teams.dawo.scanners.claim_extraction.schemas import (
    ClaimExtractionResult,
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
        max_claims_per_content=10,
    )


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    client = AsyncMock()
    client.generate = AsyncMock(return_value="[]")
    return client


@pytest.fixture
def mock_retry() -> MagicMock:
    retry = MagicMock()
    # execute_with_retry just calls the function
    async def _execute(func, *args, **kwargs):
        from unittest.mock import AsyncMock as AM
        if callable(func):
            result = func(*args, **kwargs)
            if hasattr(result, "__await__"):
                return await result
            return result
        return func
    retry.execute_with_retry = AsyncMock(side_effect=_execute)
    return retry


@pytest.fixture
def classifier(
    mock_llm_client: AsyncMock,
    mock_retry: MagicMock,
    config: HealthClaimExtractionConfig,
) -> ClaimLLMClassifier:
    return ClaimLLMClassifier(
        llm_client=mock_llm_client,
        retry=mock_retry,
        config=config,
    )


@pytest.fixture
def sample_pre_filter_matches() -> list[PatternMatch]:
    return [
        PatternMatch(
            matched_text="boosts immunity",
            pattern="boosts immunity",
            category="enhancement",
            language="en",
            start_pos=10,
            end_pos=25,
            surrounding_context="extract boosts immunity and ener",
        ),
    ]


@pytest.fixture
def valid_llm_response() -> str:
    return json.dumps([
        {
            "claim_text": "boosts immunity",
            "category": "enhancement",
            "confidence": 85,
            "reasoning": "Enhancement claim about immune function",
            "language": "en",
        },
        {
            "claim_text": "treats brain fog",
            "category": "treatment",
            "confidence": 92,
            "reasoning": "Medical treatment claim - prohibited",
            "language": "en",
        },
    ])


class TestClaimLLMClassifier:
    """Tests for ClaimLLMClassifier."""

    @pytest.mark.asyncio
    async def test_valid_llm_response_parsed(
        self,
        classifier: ClaimLLMClassifier,
        mock_llm_client: AsyncMock,
        valid_llm_response: str,
        sample_pre_filter_matches: list[PatternMatch],
    ) -> None:
        mock_llm_client.generate.return_value = valid_llm_response
        results = await classifier.classify_claims(
            "Our extract boosts immunity and treats brain fog.",
            sample_pre_filter_matches,
            "en",
        )
        assert len(results) >= 1
        assert all(isinstance(r, ClaimExtractionResult) for r in results)

    @pytest.mark.asyncio
    async def test_malformed_json_returns_empty(
        self,
        classifier: ClaimLLMClassifier,
        mock_llm_client: AsyncMock,
    ) -> None:
        mock_llm_client.generate.return_value = "not valid json at all"
        results = await classifier.classify_claims("some content", [], "en")
        assert results == []

    @pytest.mark.asyncio
    async def test_llm_timeout_returns_empty(
        self,
        classifier: ClaimLLMClassifier,
        mock_llm_client: AsyncMock,
    ) -> None:
        mock_llm_client.generate.side_effect = TimeoutError("LLM timeout")
        results = await classifier.classify_claims("some content", [], "en")
        assert results == []

    @pytest.mark.asyncio
    async def test_merge_regex_confirmed_by_llm(
        self,
        classifier: ClaimLLMClassifier,
        mock_llm_client: AsyncMock,
        sample_pre_filter_matches: list[PatternMatch],
    ) -> None:
        llm_response = json.dumps([{
            "claim_text": "boosts immunity",
            "category": "enhancement",
            "confidence": 85,
            "reasoning": "Enhancement claim",
            "language": "en",
        }])
        mock_llm_client.generate.return_value = llm_response
        results = await classifier.classify_claims(
            "extract boosts immunity and energy",
            sample_pre_filter_matches,
            "en",
        )
        # Regex + LLM confirm = hybrid, confidence 90
        hybrid = [r for r in results if r.claim_text == "boosts immunity"]
        assert len(hybrid) == 1
        assert hybrid[0].confidence_score == 90
        assert hybrid[0].extraction_method == "hybrid"

    @pytest.mark.asyncio
    async def test_merge_regex_only(
        self,
        classifier: ClaimLLMClassifier,
        mock_llm_client: AsyncMock,
        sample_pre_filter_matches: list[PatternMatch],
    ) -> None:
        # LLM returns empty (missed the regex match)
        mock_llm_client.generate.return_value = "[]"
        results = await classifier.classify_claims(
            "extract boosts immunity",
            sample_pre_filter_matches,
            "en",
        )
        regex_only = [r for r in results if r.claim_text == "boosts immunity"]
        assert len(regex_only) == 1
        assert regex_only[0].confidence_score == 60
        assert regex_only[0].extraction_method == "regex"

    @pytest.mark.asyncio
    async def test_merge_llm_only(
        self,
        classifier: ClaimLLMClassifier,
        mock_llm_client: AsyncMock,
    ) -> None:
        llm_response = json.dumps([{
            "claim_text": "treats brain fog",
            "category": "treatment",
            "confidence": 92,
            "reasoning": "Treatment claim",
            "language": "en",
        }])
        mock_llm_client.generate.return_value = llm_response
        results = await classifier.classify_claims(
            "Our product treats brain fog.",
            [],  # no regex matches
            "en",
        )
        llm_only = [r for r in results if r.claim_text == "treats brain fog"]
        assert len(llm_only) == 1
        assert llm_only[0].confidence_score == 75
        assert llm_only[0].extraction_method == "llm"

    @pytest.mark.asyncio
    async def test_deduplication_overlapping_claims(
        self,
        classifier: ClaimLLMClassifier,
        mock_llm_client: AsyncMock,
    ) -> None:
        # Two regex matches, LLM confirms one with overlap
        regex_matches = [
            PatternMatch(
                matched_text="boosts immunity",
                pattern="boosts immunity",
                category="enhancement",
                language="en",
                start_pos=0, end_pos=15,
                surrounding_context="boosts immunity",
            ),
        ]
        llm_response = json.dumps([{
            "claim_text": "boosts immunity",
            "category": "enhancement",
            "confidence": 90,
            "reasoning": "Same claim",
            "language": "en",
        }])
        mock_llm_client.generate.return_value = llm_response
        results = await classifier.classify_claims(
            "boosts immunity",
            regex_matches,
            "en",
        )
        # Should deduplicate, keep higher confidence
        boost_claims = [r for r in results if "immunity" in r.claim_text]
        assert len(boost_claims) == 1

    @pytest.mark.asyncio
    async def test_prompt_includes_norwegian_context(
        self,
        classifier: ClaimLLMClassifier,
        mock_llm_client: AsyncMock,
    ) -> None:
        mock_llm_client.generate.return_value = "[]"
        await classifier.classify_claims("Styrker immunforsvaret", [], "no")
        call_args = mock_llm_client.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "Norwegian" in prompt or "norsk" in prompt.lower() or "no" in prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_mushroom_context(
        self,
        classifier: ClaimLLMClassifier,
        mock_llm_client: AsyncMock,
    ) -> None:
        mock_llm_client.generate.return_value = "[]"
        await classifier.classify_claims("mushroom extract", [], "en")
        call_args = mock_llm_client.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "mushroom" in prompt.lower()

    @pytest.mark.asyncio
    async def test_claims_capped_at_max(
        self,
        mock_llm_client: AsyncMock,
        mock_retry: MagicMock,
    ) -> None:
        config = HealthClaimExtractionConfig(
            prohibited_patterns=(
                ClaimPattern(pattern="test", category="treatment", language="en"),
            ),
            max_claims_per_content=2,
        )
        classifier = ClaimLLMClassifier(mock_llm_client, mock_retry, config)
        llm_response = json.dumps([
            {"claim_text": f"claim {i}", "category": "treatment", "confidence": 80, "reasoning": "r", "language": "en"}
            for i in range(5)
        ])
        mock_llm_client.generate.return_value = llm_response
        results = await classifier.classify_claims("text", [], "en")
        assert len(results) <= 2
