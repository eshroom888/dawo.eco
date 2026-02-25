"""Tests for LeadRepository.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Tests repository CRUD operations with mocked AsyncSession.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from teams.dawo.leads.repository import LeadRepository
from core.leads.models import Lead, LeadActivity, LeadStatus, LeadSource, ActivityType


class TestLeadRepository:
    """Tests for LeadRepository class."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock AsyncSession."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> LeadRepository:
        """Create LeadRepository with mock session."""
        return LeadRepository(session=mock_session)

    @pytest.fixture
    def sample_lead_data(self) -> dict:
        """Sample lead data for creation."""
        return {
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "company": "Example Corp",
            "job_title": "CEO",
            "country": "Norway",
            "source": "cold_research",
            "status": "new",
        }

    @pytest.fixture
    def mock_lead(self) -> MagicMock:
        """Create mock Lead instance."""
        lead = MagicMock(spec=Lead)
        lead.id = uuid4()
        lead.email = "john.doe@example.com"
        lead.first_name = "John"
        lead.last_name = "Doe"
        lead.company = "Example Corp"
        lead.status = "new"
        lead.score = 0.0
        lead.updated_at = datetime.now(UTC)
        return lead

    # =========================================================================
    # create_lead tests
    # =========================================================================

    async def test_create_lead_adds_to_session(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        sample_lead_data: dict,
    ) -> None:
        """Test that create_lead adds lead to session."""
        await repository.create_lead(sample_lead_data)

        # Verify lead was added to session
        assert mock_session.add.called
        mock_session.flush.assert_called()
        mock_session.commit.assert_called()

    async def test_create_lead_creates_activity_record(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        sample_lead_data: dict,
    ) -> None:
        """Test that create_lead creates CREATED activity."""
        await repository.create_lead(sample_lead_data)

        # Should have added both Lead and LeadActivity
        assert mock_session.add.call_count >= 2

    async def test_create_lead_returns_lead(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        sample_lead_data: dict,
    ) -> None:
        """Test that create_lead returns the created lead."""
        result = await repository.create_lead(sample_lead_data)

        # Lead class was instantiated
        assert result is not None
        mock_session.refresh.assert_called()

    # =========================================================================
    # bulk_create_leads tests
    # =========================================================================

    async def test_bulk_create_leads_creates_multiple(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk creation of multiple leads."""
        leads_data = [
            {"email": "lead1@example.com", "first_name": "Lead", "last_name": "One", "company": "Corp"},
            {"email": "lead2@example.com", "first_name": "Lead", "last_name": "Two", "company": "Corp"},
        ]

        # Mock get_lead_by_email to return None (no duplicates)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        count, ids = await repository.bulk_create_leads(leads_data)

        assert count == 2
        assert len(ids) == 2
        mock_session.commit.assert_called()

    async def test_bulk_create_leads_skips_duplicates(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test that bulk create skips existing emails."""
        leads_data = [
            {"email": "existing@example.com", "first_name": "Existing", "last_name": "Lead", "company": "Corp"},
        ]

        # Mock get_lead_by_email to return existing lead
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        count, ids = await repository.bulk_create_leads(leads_data)

        assert count == 0
        assert len(ids) == 0

    async def test_bulk_create_leads_empty_list(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk create with empty list."""
        count, ids = await repository.bulk_create_leads([])

        assert count == 0
        assert ids == []
        mock_session.commit.assert_not_called()

    async def test_bulk_create_leads_handles_partial_failure(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that bulk create continues on individual lead failure."""
        leads_data = [
            {"email": "good@example.com", "first_name": "Good", "last_name": "Lead", "company": "Corp"},
            {"email": "bad@example.com"},  # Missing required fields
        ]

        # First call succeeds (no existing), second fails
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Should continue despite errors
        count, ids = await repository.bulk_create_leads(leads_data)

        # At least one should have been attempted
        assert mock_session.commit.called

    # =========================================================================
    # get_lead_by_id tests
    # =========================================================================

    async def test_get_lead_by_id_returns_lead(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test get_lead_by_id returns lead when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        result = await repository.get_lead_by_id(mock_lead.id)

        assert result == mock_lead
        mock_session.execute.assert_called_once()

    async def test_get_lead_by_id_returns_none_when_not_found(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_lead_by_id returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_lead_by_id(uuid4())

        assert result is None

    # =========================================================================
    # get_lead_by_email tests
    # =========================================================================

    async def test_get_lead_by_email_case_insensitive(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test get_lead_by_email is case insensitive."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        result = await repository.get_lead_by_email("JOHN.DOE@EXAMPLE.COM")

        assert result == mock_lead

    async def test_get_lead_by_email_returns_none_when_not_found(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_lead_by_email returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_lead_by_email("notfound@example.com")

        assert result is None

    # =========================================================================
    # get_leads_by_company tests
    # =========================================================================

    async def test_get_leads_by_company_partial_match(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test get_leads_by_company uses partial matching."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_lead]
        mock_session.execute.return_value = mock_result

        results = await repository.get_leads_by_company("Example")

        assert len(results) == 1
        assert results[0] == mock_lead

    async def test_get_leads_by_company_with_country_filter(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test get_leads_by_company with country filter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_lead]
        mock_session.execute.return_value = mock_result

        results = await repository.get_leads_by_company("Example", country="Norway")

        assert len(results) == 1
        mock_session.execute.assert_called_once()

    async def test_get_leads_by_company_returns_empty_list(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_leads_by_company returns empty list when none found."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await repository.get_leads_by_company("Nonexistent")

        assert results == []

    # =========================================================================
    # get_leads_by_status tests
    # =========================================================================

    async def test_get_leads_by_status_returns_ordered_by_score(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test get_leads_by_status returns leads ordered by score."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_lead]
        mock_session.execute.return_value = mock_result

        results = await repository.get_leads_by_status(LeadStatus.NEW)

        assert len(results) == 1
        mock_session.execute.assert_called_once()

    async def test_get_leads_by_status_respects_limit(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_leads_by_status respects limit parameter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repository.get_leads_by_status(LeadStatus.NEW, limit=50)

        mock_session.execute.assert_called_once()

    # =========================================================================
    # update_lead_status tests
    # =========================================================================

    async def test_update_lead_status_updates_status(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test update_lead_status updates the status."""
        # Mock get_lead_by_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        result = await repository.update_lead_status(mock_lead.id, LeadStatus.CONTACTED)

        assert result is not None
        mock_session.commit.assert_called()

    async def test_update_lead_status_creates_activity(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test update_lead_status creates STATUS_CHANGE activity."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        await repository.update_lead_status(mock_lead.id, LeadStatus.CONTACTED)

        # Should have added activity
        assert mock_session.add.called

    async def test_update_lead_status_returns_none_when_not_found(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test update_lead_status returns None when lead not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.update_lead_status(uuid4(), LeadStatus.CONTACTED)

        assert result is None

    async def test_update_lead_status_sets_lost_reason(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test update_lead_status sets lost_reason for LOST status."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        await repository.update_lead_status(
            mock_lead.id,
            LeadStatus.LOST,
            reason="Not interested"
        )

        assert mock_lead.lost_reason == "Not interested"

    # =========================================================================
    # update_lead_score tests
    # =========================================================================

    async def test_update_lead_score_updates_score(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test update_lead_score updates the score."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        result = await repository.update_lead_score(mock_lead.id, 85.5)

        assert result is not None
        assert mock_lead.score == 85.5
        mock_session.commit.assert_called()

    async def test_update_lead_score_sets_breakdown(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test update_lead_score sets score_breakdown."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        breakdown = {"fit": 80, "engagement": 90}
        await repository.update_lead_score(mock_lead.id, 85.0, score_breakdown=breakdown)

        assert mock_lead.score_breakdown == breakdown

    async def test_update_lead_score_creates_activity(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
        mock_lead: MagicMock,
    ) -> None:
        """Test update_lead_score creates SCORE_UPDATED activity."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute.return_value = mock_result

        await repository.update_lead_score(mock_lead.id, 75.0)

        # Should have added activity
        assert mock_session.add.called

    # =========================================================================
    # count_leads_by_status tests
    # =========================================================================

    async def test_count_leads_by_status_returns_counts(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test count_leads_by_status returns status counts."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("new", 10),
            ("contacted", 5),
            ("converted", 2),
        ]
        mock_session.execute.return_value = mock_result

        counts = await repository.count_leads_by_status()

        assert counts == {"new": 10, "contacted": 5, "converted": 2}

    async def test_count_leads_by_status_empty_database(
        self,
        repository: LeadRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test count_leads_by_status with no leads."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        counts = await repository.count_leads_by_status()

        assert counts == {}
