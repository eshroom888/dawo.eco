"""Tests for batch validation functionality.

Tests cover:
- Concurrent batch processing
- Partial failure handling
- Statistics tracking
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from teams.dawo.research import TransformedResearch, ResearchSource, ComplianceStatus
from teams.dawo.validators.eu_compliance import (
    ContentComplianceCheck,
    OverallStatus,
)
from teams.dawo.validators.research_compliance import (
    ResearchComplianceValidator,
    ValidationStats,
)


class TestBatchValidation:
    """Tests for validate_batch method."""

    @pytest.mark.asyncio
    async def test_batch_validation_processes_all_items(
        self,
        mock_eu_compliance_checker: AsyncMock,
        research_batch: list[TransformedResearch],
    ):
        """Test that batch validation processes all items."""
        # Arrange
        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        results = await validator.validate_batch(research_batch)

        # Assert
        assert len(results) == len(research_batch)
        assert mock_eu_compliance_checker.check_content.call_count == len(research_batch)

    @pytest.mark.asyncio
    async def test_batch_validation_returns_mixed_statuses(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test that batch returns items with different compliance statuses."""
        # Arrange
        items = [
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title=f"Item {i}",
                content=f"Content for item {i}",
                url=f"https://reddit.com/r/test/{i}",
                tags=[],
                source_metadata={},
                score=5.0,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(3)
        ]

        # Configure mock to return different statuses
        call_count = [0]

        async def varying_response(*args, **kwargs):
            count = call_count[0]
            call_count[0] += 1
            if count == 0:
                return ContentComplianceCheck(
                    overall_status=OverallStatus.COMPLIANT,
                    flagged_phrases=[],
                )
            elif count == 1:
                return ContentComplianceCheck(
                    overall_status=OverallStatus.WARNING,
                    flagged_phrases=[],
                )
            else:
                return ContentComplianceCheck(
                    overall_status=OverallStatus.REJECTED,
                    flagged_phrases=[],
                )

        mock_eu_compliance_checker.check_content = AsyncMock(side_effect=varying_response)

        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        results = await validator.validate_batch(items)

        # Assert
        statuses = [r.compliance_status for r in results]
        assert ComplianceStatus.COMPLIANT in statuses
        assert ComplianceStatus.WARNING in statuses
        assert ComplianceStatus.REJECTED in statuses


class TestPartialFailureHandling:
    """Tests for handling partial failures in batch validation."""

    @pytest.mark.asyncio
    async def test_batch_continues_on_individual_failure(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test that batch continues processing even if one item fails."""
        # Arrange
        items = [
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title=f"Item {i}",
                content=f"Content {i}",
                url=f"https://reddit.com/r/test/{i}",
                tags=[],
                source_metadata={},
                score=5.0,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(3)
        ]

        # Configure mock to fail on second item
        call_count = [0]

        async def failing_response(*args, **kwargs):
            count = call_count[0]
            call_count[0] += 1
            if count == 1:
                raise ValueError("Simulated failure")
            return ContentComplianceCheck(
                overall_status=OverallStatus.COMPLIANT,
                flagged_phrases=[],
            )

        mock_eu_compliance_checker.check_content = AsyncMock(side_effect=failing_response)

        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        results = await validator.validate_batch(items)

        # Assert
        # Should have 2 results (first and third succeeded, second failed)
        assert len(results) == 2
        assert mock_eu_compliance_checker.check_content.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_returns_partial_results_on_failures(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test that batch returns successful results even with failures."""
        # Arrange
        items = [
            TransformedResearch(
                source=ResearchSource.PUBMED,
                title="Good item",
                content="Valid content",
                url="https://pubmed.ncbi.nlm.nih.gov/123/",
                tags=[],
                source_metadata={"pmid": "123"},
                score=8.0,
                created_at=datetime.now(timezone.utc),
            ),
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title="Bad item",
                content="Will fail",
                url="https://reddit.com/r/test/fail",
                tags=[],
                source_metadata={},
                score=2.0,
                created_at=datetime.now(timezone.utc),
            ),
        ]

        # First call succeeds, second raises exception
        mock_eu_compliance_checker.check_content = AsyncMock(
            side_effect=[
                ContentComplianceCheck(
                    overall_status=OverallStatus.COMPLIANT,
                    flagged_phrases=[],
                ),
                ValueError("Validation error"),
            ]
        )

        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        results = await validator.validate_batch(items)

        # Assert
        assert len(results) == 1
        assert results[0].compliance_status == ComplianceStatus.COMPLIANT


class TestValidationStatistics:
    """Tests for validation statistics tracking."""

    @pytest.mark.asyncio
    async def test_batch_returns_correct_statistics(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test that batch validation tracks correct statistics."""
        # Arrange
        items = [
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title=f"Item {i}",
                content=f"Content {i}",
                url=f"https://reddit.com/r/test/{i}",
                tags=[],
                source_metadata={},
                score=5.0,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]

        # Configure varying responses
        call_count = [0]

        async def varying_response(*args, **kwargs):
            count = call_count[0]
            call_count[0] += 1
            if count < 2:
                return ContentComplianceCheck(overall_status=OverallStatus.COMPLIANT, flagged_phrases=[])
            elif count < 4:
                return ContentComplianceCheck(overall_status=OverallStatus.WARNING, flagged_phrases=[])
            else:
                return ContentComplianceCheck(overall_status=OverallStatus.REJECTED, flagged_phrases=[])

        mock_eu_compliance_checker.check_content = AsyncMock(side_effect=varying_response)

        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        results, stats = await validator.validate_batch_with_stats(items)

        # Assert
        assert stats.total == 5
        assert stats.validated == 5
        assert stats.compliant == 2
        assert stats.warned == 2
        assert stats.rejected == 1
        assert stats.failed == 0

    @pytest.mark.asyncio
    async def test_statistics_track_failures(
        self,
        mock_eu_compliance_checker: AsyncMock,
    ):
        """Test that statistics properly track failed validations."""
        # Arrange
        items = [
            TransformedResearch(
                source=ResearchSource.REDDIT,
                title=f"Item {i}",
                content=f"Content {i}",
                url=f"https://reddit.com/r/test/{i}",
                tags=[],
                source_metadata={},
                score=5.0,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(3)
        ]

        # Second item fails
        mock_eu_compliance_checker.check_content = AsyncMock(
            side_effect=[
                ContentComplianceCheck(overall_status=OverallStatus.COMPLIANT, flagged_phrases=[]),
                ValueError("Failure"),
                ContentComplianceCheck(overall_status=OverallStatus.COMPLIANT, flagged_phrases=[]),
            ]
        )

        validator = ResearchComplianceValidator(
            compliance_checker=mock_eu_compliance_checker
        )

        # Act
        results, stats = await validator.validate_batch_with_stats(items)

        # Assert
        assert stats.total == 3
        assert stats.validated == 2
        assert stats.failed == 1
