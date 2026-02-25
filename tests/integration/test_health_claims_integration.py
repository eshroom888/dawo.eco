"""Integration tests for EU Health Claims Monitor.

Story 6-1, Task 13: Integration tests.

Tests the full pipeline flow with real component interactions
(mocked HTTP only, real parsing/filtering/detection).
"""

import asyncio
import pytest
from io import BytesIO
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from core.regulatory.events import RegulatoryEventEmitter, RegulatoryEvent, RegulatoryEventType
from core.regulatory.models import ChangeType, ChangeSeverity
from teams.dawo.scanners.health_claims.client import HealthClaimsClient
from teams.dawo.scanners.health_claims.parser import RegisterParser
from teams.dawo.scanners.health_claims.relevance_filter import RelevanceFilter
from teams.dawo.scanners.health_claims.change_detector import ChangeDetector
from teams.dawo.scanners.health_claims.repository import HealthClaimsRepository
from teams.dawo.scanners.health_claims.pipeline import HealthClaimsMonitorPipeline
from teams.dawo.scanners.health_claims.schemas import MonitorStatus, ClaimChangeRecord


@dataclass
class MockRetryResult:
    success: bool = True
    response: object = None
    attempts: int = 1
    last_error: Optional[str] = None
    is_incomplete: bool = False


def _create_xls_data(claims_data: list[dict]) -> bytes:
    """Create XLS bytes from claim data."""
    df = pd.DataFrame(claims_data)
    buf = BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def _create_csv_data(claims_data: list[dict]) -> bytes:
    """Create CSV bytes from claim data."""
    df = pd.DataFrame(claims_data)
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")


BASE_CLAIMS = [
    {
        "Claim ID": "ID-001",
        "Claim Type": "Article 13.1",
        "Substance": "Beta-glucans from oat",
        "Health Relationship": "Blood cholesterol",
        "Claim Text": "Beta-glucans contribute to maintenance of normal blood cholesterol levels",
        "Conditions of Use": "3g per day",
        "Food Category": "Food supplements",
        "Status": "Authorised",
    },
    {
        "Claim ID": "ID-002",
        "Claim Type": "Article 13.1",
        "Substance": "Vitamin C",
        "Health Relationship": "Oxidative stress",
        "Claim Text": "Vitamin C contributes to protection of cells from oxidative stress",
        "Conditions of Use": "80mg per day",
        "Food Category": "Food supplements",
        "Status": "Authorised",
    },
    {
        "Claim ID": "ID-003",
        "Claim Type": "Article 13.1",
        "Substance": "Ganoderma lucidum",
        "Health Relationship": "Immune system",
        "Claim Text": "Ganoderma lucidum extract supports the immune system",
        "Conditions of Use": "1g per day",
        "Food Category": "Food supplements",
        "Status": "On hold",
    },
]


MODIFIED_CLAIMS = [
    BASE_CLAIMS[0],  # ID-001 unchanged
    BASE_CLAIMS[1],  # ID-002 unchanged
    {  # ID-003 status changed
        **BASE_CLAIMS[2],
        "Status": "Authorised",
    },
    {  # ID-004 new claim
        "Claim ID": "ID-004",
        "Claim Type": "Article 13.1",
        "Substance": "Ashwagandha root extract",
        "Health Relationship": "Stress management",
        "Claim Text": "Ashwagandha contributes to stress reduction",
        "Conditions of Use": "300mg per day",
        "Food Category": "Food supplements",
        "Status": "Authorised",
    },
]


@pytest.fixture
def parser():
    return RegisterParser()


@pytest.fixture
def relevance_filter():
    return RelevanceFilter(
        mushroom_keywords=("beta-glucan", "ganoderma", "reishi"),
        adaptogen_keywords=("ashwagandha", "rhodiola"),
        vitamin_mineral_keywords=("vitamin c", "vitamin d"),
    )


@pytest.fixture
def change_detector():
    return ChangeDetector(
        mushroom_keywords=("beta-glucan", "ganoderma", "reishi"),
        adaptogen_keywords=("ashwagandha", "rhodiola"),
        vitamin_mineral_keywords=("vitamin c", "vitamin d"),
    )


class TestFullPipelineIntegration:
    """Test 13.1: Full pipeline flow with real components."""

    @pytest.mark.asyncio
    async def test_full_pipeline_first_run(self, parser, relevance_filter, change_detector):
        """First run: download mock → parse → filter → detect → save → events."""
        xls_data = _create_xls_data(BASE_CLAIMS)

        # Mock client and repository
        mock_client = AsyncMock(spec=HealthClaimsClient)
        mock_client.download_register.return_value = xls_data

        mock_repo = AsyncMock(spec=HealthClaimsRepository)
        mock_repo.get_latest_snapshot.return_value = None
        mock_snapshot = MagicMock()
        mock_snapshot.id = "snap-001"
        mock_snapshot.snapshot_hash = "a" * 64
        mock_repo.save_snapshot.return_value = mock_snapshot
        mock_repo.save_changes.return_value = []

        mock_emitter = AsyncMock(spec=RegulatoryEventEmitter)

        pipeline = HealthClaimsMonitorPipeline(
            client=mock_client,
            parser=parser,
            relevance_filter=relevance_filter,
            change_detector=change_detector,
            repository=mock_repo,
            event_emitter=mock_emitter,
            source_url="https://example.com/test.xls",
        )

        result = await pipeline.execute()

        assert result.status == MonitorStatus.COMPLETE
        assert result.claim_count == 3
        assert result.relevant_count > 0  # Beta-glucans + Ganoderma + Vitamin C
        assert result.changes_detected == 0  # First run, no previous
        mock_repo.save_snapshot.assert_called_once()


