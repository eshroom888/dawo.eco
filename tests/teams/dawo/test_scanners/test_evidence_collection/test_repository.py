"""Tests for EvidenceRepository (Story 6-8, Task 7).

Tests CRUD, immutability guard, and integrity verification.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.regulatory.models import Evidence, EvidenceAuditLog
from teams.dawo.scanners.evidence_collection.repository import EvidenceRepository
from teams.dawo.scanners.evidence_collection.schemas import (
    EvidenceCreateDTO,
    ImmutableEvidenceError,
)


@pytest.fixture
def evidence_repo(mock_session, mock_storage_service) -> EvidenceRepository:
    """EvidenceRepository with mocked session and storage."""
    return EvidenceRepository(
        session=mock_session, storage_service=mock_storage_service
    )


@pytest.fixture
def sample_dto() -> EvidenceCreateDTO:
    """Sample EvidenceCreateDTO."""
    return EvidenceCreateDTO(
        violation_id=uuid4(),
        competitor_name="CompetitorA",
        source_url="https://instagram.com/p/ABC123/",
        source_type="instagram_post",
        claim_text="treats brain fog",
        claim_category="treatment",
        violation_type="unauthorized_treatment_claim",
        severity="high",
        regulation_violated="EC 1924/2006 Art. 10",
        detection_reasoning="Treatment claim prohibited",
        confidence=0.92,
        screenshot_path="evidence/screenshots/2026-02/test.png",
        screenshot_hash="a" * 64,
        screenshot_size_bytes=50000,
        captured_at=datetime.now(UTC),
        evidence_metadata={"page_title": "Post"},
    )


class TestEvidenceRepositoryCreate:
    """Tests for create method."""

    async def test_create_inserts_evidence_and_audit(
        self, evidence_repo: EvidenceRepository, sample_dto: EvidenceCreateDTO, mock_session
    ) -> None:
        """create() inserts Evidence record and audit log entry."""
        result = await evidence_repo.create(sample_dto)
        assert isinstance(result, Evidence)
        # session.add called twice: once for evidence, once for audit
        assert mock_session.add.call_count == 2

    async def test_create_returns_orm_object(
        self, evidence_repo: EvidenceRepository, sample_dto: EvidenceCreateDTO
    ) -> None:
        """create() returns Evidence ORM object with correct fields."""
        result = await evidence_repo.create(sample_dto)
        assert result.competitor_name == "CompetitorA"
        assert result.source_type == "instagram_post"
        assert result.severity == "high"


class TestEvidenceRepositoryGet:
    """Tests for get methods."""

    async def test_get_by_violation_id_returns_evidence(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """get_by_violation_id returns evidence if exists."""
        mock_evidence = MagicMock(spec=Evidence)
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_evidence
        mock_session.execute.return_value = mock_result

        result = await evidence_repo.get_by_violation_id(uuid4())
        assert result == mock_evidence

    async def test_get_by_violation_id_returns_none(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """get_by_violation_id returns None if not exists."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = await evidence_repo.get_by_violation_id(uuid4())
        assert result is None

    async def test_get_collected_violation_ids_returns_set(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """get_collected_violation_ids returns correct UUID set."""
        id1, id2 = uuid4(), uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [id1, id2]
        mock_session.execute.return_value = mock_result

        result = await evidence_repo.get_collected_violation_ids()
        assert result == {id1, id2}


class TestEvidenceRepositoryUpdate:
    """Tests for update (immutability guard)."""

    async def test_update_always_raises_immutable_error(
        self, evidence_repo: EvidenceRepository
    ) -> None:
        """update() ALWAYS raises ImmutableEvidenceError."""
        with pytest.raises(ImmutableEvidenceError):
            await evidence_repo.update(uuid4(), claim_text="changed")

    async def test_update_logs_modification_blocked(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """update() logs modification_blocked audit entry."""
        try:
            await evidence_repo.update(uuid4(), screenshot_hash="new")
        except ImmutableEvidenceError:
            pass
        # Verify audit log was added
        mock_session.add.assert_called_once()
        audit_arg = mock_session.add.call_args[0][0]
        assert isinstance(audit_arg, EvidenceAuditLog)
        assert audit_arg.action == "modification_blocked"


class TestEvidenceRepositoryVerifyIntegrity:
    """Tests for verify_integrity."""

    async def test_delegates_to_storage_service(
        self, evidence_repo: EvidenceRepository, mock_session, mock_storage_service
    ) -> None:
        """verify_integrity delegates hash comparison to storage service."""
        mock_evidence = MagicMock(spec=Evidence)
        mock_evidence.screenshot_path = "evidence/screenshots/2026-02/test.png"
        mock_evidence.screenshot_hash = "a" * 64
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_evidence
        mock_session.execute.return_value = mock_result

        result = await evidence_repo.verify_integrity(uuid4())
        assert result is True
        mock_storage_service.verify_integrity.assert_called_once()


class TestEvidenceRepositoryCommit:
    """Tests for commit."""

    async def test_commit_calls_session_commit(
        self, evidence_repo: EvidenceRepository, mock_session
    ) -> None:
        """commit() calls session.commit()."""
        await evidence_repo.commit()
        mock_session.commit.assert_called_once()
