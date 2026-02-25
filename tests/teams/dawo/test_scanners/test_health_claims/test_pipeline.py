"""Tests for HealthClaimsMonitorPipeline.

Story 6-1, Task 12.19-12.23: Pipeline tests.
"""

import pytest
from io import BytesIO
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pandas as pd

from core.regulatory.events import RegulatoryEventEmitter, RegulatoryEvent, RegulatoryEventType
from core.regulatory.models import ChangeType, ChangeSeverity, ClaimSnapshot, HealthClaim
from teams.dawo.scanners.health_claims.client import HealthClaimsClient, HealthClaimsClientError
from teams.dawo.scanners.health_claims.parser import RegisterParser, ParseError
from teams.dawo.scanners.health_claims.relevance_filter import RelevanceFilter
from teams.dawo.scanners.health_claims.change_detector import ChangeDetector
from teams.dawo.scanners.health_claims.repository import HealthClaimsRepository
from teams.dawo.scanners.health_claims.pipeline import HealthClaimsMonitorPipeline
from teams.dawo.scanners.health_claims.schemas import MonitorResult, MonitorStatus, ClaimChangeRecord, FilterStats


@pytest.fixture
def mock_client():
    client = AsyncMock(spec=HealthClaimsClient)
    client.download_register.return_value = b"<xls data>"
    return client


@pytest.fixture
def mock_parser(sample_claims_df):
    parser = MagicMock(spec=RegisterParser)
    parser.parse.return_value = sample_claims_df
    return parser


@pytest.fixture
def mock_filter():
    f = MagicMock(spec=RelevanceFilter)
    f.filter.side_effect = lambda df: (df, FilterStats(total_claims=len(df), relevant_claims=3))
    return f


@pytest.fixture
def mock_detector():
    detector = MagicMock(spec=ChangeDetector)
    detector.detect.return_value = []
    return detector


@pytest.fixture
def mock_repository():
    repo = AsyncMock(spec=HealthClaimsRepository)
    repo.get_latest_snapshot.return_value = None
    repo.get_claims_by_snapshot.return_value = []
    snapshot = MagicMock(spec=ClaimSnapshot)
    snapshot.id = uuid4()
    snapshot.snapshot_hash = "a" * 64
    repo.save_snapshot.return_value = snapshot
    repo.save_changes.return_value = 0
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_emitter():
    return AsyncMock(spec=RegulatoryEventEmitter)


@pytest.fixture
def pipeline(mock_client, mock_parser, mock_filter, mock_detector, mock_repository, mock_emitter):
    return HealthClaimsMonitorPipeline(
        client=mock_client,
        parser=mock_parser,
        relevance_filter=mock_filter,
        change_detector=mock_detector,
        repository=mock_repository,
        event_emitter=mock_emitter,
        source_url="https://example.com/data.xls",
    )


class TestPipelineHappyPath:
    """Test 12.19: Full happy path execution."""

    @pytest.mark.asyncio
    async def test_execute_complete(self, pipeline, mock_client, mock_parser, mock_filter, mock_detector, mock_repository):
        result = await pipeline.execute()
        assert result.status == MonitorStatus.COMPLETE
        mock_client.download_register.assert_called_once()
        mock_parser.parse.assert_called_once()
        mock_filter.filter.assert_called_once()
        mock_detector.detect.assert_called_once()
        mock_repository.save_snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_claim_count(self, pipeline, sample_claims_df, mock_parser):
        mock_parser.parse.return_value = sample_claims_df
        result = await pipeline.execute()
        assert result.claim_count == len(sample_claims_df)

    @pytest.mark.asyncio
    async def test_execute_returns_relevant_count(self, pipeline):
        result = await pipeline.execute()
        assert result.relevant_count == 3  # From mock_filter


class TestPipelineFirstRun:
    """Test 12.20: First run (no previous snapshot)."""

    @pytest.mark.asyncio
    async def test_first_run_no_changes(self, pipeline, mock_repository, mock_detector):
        mock_repository.get_latest_snapshot.return_value = None
        mock_detector.detect.return_value = []

        result = await pipeline.execute()
        assert result.status == MonitorStatus.COMPLETE
        assert result.changes_detected == 0


