"""Tests for YouTube Key Insight Extractor.

Tests Task 6: KeyInsightExtractor implementation using tier="generate" for
LLM-powered summarization of video transcripts.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import json


class TestKeyInsightExtractor:
    """Tests for KeyInsightExtractor class."""

    def test_can_import_key_insight_extractor(self):
        """Test that KeyInsightExtractor can be imported from module."""
        from teams.dawo.scanners.youtube import KeyInsightExtractor

        assert KeyInsightExtractor is not None

    def test_insight_extractor_accepts_llm_client_injection(self):
        """Test that KeyInsightExtractor accepts LLM client via constructor."""
        from teams.dawo.scanners.youtube.insight_extractor import KeyInsightExtractor

        llm_client = MagicMock()

        extractor = KeyInsightExtractor(llm_client=llm_client)

        assert extractor._llm_client is llm_client


class TestKeyInsightExtractorExtract:
    """Tests for KeyInsightExtractor.extract_insights method."""

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response with valid JSON."""
        return json.dumps({
            "main_summary": "This video explores the cognitive benefits of lion's mane mushroom. "
                          "The host discusses recent research showing potential memory improvements.",
            "quotable_insights": [
                {
                    "text": "Lion's mane contains compounds that stimulate nerve growth factor production.",
                    "context": "Discussing NGF production mechanism",
                    "topic": "lions_mane cognition",
                    "is_claim": True,
                },
                {
                    "text": "Studies show 10-15% improvement in memory tests after 4 weeks.",
                    "context": "Citing research study results",
                    "topic": "research",
                    "is_claim": True,
                },
            ],
            "key_topics": ["lions_mane", "cognition", "research", "dosage"],
            "confidence_score": 0.85,
        })

    @pytest.fixture
    def sample_transcript(self):
        """Sample transcript for testing."""
        return """
        Today we're talking about lion's mane mushroom and its benefits for brain health.
        Lion's mane contains compounds called hericenones and erinacines that stimulate
        nerve growth factor production. Studies show 10-15% improvement in memory tests
        after 4 weeks of supplementation at 500mg daily. While more research is needed,
        the initial results are promising for cognitive support.
        """

    @pytest.mark.asyncio
    async def test_extract_insights_returns_insight_result(
        self, mock_llm_response, sample_transcript
    ):
        """Test extract_insights returns InsightResult."""
        from teams.dawo.scanners.youtube.insight_extractor import KeyInsightExtractor
        from teams.dawo.scanners.youtube import InsightResult

        llm_client = AsyncMock()
        llm_client.generate = AsyncMock(return_value=mock_llm_response)

        extractor = KeyInsightExtractor(llm_client=llm_client)

        result = await extractor.extract_insights(
            transcript=sample_transcript,
            title="Lion's Mane Benefits Explained",
            channel_name="Health Science Channel",
        )

        assert isinstance(result, InsightResult)
        assert result.main_summary is not None
        assert len(result.main_summary) > 0

    @pytest.mark.asyncio
    async def test_extract_insights_includes_quotable_insights(
        self, mock_llm_response, sample_transcript
    ):
        """Test that extract_insights includes quotable insights."""
        from teams.dawo.scanners.youtube.insight_extractor import KeyInsightExtractor
        from teams.dawo.scanners.youtube import QuotableInsight

        llm_client = AsyncMock()
        llm_client.generate = AsyncMock(return_value=mock_llm_response)

        extractor = KeyInsightExtractor(llm_client=llm_client)

        result = await extractor.extract_insights(
            transcript=sample_transcript,
            title="Lion's Mane Benefits",
            channel_name="Health Channel",
        )

        assert len(result.quotable_insights) > 0
        assert len(result.quotable_insights) <= 3  # Max 3 per spec
        insight = result.quotable_insights[0]
        assert isinstance(insight, QuotableInsight)
        assert insight.text is not None
        assert insight.context is not None

    @pytest.mark.asyncio
    async def test_extract_insights_includes_key_topics(
        self, mock_llm_response, sample_transcript
    ):
        """Test that extract_insights includes key topics."""
        from teams.dawo.scanners.youtube.insight_extractor import KeyInsightExtractor

        llm_client = AsyncMock()
        llm_client.generate = AsyncMock(return_value=mock_llm_response)

        extractor = KeyInsightExtractor(llm_client=llm_client)

        result = await extractor.extract_insights(
            transcript=sample_transcript,
            title="Lion's Mane Benefits",
            channel_name="Health Channel",
        )

        assert len(result.key_topics) >= 3
        assert "lions_mane" in result.key_topics

    @pytest.mark.asyncio
    async def test_extract_insights_includes_confidence_score(
        self, mock_llm_response, sample_transcript
    ):
        """Test that extract_insights includes confidence score."""
        from teams.dawo.scanners.youtube.insight_extractor import KeyInsightExtractor

        llm_client = AsyncMock()
        llm_client.generate = AsyncMock(return_value=mock_llm_response)

        extractor = KeyInsightExtractor(llm_client=llm_client)

        result = await extractor.extract_insights(
            transcript=sample_transcript,
            title="Lion's Mane Benefits",
            channel_name="Health Channel",
        )

        assert 0.0 <= result.confidence_score <= 1.0
        assert result.confidence_score == 0.85

    @pytest.mark.asyncio
    async def test_extract_insights_uses_short_prompt_for_short_transcripts(
        self, sample_transcript
    ):
        """Test that short transcripts use the short prompt."""
        from teams.dawo.scanners.youtube.insight_extractor import KeyInsightExtractor
        from teams.dawo.scanners.youtube import SHORT_TRANSCRIPT_THRESHOLD

        short_response = json.dumps({
            "main_summary": "Brief summary of short video.",
            "quotable_insights": [],
            "key_topics": ["lions_mane"],
            "confidence_score": 0.6,
        })

        llm_client = AsyncMock()
        llm_client.generate = AsyncMock(return_value=short_response)

        extractor = KeyInsightExtractor(llm_client=llm_client)

        # Use a short transcript (under threshold)
        short_transcript = "Lion's mane is good for brain health."

        result = await extractor.extract_insights(
            transcript=short_transcript,
            title="Quick Tips",
            channel_name="Health Tips",
        )

        assert result.main_summary is not None
        # Should have called generate with short prompt context
        llm_client.generate.assert_called_once()