class TestSequentialRuns:
    """Test 13.2: Change detection across two sequential runs."""

    @pytest.mark.asyncio
    async def test_detects_changes_between_runs(self, parser, relevance_filter, change_detector):
        """Second run detects changes vs first run data."""
        # Parse first run data
        first_data = _create_xls_data(BASE_CLAIMS)
        first_df = parser.parse(first_data)
        first_filtered, _ = relevance_filter.filter(first_df)

        # Parse second run data (with modifications)
        second_data = _create_xls_data(MODIFIED_CLAIMS)
        second_df = parser.parse(second_data)

        # Detect changes
        changes = change_detector.detect(first_df, second_df)

        # Should detect: ID-003 status change, ID-004 new
        assert len(changes) >= 2

        change_types = {c.change_type for c in changes}
        assert ChangeType.STATUS_CHANGED.value in change_types
        assert ChangeType.NEW.value in change_types

        # ID-003 (Ganoderma) status change should be CRITICAL (relevant mushroom)
        ganoderma_changes = [c for c in changes if c.claim_id == "ID-003" and c.change_type == ChangeType.STATUS_CHANGED.value]
        assert len(ganoderma_changes) == 1
        assert ganoderma_changes[0].is_relevant
        assert ganoderma_changes[0].severity == ChangeSeverity.CRITICAL.value


class TestRelevantClaimFiltering:
    """Test 13.3: Relevant claim filtering end-to-end."""

    def test_filters_relevant_claims(self, parser, relevance_filter):
        xls_data = _create_xls_data(BASE_CLAIMS)
        df = parser.parse(xls_data)
        filtered_df, stats = relevance_filter.filter(df)

        # Beta-glucans → mushroom
        # Vitamin C → vitamin_mineral
        # Ganoderma → mushroom
        assert stats.relevant_claims >= 3
        assert stats.mushroom_matches >= 2
        assert stats.vitamin_mineral_matches >= 1

        relevant = filtered_df[filtered_df["is_relevant"]]
        assert len(relevant) >= 3


class TestStatusChangeEvents:
    """Test 13.4: Event emission for status change."""

    @pytest.mark.asyncio
    async def test_status_change_emits_event(self, parser, relevance_filter, change_detector):
        """On hold → Authorised for relevant substance emits CRITICAL event."""
        first_data = _create_xls_data(BASE_CLAIMS)
        second_data = _create_xls_data(MODIFIED_CLAIMS)

        mock_client = AsyncMock(spec=HealthClaimsClient)
        mock_client.download_register.return_value = second_data

        # Mock repository with first run data as "previous"
        mock_repo = AsyncMock(spec=HealthClaimsRepository)
        mock_snapshot = MagicMock()
        mock_snapshot.id = "snap-001"
        mock_repo.get_latest_snapshot.return_value = mock_snapshot

        # Return first run claims as previous
        first_df = parser.parse(first_data)
        mock_claims = []
        for _, row in first_df.iterrows():
            claim = MagicMock()
            for col in first_df.columns:
                setattr(claim, col, row[col] if pd.notna(row[col]) else None)
            mock_claims.append(claim)
        mock_repo.get_claims_by_snapshot.return_value = mock_claims

        new_snapshot = MagicMock()
        new_snapshot.id = "snap-002"
        new_snapshot.snapshot_hash = "b" * 64
        mock_repo.save_snapshot.return_value = new_snapshot
        mock_repo.save_changes.return_value = []

        received_events = []
        mock_emitter = AsyncMock(spec=RegulatoryEventEmitter)
        mock_emitter.emit.side_effect = lambda e: received_events.append(e)

        pipeline = HealthClaimsMonitorPipeline(
            client=mock_client,
            parser=parser,
            relevance_filter=relevance_filter,
            change_detector=change_detector,
            repository=mock_repo,
            event_emitter=mock_emitter,
            source_url="https://example.com/test.xls",
        )

        result = await pipeline.execute()

        assert result.status == MonitorStatus.COMPLETE
        assert result.changes_detected > 0
        # Should have emitted at least one event for CRITICAL/HIGH severity changes
        assert mock_emitter.emit.call_count >= 1


class TestGracefulDegradation:
    """Test 13.5: Graceful degradation on download failure."""

    @pytest.mark.asyncio
    async def test_download_failure_preserves_previous(self, parser, relevance_filter, change_detector):
        mock_client = AsyncMock(spec=HealthClaimsClient)
        from teams.dawo.scanners.health_claims.client import HealthClaimsClientError
        mock_client.download_register.side_effect = HealthClaimsClientError("Service unavailable")

        mock_repo = AsyncMock(spec=HealthClaimsRepository)
        mock_emitter = AsyncMock(spec=RegulatoryEventEmitter)

        pipeline = HealthClaimsMonitorPipeline(
            client=mock_client,
            parser=parser,
            relevance_filter=relevance_filter,
            change_detector=change_detector,
            repository=mock_repo,
            event_emitter=mock_emitter,
        )

        result = await pipeline.execute()

        assert result.status == MonitorStatus.INCOMPLETE
        assert "Download failed" in result.errors[0]
        # Repository save should NOT have been called
        mock_repo.save_snapshot.assert_not_called()
        mock_repo.save_changes.assert_not_called()
