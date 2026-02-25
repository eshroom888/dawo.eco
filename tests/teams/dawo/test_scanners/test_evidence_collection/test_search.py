"""Tests for EvidenceRepository search/filter methods (Story 6-9, Task 1).

Tests search, get_by_id, get_summary_stats, get_distinct_competitors,
get_competitor_timeline, and log_download methods.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest

from core.regulatory.models import Evidence, EvidenceAuditLog
from teams.dawo.scanners.evidence_collection.repository import EvidenceRepository


@pytest.fixture
def evidence_repo(mock_session, mock_storage_service) -> EvidenceRepository:
    """EvidenceRepository with mocked session and storage."""
    return EvidenceRepository(
        session=mock_session, storage_service=mock_storage_service
    )


def _make_evidence(**overrides) -> MagicMock:
    """Create a mock Evidence with default values."""
    e = MagicMock(spec=Evidence)
    e.id = overrides.get("id", uuid4())
    e.competitor_name = overrides.get("competitor_name", "CompetitorA")
    e.violation_type = overrides.get("violation_type", "unauthorized_treatment_claim")
    e.severity = overrides.get("severity", "high")
    e.claim_text = overrides.get("claim_text", "treats brain fog")
    e.claim_category = overrides.get("claim_category", "treatment")
    e.source_type = overrides.get("source_type", "instagram_post")
    e.source_url = overrides.get("source_url", "https://instagram.com/p/ABC123/")
    e.captured_at = overrides.get("captured_at", datetime.now(UTC))
    e.screenshot_path = overrides.get("screenshot_path", "evidence/screenshots/2026-02/test.png")
    e.screenshot_hash = overrides.get("screenshot_hash", "a" * 64)
    e.screenshot_size_bytes = overrides.get("screenshot_size_bytes", 50000)
    e.confidence = overrides.get("confidence", 0.92)
    e.regulation_violated = overrides.get("regulation_violated", "EC 1924/2006 Art. 10")
    e.violation = overrides.get("violation", None)
    e.audit_logs = overrides.get("audit_logs", [])
    return e


class TestSearchNoFilters:
    """Tests for search() with no filters returns all evidence."""

    async def test_search_returns_tuple_of_list_and_count(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search() returns (list[Evidence], total_count)."""
        mock_session.scalar = AsyncMock(return_value=2)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_evidence(), _make_evidence()
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search()
        assert total == 2
        assert len(results) == 2

    async def test_search_empty_returns_empty_list_and_zero(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search() with no data returns ([], 0)."""
        mock_session.scalar = AsyncMock(return_value=0)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search()
        assert total == 0
        assert results == []


class TestSearchCompetitorFilter:
    """Tests for search() with competitor_name filter."""

    async def test_filters_by_competitor_name(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search(competitor_name='X') returns only X's evidence."""
        mock_session.scalar = AsyncMock(return_value=1)
        evidence = _make_evidence(competitor_name="CompetitorA")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [evidence]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search(competitor_name="CompetitorA")
        assert total == 1
        assert len(results) == 1


class TestSearchSeverityFilter:
    """Tests for search() with severity filter."""

    async def test_filters_by_severity(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search(severity='high') returns only high severity evidence."""
        mock_session.scalar = AsyncMock(return_value=1)
        evidence = _make_evidence(severity="high")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [evidence]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search(severity="high")
        assert total == 1


class TestSearchViolationTypeFilter:
    """Tests for search() with violation_type filter."""

    async def test_filters_by_violation_type(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search(violation_type='X') returns matching evidence."""
        mock_session.scalar = AsyncMock(return_value=1)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_evidence()]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search(
            violation_type="unauthorized_treatment_claim"
        )
        assert total == 1


class TestSearchDateRange:
    """Tests for search() with date_from + date_to range."""

    async def test_filters_by_date_range(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search(date_from, date_to) filters by captured_at range."""
        mock_session.scalar = AsyncMock(return_value=1)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_evidence()]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search(
            date_from=datetime(2026, 1, 1, tzinfo=UTC),
            date_to=datetime(2026, 12, 31, tzinfo=UTC),
        )
        assert total == 1


class TestSearchClaimKeywords:
    """Tests for search() with claim_keywords (ILIKE match)."""

    async def test_filters_by_claim_keywords(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search(claim_keywords='brain') matches via ILIKE."""
        mock_session.scalar = AsyncMock(return_value=1)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_evidence(claim_text="treats brain fog")
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search(claim_keywords="brain")
        assert total == 1


class TestSearchCombinedFilters:
    """Tests for search() with multiple combined filters."""

    async def test_multiple_filters_combine(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search() with multiple filters applies all of them."""
        mock_session.scalar = AsyncMock(return_value=1)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_evidence()]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search(
            competitor_name="CompetitorA",
            severity="high",
            violation_type="unauthorized_treatment_claim",
            claim_keywords="brain",
        )
        assert total == 1
        assert len(results) == 1


class TestSearchPagination:
    """Tests for search() pagination (limit/offset, total_count)."""

    async def test_pagination_defaults(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search() defaults to limit=25, offset=0."""
        mock_session.scalar = AsyncMock(return_value=50)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_evidence() for _ in range(25)
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search()
        assert total == 50
        assert len(results) == 25

    async def test_pagination_custom_limit_offset(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search(limit=10, offset=20) paginates correctly."""
        mock_session.scalar = AsyncMock(return_value=50)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_evidence() for _ in range(10)
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search(limit=10, offset=20)
        assert total == 50
        assert len(results) == 10


class TestSearchSorting:
    """Tests for search() sorting."""

    async def test_sort_by_captured_at_desc_default(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search() defaults to captured_at desc sorting."""
        mock_session.scalar = AsyncMock(return_value=1)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_evidence()]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search(
            sort_by="captured_at", sort_order="desc"
        )
        assert total == 1

    async def test_sort_by_severity_asc(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search(sort_by='severity', sort_order='asc') sorts ascending."""
        mock_session.scalar = AsyncMock(return_value=1)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_evidence()]
        mock_session.execute = AsyncMock(return_value=mock_result)

        results, total = await evidence_repo.search(
            sort_by="severity", sort_order="asc"
        )
        assert total == 1

    async def test_invalid_sort_by_falls_back_to_captured_at(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """search(sort_by='__class__') falls back to captured_at (whitelist)."""
        mock_session.scalar = AsyncMock(return_value=1)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_evidence()]
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise — falls back to captured_at
        results, total = await evidence_repo.search(sort_by="__class__")
        assert total == 1


class TestGetByIdLightweight:
    """Tests for get_by_id_lightweight()."""

    async def test_returns_evidence_without_relations(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """get_by_id_lightweight() returns evidence without eager loading."""
        evidence = _make_evidence()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = evidence
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await evidence_repo.get_by_id_lightweight(evidence.id)
        assert result is not None

    async def test_returns_none_for_missing(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """get_by_id_lightweight() returns None for missing ID."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await evidence_repo.get_by_id_lightweight(uuid4())
        assert result is None


class TestGetById:
    """Tests for get_by_id()."""

    async def test_returns_evidence_with_relations(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """get_by_id() returns evidence with violation + audit_logs."""
        evidence = _make_evidence()
        evidence.violation = MagicMock()
        evidence.audit_logs = [MagicMock(spec=EvidenceAuditLog)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = evidence
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await evidence_repo.get_by_id(evidence.id)
        assert result is not None
        assert result.violation is not None
        assert len(result.audit_logs) == 1

    async def test_returns_none_for_missing_id(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """get_by_id() returns None for non-existent ID."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await evidence_repo.get_by_id(uuid4())
        assert result is None


class TestGetSummaryStats:
    """Tests for get_summary_stats()."""

    async def test_returns_correct_counts(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """get_summary_stats() returns total, by_severity, by_competitor, by_violation_type."""
        # Mock: total count
        mock_session.scalar = AsyncMock(return_value=10)

        # Mock: three execute calls (severity, competitor, violation_type)
        severity_result = MagicMock()
        severity_result.all.return_value = [("high", 5), ("medium", 3), ("low", 2)]

        competitor_result = MagicMock()
        competitor_result.all.return_value = [("CompA", 6), ("CompB", 4)]

        type_result = MagicMock()
        type_result.all.return_value = [("violation", 8), ("suspect", 2)]

        mock_session.execute = AsyncMock(
            side_effect=[severity_result, competitor_result, type_result]
        )

        stats = await evidence_repo.get_summary_stats()
        assert stats["total_evidence"] == 10
        assert stats["by_severity"] == {"high": 5, "medium": 3, "low": 2}
        assert stats["by_competitor"] == {"CompA": 6, "CompB": 4}
        assert stats["by_violation_type"] == {"violation": 8, "suspect": 2}


class TestGetDistinctCompetitors:
    """Tests for get_distinct_competitors()."""

    async def test_returns_sorted_unique_names(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """get_distinct_competitors() returns sorted unique competitor names."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            "CompetitorA", "CompetitorB", "CompetitorC"
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        names = await evidence_repo.get_distinct_competitors()
        assert names == ["CompetitorA", "CompetitorB", "CompetitorC"]


class TestGetCompetitorTimeline:
    """Tests for get_competitor_timeline()."""

    async def test_returns_monthly_counts(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """get_competitor_timeline() returns [{month, count}, ...]."""
        mock_result = MagicMock()
        row1 = MagicMock()
        row1.month = "2026-01"
        row1.count = 3
        row2 = MagicMock()
        row2.month = "2026-02"
        row2.count = 5
        mock_result.all.return_value = [row1, row2]
        mock_session.execute = AsyncMock(return_value=mock_result)

        timeline = await evidence_repo.get_competitor_timeline("CompetitorA")
        assert len(timeline) == 2
        assert timeline[0] == {"month": "2026-01", "count": 3}
        assert timeline[1] == {"month": "2026-02", "count": 5}


class TestLogDownload:
    """Tests for log_download()."""

    async def test_creates_audit_entry(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """log_download() creates audit log entry with action='downloaded'."""
        evidence_id = uuid4()
        await evidence_repo.log_download(evidence_id)

        mock_session.add.assert_called_once()
        audit_arg = mock_session.add.call_args[0][0]
        assert isinstance(audit_arg, EvidenceAuditLog)
        assert audit_arg.action == "downloaded"
        assert audit_arg.evidence_id == evidence_id
        assert audit_arg.actor == "operator"