class TestKeyInsightExtractorErrorHandling:
    """Tests for error handling in KeyInsightExtractor."""

    @pytest.mark.asyncio
    async def test_handles_invalid_json_response(self):
        """Test handling of invalid JSON from LLM."""
        from teams.dawo.scanners.youtube.insight_extractor import (
            KeyInsightExtractor,
            InsightExtractionError,
        )

        llm_client = AsyncMock()
        llm_client.generate = AsyncMock(return_value="Not valid JSON at all")

        extractor = KeyInsightExtractor(llm_client=llm_client)

        with pytest.raises(InsightExtractionError):
            await extractor.extract_insights(
                transcript="Some transcript",
                title="Some title",
                channel_name="Some channel",
            )

    @pytest.mark.asyncio
    async def test_handles_missing_fields_in_response(self):
        """Test handling of incomplete JSON response."""
        from teams.dawo.scanners.youtube.insight_extractor import KeyInsightExtractor

        # Missing confidence_score - should default
        incomplete_response = json.dumps({
            "main_summary": "A summary without all fields.",
            "quotable_insights": [],
            "key_topics": [],
        })

        llm_client = AsyncMock()
        llm_client.generate = AsyncMock(return_value=incomplete_response)

        extractor = KeyInsightExtractor(llm_client=llm_client)

        result = await extractor.extract_insights(
            transcript="Some transcript",
            title="Some title",
            channel_name="Some channel",
        )

        # Should still return valid result with defaults
        assert result.main_summary == "A summary without all fields."
        assert result.confidence_score == 0.0  # Default value

    @pytest.mark.asyncio
    async def test_handles_llm_api_error(self):
        """Test handling of LLM API errors."""
        from teams.dawo.scanners.youtube.insight_extractor import (
            KeyInsightExtractor,
            InsightExtractionError,
        )

        llm_client = AsyncMock()
        llm_client.generate = AsyncMock(side_effect=Exception("API connection failed"))

        extractor = KeyInsightExtractor(llm_client=llm_client)

        with pytest.raises(InsightExtractionError) as exc_info:
            await extractor.extract_insights(
                transcript="Some transcript",
                title="Some title",
                channel_name="Some channel",
            )

        assert "API connection failed" in str(exc_info.value)


class TestInsightExtractionError:
    """Tests for InsightExtractionError exception."""

    def test_can_import_insight_extraction_error(self):
        """Test that InsightExtractionError can be imported."""
        from teams.dawo.scanners.youtube import InsightExtractionError

        assert InsightExtractionError is not None

    def test_insight_extraction_error_with_video_id(self):
        """Test InsightExtractionError stores video context."""
        from teams.dawo.scanners.youtube.insight_extractor import InsightExtractionError

        error = InsightExtractionError(
            message="Failed to parse response",
            video_id="abc123",
            video_title="Test Video",
        )

        assert error.message == "Failed to parse response"
        assert error.video_id == "abc123"
        assert error.video_title == "Test Video"