class TestPipelineDownloadFailure:
    """Test 12.21: Download failure returns INCOMPLETE."""

    @pytest.mark.asyncio
    async def test_download_failure_incomplete(self, pipeline, mock_client):
        mock_client.download_register.side_effect = HealthClaimsClientError("Connection refused")

        result = await pipeline.execute()
        assert result.status == MonitorStatus.INCOMPLETE
        assert len(result.errors) > 0
        assert "Download failed" in result.errors[0]


class TestPipelineParseFailure:
    """Test 12.22: Parse failure returns INCOMPLETE."""

    @pytest.mark.asyncio
    async def test_parse_failure_incomplete(self, pipeline, mock_parser):
        mock_parser.parse.side_effect = ParseError("Wrong columns")

        result = await pipeline.execute()
        assert result.status == MonitorStatus.INCOMPLETE
        assert len(result.errors) > 0
        assert "Parse failed" in result.errors[0]


class TestPipelineEventsPublished:
    """Test 12.23: Events published for CRITICAL changes."""

    @pytest.mark.asyncio
    async def test_critical_changes_emit_events(self, pipeline, mock_detector, mock_emitter):
        mock_detector.detect.return_value = [
            ClaimChangeRecord(
                claim_id="ID-003",
                change_type=ChangeType.STATUS_CHANGED.value,
                field_changed="status",
                old_value="On hold",
                new_value="Authorised",
                is_relevant=True,
                severity=ChangeSeverity.CRITICAL.value,
            ),
        ]

        result = await pipeline.execute()
        mock_emitter.emit.assert_called_once()
        event = mock_emitter.emit.call_args[0][0]
        assert isinstance(event, RegulatoryEvent)
        assert event.event_type == RegulatoryEventType.CLAIM_STATUS_CHANGED
        assert event.claim_id == "ID-003"
        assert event.severity == ChangeSeverity.CRITICAL.value

    @pytest.mark.asyncio
    async def test_low_severity_no_events(self, pipeline, mock_detector, mock_emitter):
        mock_detector.detect.return_value = [
            ClaimChangeRecord(
                claim_id="ID-001",
                change_type=ChangeType.MODIFIED.value,
                field_changed="claim_text",
                old_value="old",
                new_value="new",
                is_relevant=False,
                severity=ChangeSeverity.LOW.value,
            ),
        ]

        result = await pipeline.execute()
        mock_emitter.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_relevant_claim_emits_event(self, pipeline, mock_detector, mock_emitter):
        mock_detector.detect.return_value = [
            ClaimChangeRecord(
                claim_id="ID-006",
                change_type=ChangeType.NEW.value,
                new_value="Rhodiola",
                is_relevant=True,
                severity=ChangeSeverity.HIGH.value,
            ),
        ]

        result = await pipeline.execute()
        mock_emitter.emit.assert_called_once()
        event = mock_emitter.emit.call_args[0][0]
        assert event.event_type == RegulatoryEventType.NEW_CLAIM_APPROVED

    @pytest.mark.asyncio
    async def test_change_counts_in_result(self, pipeline, mock_detector):
        mock_detector.detect.return_value = [
            ClaimChangeRecord(claim_id="ID-001", change_type=ChangeType.NEW.value, severity="low"),
            ClaimChangeRecord(claim_id="ID-002", change_type=ChangeType.REMOVED.value, severity="low"),
            ClaimChangeRecord(claim_id="ID-003", change_type=ChangeType.STATUS_CHANGED.value, field_changed="status", severity="medium"),
            ClaimChangeRecord(claim_id="ID-004", change_type=ChangeType.MODIFIED.value, field_changed="claim_text", severity="low"),
        ]

        result = await pipeline.execute()
        assert result.changes_detected == 4
        assert result.new_claims == 1
        assert result.removed_claims == 1
        assert result.status_changes == 1
        assert result.modified_claims == 1
