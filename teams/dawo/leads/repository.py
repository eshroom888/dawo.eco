"""Lead Repository for database operations.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Provides async database operations for Lead model:
- CRUD operations
- Bulk operations for pipeline efficiency
- Query methods for duplicate detection
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from core.leads.models import Lead, LeadActivity, OutreachEmail, LeadStatus, LeadSource, ActivityType, EmailStatus


logger = logging.getLogger(__name__)


class LeadRepository:
    """Async repository for Lead database operations.

    Provides CRUD operations and query methods for the Lead model.
    Uses SQLAlchemy async ORM patterns.

    Accepts AsyncSession via dependency injection.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create_lead(self, lead_data: dict) -> Lead:
        """Create a single lead.

        Args:
            lead_data: Dictionary of lead attributes

        Returns:
            Created Lead instance

        Raises:
            Exception: On database error
        """
        lead = Lead(**lead_data)
        self._session.add(lead)
        await self._session.flush()

        # Create activity record
        await self._create_activity(
            lead_id=lead.id,
            activity_type=ActivityType.CREATED,
            description="Lead created via B2B research scanner",
            metadata={"source": "b2b_lead_pipeline"},
        )

        await self._session.commit()
        await self._session.refresh(lead)

        logger.debug(f"Created lead: {lead.email} (id={lead.id})")
        return lead

    async def bulk_create_leads(
        self,
        leads_data: list[dict],
    ) -> tuple[int, list[UUID]]:
        """Create multiple leads in a single transaction.

        Uses PostgreSQL upsert to handle potential duplicates gracefully.

        Args:
            leads_data: List of lead attribute dictionaries

        Returns:
            Tuple of (count created, list of created UUIDs)

        Note:
            Duplicates (by email) are skipped, not updated.
        """
        if not leads_data:
            return 0, []

        created_ids: list[UUID] = []
        created_count = 0

        try:
            for lead_data in leads_data:
                try:
                    # Check if already exists
                    existing = await self.get_lead_by_email(lead_data["email"])
                    if existing:
                        logger.debug(f"Skipping existing lead: {lead_data['email']}")
                        continue

                    # Create lead
                    lead = Lead(**lead_data)
                    self._session.add(lead)
                    await self._session.flush()

                    # Create activity record
                    activity = LeadActivity(
                        lead_id=lead.id,
                        activity_type=ActivityType.CREATED.value,
                        description="Lead created via B2B research scanner",
                        activity_metadata={"source": "b2b_lead_pipeline"},
                        created_by="system",
                    )
                    self._session.add(activity)

                    created_ids.append(lead.id)
                    created_count += 1

                except Exception as e:
                    logger.warning(f"Failed to create lead {lead_data.get('email')}: {e}")
                    continue

            await self._session.commit()
            logger.info(f"Bulk created {created_count} leads")

            return created_count, created_ids

        except Exception as e:
            logger.error(f"Bulk create failed: {e}")
            await self._session.rollback()
            raise

    async def get_lead_by_id(self, lead_id: UUID) -> Optional[Lead]:
        """Get a lead by ID.

        Args:
            lead_id: Lead UUID

        Returns:
            Lead instance or None if not found
        """
        result = await self._session.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        return result.scalar_one_or_none()

    async def get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Get a lead by email address.

        Args:
            email: Email address (case-insensitive)

        Returns:
            Lead instance or None if not found
        """
        result = await self._session.execute(
            select(Lead).where(func.lower(Lead.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_leads_by_company(
        self,
        company: str,
        country: Optional[str] = None,
    ) -> Sequence[Lead]:
        """Get leads by company name.

        Args:
            company: Company name (case-insensitive partial match)
            country: Optional country filter

        Returns:
            List of matching leads
        """
        query = select(Lead).where(
            func.lower(Lead.company).contains(company.lower())
        )

        if country:
            query = query.where(func.lower(Lead.country) == country.lower())

        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_leads_by_status(
        self,
        status: LeadStatus,
        limit: int = 100,
    ) -> Sequence[Lead]:
        """Get leads by pipeline status.

        Args:
            status: Lead status to filter by
            limit: Maximum results

        Returns:
            List of matching leads
        """
        result = await self._session.execute(
            select(Lead)
            .where(Lead.status == status.value)
            .order_by(Lead.score.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_lead_status(
        self,
        lead_id: UUID,
        status: LeadStatus,
        reason: Optional[str] = None,
    ) -> Optional[Lead]:
        """Update lead pipeline status.

        Args:
            lead_id: Lead UUID
            status: New status
            reason: Optional reason for status change

        Returns:
            Updated Lead or None if not found
        """
        lead = await self.get_lead_by_id(lead_id)
        if not lead:
            return None

        old_status = lead.status
        lead.status = status.value
        lead.updated_at = datetime.now(UTC)

        # Update lost_reason if applicable
        if status == LeadStatus.LOST and reason:
            lead.lost_reason = reason

        # Create activity record
        await self._create_activity(
            lead_id=lead_id,
            activity_type=ActivityType.STATUS_CHANGE,
            description=f"Status changed from {old_status} to {status.value}",
            metadata={
                "old_status": old_status,
                "new_status": status.value,
                "reason": reason,
            },
        )

        await self._session.commit()
        await self._session.refresh(lead)

        return lead

    async def update_lead_score(
        self,
        lead_id: UUID,
        score: float,
        score_breakdown: Optional[dict] = None,
    ) -> Optional[Lead]:
        """Update lead score.

        Args:
            lead_id: Lead UUID
            score: New score (0-100)
            score_breakdown: Optional scoring breakdown

        Returns:
            Updated Lead or None if not found
        """
        lead = await self.get_lead_by_id(lead_id)
        if not lead:
            return None

        old_score = lead.score
        lead.score = score
        lead.updated_at = datetime.now(UTC)

        if score_breakdown:
            lead.score_breakdown = score_breakdown

        # Create activity record
        await self._create_activity(
            lead_id=lead_id,
            activity_type=ActivityType.SCORE_UPDATED,
            description=f"Score updated from {old_score:.1f} to {score:.1f}",
            metadata={
                "old_score": old_score,
                "new_score": score,
                "breakdown": score_breakdown,
            },
        )

        await self._session.commit()
        await self._session.refresh(lead)

        return lead

    async def count_leads_by_status(self) -> dict[str, int]:
        """Count leads by status.

        Returns:
            Dict mapping status to count
        """
        result = await self._session.execute(
            select(Lead.status, func.count(Lead.id))
            .group_by(Lead.status)
        )

        return {status: count for status, count in result.all()}

    async def _create_activity(
        self,
        lead_id: UUID,
        activity_type: ActivityType,
        description: str,
        metadata: Optional[dict] = None,
    ) -> LeadActivity:
        """Create a lead activity record.

        Args:
            lead_id: Lead UUID
            activity_type: Type of activity
            description: Human-readable description
            metadata: Optional additional data

        Returns:
            Created LeadActivity instance
        """
        activity = LeadActivity(
            lead_id=lead_id,
            activity_type=activity_type.value,
            description=description,
            activity_metadata=metadata,
            created_by="system",
        )
        self._session.add(activity)
        return activity

    # =========================================================================
    # Enrichment Methods (Story 5-2)
    # =========================================================================

    async def get_by_id(self, lead_id: UUID) -> Optional[Lead]:
        """Get a lead by ID (alias for get_lead_by_id).

        Args:
            lead_id: Lead UUID

        Returns:
            Lead instance or None if not found
        """
        return await self.get_lead_by_id(lead_id)

    async def get_leads_for_enrichment(
        self,
        limit: int = 10,
    ) -> Sequence[Lead]:
        """Get leads ready for enrichment.

        Queries leads with status=NEW, ordered by creation time (oldest first).

        Args:
            limit: Maximum number of leads to return

        Returns:
            Sequence of Lead instances ready for enrichment
        """
        result = await self._session.execute(
            select(Lead)
            .where(Lead.status == LeadStatus.NEW.value)
            .order_by(Lead.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_enrichment(
        self,
        lead_id: UUID,
        enrichment_data: dict,
        status: LeadStatus,
        score: float,
        enriched_at: datetime,
    ) -> Optional[Lead]:
        """Update lead with enrichment data.

        Args:
            lead_id: Lead UUID
            enrichment_data: Enrichment data dict for JSONB storage
            status: New lead status (QUALIFIED, RESEARCHING, CONVERTED)
            score: Lead score (0-100)
            enriched_at: Timestamp of enrichment

        Returns:
            Updated Lead or None if not found
        """
        lead = await self.get_lead_by_id(lead_id)
        if not lead:
            return None

        old_status = lead.status

        lead.enrichment_data = enrichment_data
        lead.status = status.value
        lead.score = score
        lead.enriched_at = enriched_at
        lead.updated_at = datetime.now(UTC)

        # Extract score breakdown if present
        if "score_breakdown" in enrichment_data:
            lead.score_breakdown = enrichment_data["score_breakdown"]

        # Create status change activity if status changed
        if old_status != status.value:
            await self._create_activity(
                lead_id=lead_id,
                activity_type=ActivityType.STATUS_CHANGE,
                description=f"Status changed from {old_status} to {status.value} via enrichment",
                metadata={
                    "old_status": old_status,
                    "new_status": status.value,
                    "source": "enrichment_pipeline",
                },
            )

        await self._session.commit()
        await self._session.refresh(lead)

        logger.debug(f"Updated enrichment for lead {lead_id}: status={status.value}, score={score:.1f}")
        return lead

    async def add_activity(
        self,
        lead_id: UUID,
        activity_type: ActivityType,
        description: str,
        metadata: Optional[dict] = None,
    ) -> LeadActivity:
        """Add an activity log entry for a lead.

        Public method for pipeline and service use.

        Args:
            lead_id: Lead UUID
            activity_type: Type of activity
            description: Human-readable description
            metadata: Optional additional data

        Returns:
            Created LeadActivity instance
        """
        activity = await self._create_activity(
            lead_id=lead_id,
            activity_type=activity_type,
            description=description,
            metadata=metadata,
        )
        await self._session.commit()
        return activity

    async def mark_existing_customer(self, lead_id: UUID) -> Optional[Lead]:
        """Mark a lead as an existing DAWO customer.

        Sets status to CONVERTED and adds "existing_customer" tag.

        Args:
            lead_id: Lead UUID

        Returns:
            Updated Lead or None if not found
        """
        lead = await self.get_lead_by_id(lead_id)
        if not lead:
            return None

        old_status = lead.status
        lead.status = LeadStatus.CONVERTED.value
        lead.converted_at = datetime.now(UTC)
        lead.updated_at = datetime.now(UTC)

        # Add tag
        if "existing_customer" not in lead.tags:
            lead.tags = lead.tags + ["existing_customer"]

        # Create activity record
        await self._create_activity(
            lead_id=lead_id,
            activity_type=ActivityType.STATUS_CHANGE,
            description=f"Marked as existing DAWO customer (was {old_status})",
            metadata={
                "old_status": old_status,
                "new_status": LeadStatus.CONVERTED.value,
                "reason": "existing_customer",
            },
        )

        await self._session.commit()
        await self._session.refresh(lead)

        logger.info(f"Marked lead {lead_id} as existing customer")
        return lead

    async def get_enrichment_stats(self) -> dict[str, int]:
        """Get enrichment statistics by status.

        Returns:
            Dict with counts for NEW, RESEARCHING, QUALIFIED, CONVERTED
        """
        result = await self._session.execute(
            select(Lead.status, func.count(Lead.id))
            .where(
                Lead.status.in_([
                    LeadStatus.NEW.value,
                    LeadStatus.RESEARCHING.value,
                    LeadStatus.QUALIFIED.value,
                    LeadStatus.CONVERTED.value,
                ])
            )
            .group_by(Lead.status)
        )

        # Initialize with zeros
        stats = {
            "new": 0,
            "researching": 0,
            "qualified": 0,
            "converted": 0,
        }

        # Update with actual counts
        for status_val, count in result.all():
            stats[status_val] = count

        return stats

    # =========================================================================
    # Outreach Methods (Story 5-3)
    # =========================================================================

    async def get_leads_for_outreach(
        self,
        limit: int = 10,
        min_confidence: float = 6.0,
    ) -> Sequence[Lead]:
        """Get leads ready for outreach generation.

        Queries leads with:
        - status=QUALIFIED
        - confidence_score >= 6.0 (from enrichment_data, 0-10 scale per AC #1)
        - no existing outreach_data

        Args:
            limit: Maximum number of leads to return
            min_confidence: Minimum confidence score (0-10 scale, default 6.0)

        Returns:
            Sequence of Lead instances ready for outreach
        """
        from sqlalchemy import cast, Float

        result = await self._session.execute(
            select(Lead)
            .where(
                Lead.status == LeadStatus.QUALIFIED.value,
                Lead.outreach_data.is_(None),
                # Query confidence_score from enrichment_data JSONB (0-10 scale)
                cast(
                    Lead.enrichment_data["confidence_score"].astext,
                    Float
                ) >= min_confidence,
            )
            .order_by(Lead.score.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_outreach(
        self,
        lead_id: UUID,
        outreach_data: dict,
        status: LeadStatus,
    ) -> Optional[Lead]:
        """Update lead with outreach data.

        Args:
            lead_id: Lead UUID
            outreach_data: Outreach data dict for JSONB storage
            status: New lead status (typically OUTREACH_PENDING)

        Returns:
            Updated Lead or None if not found
        """
        lead = await self.get_lead_by_id(lead_id)
        if not lead:
            return None

        old_status = lead.status

        lead.outreach_data = outreach_data
        lead.status = status.value
        lead.outreach_generated_at = datetime.now(UTC)
        lead.updated_at = datetime.now(UTC)

        # Create status change activity if status changed
        if old_status != status.value:
            await self._create_activity(
                lead_id=lead_id,
                activity_type=ActivityType.STATUS_CHANGE,
                description=f"Status changed from {old_status} to {status.value} via outreach generation",
                metadata={
                    "old_status": old_status,
                    "new_status": status.value,
                    "source": "outreach_pipeline",
                    "template_type": outreach_data.get("template_type"),
                },
            )

        await self._session.commit()
        await self._session.refresh(lead)

        logger.debug(f"Updated outreach for lead {lead_id}: status={status.value}")
        return lead

    async def get_outreach_stats(self) -> dict[str, int]:
        """Get outreach statistics by status.

        Returns:
            Dict with counts for QUALIFIED, OUTREACH_PENDING, CONTACTED
        """
        result = await self._session.execute(
            select(Lead.status, func.count(Lead.id))
            .where(
                Lead.status.in_([
                    LeadStatus.QUALIFIED.value,
                    LeadStatus.OUTREACH_PENDING.value,
                    LeadStatus.CONTACTED.value,
                ])
            )
            .group_by(Lead.status)
        )

        # Initialize with zeros
        stats = {
            "qualified": 0,
            "outreach_pending": 0,
            "contacted": 0,
        }

        # Update with actual counts
        for status_val, count in result.all():
            stats[status_val] = count

        return stats

    # =========================================================================
    # Gmail Send Methods (Story 5-4)
    # =========================================================================

    async def get_approved_for_sending(
        self,
        limit: int = 10,
    ) -> Sequence[Lead]:
        """Get leads with approved outreach drafts ready for sending.

        Queries leads where:
        - status = OUTREACH_PENDING
        - outreach_data contains approved draft

        Orders by outreach_generated_at ASC (earliest first).

        Args:
            limit: Maximum number of leads to return

        Returns:
            Sequence of Lead instances approved for sending
        """
        from sqlalchemy import cast, Boolean

        result = await self._session.execute(
            select(Lead)
            .where(
                Lead.status == LeadStatus.OUTREACH_PENDING.value,
                Lead.outreach_data.isnot(None),
                # C3 fix: only return leads with approved=true in outreach_data
                cast(
                    Lead.outreach_data["approved"].astext,
                    Boolean,
                ) == True,
            )
            .order_by(Lead.outreach_generated_at.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_send_result(
        self,
        lead_id: UUID,
        gmail_message_id: str,
        gmail_thread_id: str,
    ) -> Optional[Lead]:
        """Update lead after successful email send.

        Sets status to CONTACTED, records send timestamp,
        and increments contact count.

        Args:
            lead_id: Lead UUID
            gmail_message_id: Gmail message ID
            gmail_thread_id: Gmail thread ID

        Returns:
            Updated Lead or None if not found
        """
        lead = await self.get_lead_by_id(lead_id)
        if not lead:
            return None

        old_status = lead.status
        lead.status = LeadStatus.CONTACTED.value
        lead.last_contacted_at = datetime.now(UTC)
        lead.contact_count = (lead.contact_count or 0) + 1
        lead.updated_at = datetime.now(UTC)

        # Create status change activity
        if old_status != LeadStatus.CONTACTED.value:
            await self._create_activity(
                lead_id=lead_id,
                activity_type=ActivityType.STATUS_CHANGE,
                description=f"Status changed from {old_status} to {LeadStatus.CONTACTED.value} via Gmail send",
                metadata={
                    "old_status": old_status,
                    "new_status": LeadStatus.CONTACTED.value,
                    "source": "gmail_pipeline",
                    "gmail_message_id": gmail_message_id,
                },
            )

        # Create email sent activity
        await self._create_activity(
            lead_id=lead_id,
            activity_type=ActivityType.EMAIL_SENT,
            description="Outreach email sent via Gmail API",
            metadata={
                "gmail_message_id": gmail_message_id,
                "gmail_thread_id": gmail_thread_id,
                "sent_at": datetime.now(UTC).isoformat(),
            },
        )

        await self._session.commit()
        await self._session.refresh(lead)

        logger.debug(f"Updated send result for lead {lead_id}: gmail_msg={gmail_message_id}")
        return lead

    async def create_outreach_email(
        self,
        lead_id: UUID,
        email_data: dict,
    ) -> OutreachEmail:
        """Create OutreachEmail record with Gmail tracking fields.

        Args:
            lead_id: Lead UUID
            email_data: Dict with subject, body, gmail_message_id,
                gmail_thread_id, sent_at, status

        Returns:
            Created OutreachEmail instance
        """
        email = OutreachEmail(
            lead_id=lead_id,
            subject=email_data.get("subject", ""),
            body=email_data.get("body", ""),
            status=email_data.get("status", EmailStatus.SENT.value),
            gmail_message_id=email_data.get("gmail_message_id"),
            gmail_thread_id=email_data.get("gmail_thread_id"),
            sent_at=email_data.get("sent_at"),
        )
        self._session.add(email)
        await self._session.commit()
        await self._session.refresh(email)

        logger.debug(f"Created OutreachEmail for lead {lead_id}: gmail_msg={email.gmail_message_id}")
        return email

    async def get_send_stats(self) -> dict[str, int]:
        """Get send statistics by lead status.

        Returns:
            Dict with counts for OUTREACH_PENDING, CONTACTED
        """
        result = await self._session.execute(
            select(Lead.status, func.count(Lead.id))
            .where(
                Lead.status.in_([
                    LeadStatus.OUTREACH_PENDING.value,
                    LeadStatus.CONTACTED.value,
                ])
            )
            .group_by(Lead.status)
        )

        stats = {
            "outreach_pending": 0,
            "contacted": 0,
        }

        for status_val, count in result.all():
            stats[status_val] = count

        return stats

    # =========================================================================
    # Pipeline Methods (Story 5-5)
    # =========================================================================

    async def get_pipeline_summary(self) -> dict[str, int]:
        """Get lead counts per status across ALL LeadStatus values.

        Returns:
            Dict mapping every LeadStatus value to its count.
            Statuses with no leads return 0.
        """
        result = await self._session.execute(
            select(Lead.status, func.count(Lead.id))
            .group_by(Lead.status)
        )

        # Initialize all statuses to 0
        summary: dict[str, int] = {s.value: 0 for s in LeadStatus}

        # Fill in actual counts
        for status_val, count in result.all():
            summary[status_val] = count

        return summary

    async def get_leads_filtered(
        self,
        status: Optional[LeadStatus] = None,
        search: Optional[str] = None,
        sort_by: str = "score",
        limit: int = 25,
        offset: int = 0,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> tuple[Sequence[Lead], int]:
        """Get paginated, filterable lead list.

        Args:
            status: Optional status filter
            search: Optional search term (matches company, email, first/last name)
            sort_by: Sort field (score, created_at, last_contacted_at)
            limit: Page size
            offset: Page offset
            date_from: Optional start date filter on created_at
            date_to: Optional end date filter on created_at

        Returns:
            Tuple of (leads, total_count)
        """
        # Build base conditions
        conditions = []
        if status:
            conditions.append(Lead.status == status.value)
        if date_from:
            conditions.append(Lead.created_at >= date_from)
        if date_to:
            conditions.append(Lead.created_at <= date_to)
        if search:
            search_term = f"%{search.lower()}%"
            conditions.append(
                or_(
                    func.lower(Lead.company).like(search_term),
                    func.lower(Lead.email).like(search_term),
                    func.lower(Lead.first_name).like(search_term),
                    func.lower(Lead.last_name).like(search_term),
                )
            )

        # Count query
        count_query = select(func.count(Lead.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self._session.execute(count_query)
        total = count_result.scalar_one()

        # Data query
        data_query = select(Lead)
        if conditions:
            data_query = data_query.where(and_(*conditions))

        # Sort
        sort_map = {
            "score": Lead.score.desc(),
            "created_at": Lead.created_at.desc(),
            "last_contacted_at": Lead.last_contacted_at.desc().nullslast(),
        }
        data_query = data_query.order_by(sort_map.get(sort_by, Lead.score.desc()))
        data_query = data_query.limit(limit).offset(offset)

        leads_result = await self._session.execute(data_query)
        leads = leads_result.scalars().all()

        return leads, total

    async def get_lead_with_relations(self, lead_id: UUID) -> Optional[Lead]:
        """Get lead with eager-loaded activities and emails.

        Args:
            lead_id: Lead UUID

        Returns:
            Lead with populated activities and emails, or None
        """
        result = await self._session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .options(
                selectinload(Lead.activities),
                selectinload(Lead.emails),
            )
        )
        return result.scalar_one_or_none()

    async def get_leads_by_ids(self, lead_ids: list[UUID]) -> Sequence[Lead]:
        """Get multiple leads by their IDs in a single query.

        Args:
            lead_ids: List of Lead UUIDs

        Returns:
            Sequence of found Lead instances
        """
        if not lead_ids:
            return []
        result = await self._session.execute(
            select(Lead).where(Lead.id.in_(lead_ids))
        )
        return result.scalars().all()

    async def get_lead_activities(
        self,
        lead_id: UUID,
        limit: int = 50,
    ) -> Sequence[LeadActivity]:
        """Get activity history for a lead.

        Args:
            lead_id: Lead UUID
            limit: Maximum activities to return

        Returns:
            Activity records ordered by created_at desc
        """
        result = await self._session.execute(
            select(LeadActivity)
            .where(LeadActivity.lead_id == lead_id)
            .order_by(LeadActivity.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_followup_candidates(
        self,
        days_threshold: int = 7,
    ) -> Sequence[Lead]:
        """Find leads that need follow-up.

        Criteria:
        - status = CONTACTED
        - last_contacted_at < now() - days_threshold
        - last_replied_at IS NULL

        Args:
            days_threshold: Days without response before flagging

        Returns:
            Leads needing follow-up, oldest contact first
        """
        cutoff = datetime.now(UTC) - timedelta(days=days_threshold)
        result = await self._session.execute(
            select(Lead)
            .where(
                Lead.status == LeadStatus.CONTACTED.value,
                Lead.last_contacted_at < cutoff,
                Lead.last_replied_at.is_(None),
            )
            .order_by(Lead.last_contacted_at.asc())
        )
        return result.scalars().all()

    async def get_conversion_metrics(self) -> dict:
        """Get conversion metrics.

        Returns:
            Dict with total_leads, converted_count, conversion_rate,
            and per-status counts.
        """
        # Total leads
        total_result = await self._session.execute(
            select(func.count(Lead.id))
        )
        total = total_result.scalar_one()

        # Converted count
        converted_result = await self._session.execute(
            select(func.count(Lead.id))
            .where(Lead.status == LeadStatus.CONVERTED.value)
        )
        converted = converted_result.scalar_one()

        # Per-status counts
        status_result = await self._session.execute(
            select(Lead.status, func.count(Lead.id))
            .group_by(Lead.status)
        )
        status_counts = {s: c for s, c in status_result.all()}

        conversion_rate = (converted / total * 100) if total > 0 else 0.0

        return {
            "total_leads": total,
            "converted_count": converted,
            "conversion_rate": round(conversion_rate, 2),
            "status_counts": status_counts,
        }

    async def get_weekly_trend(self, weeks: int = 8) -> list[dict]:
        """Get weekly new leads and converted counts.

        Args:
            weeks: Number of weeks to look back

        Returns:
            List of dicts with week, new_leads, converted per week
        """
        cutoff = datetime.now(UTC) - timedelta(weeks=weeks)

        # New leads per week
        new_result = await self._session.execute(
            select(
                func.to_char(Lead.created_at, 'IYYY-"W"IW').label("week"),
                func.count(Lead.id).label("count"),
            )
            .where(Lead.created_at >= cutoff)
            .group_by(func.to_char(Lead.created_at, 'IYYY-"W"IW'))
            .order_by(func.to_char(Lead.created_at, 'IYYY-"W"IW'))
        )
        new_by_week = {w: c for w, c in new_result.all()}

        # Converted per week (by converted_at)
        converted_result = await self._session.execute(
            select(
                func.to_char(Lead.converted_at, 'IYYY-"W"IW').label("week"),
                func.count(Lead.id).label("count"),
            )
            .where(
                Lead.converted_at >= cutoff,
                Lead.converted_at.isnot(None),
            )
            .group_by(func.to_char(Lead.converted_at, 'IYYY-"W"IW'))
            .order_by(func.to_char(Lead.converted_at, 'IYYY-"W"IW'))
        )
        converted_by_week = {w: c for w, c in converted_result.all()}

        # Merge into list
        all_weeks = sorted(set(list(new_by_week.keys()) + list(converted_by_week.keys())))
        return [
            {
                "week": w,
                "new_leads": new_by_week.get(w, 0),
                "converted": converted_by_week.get(w, 0),
            }
            for w in all_weeks
        ]

    async def get_avg_time_per_stage(self) -> dict[str, float]:
        """Calculate average days leads spend in each status.

        Uses LeadActivity STATUS_CHANGE entries to calculate
        duration between consecutive status transitions per lead.

        Returns:
            Dict mapping status to average days
        """
        result = await self._session.execute(
            select(LeadActivity)
            .where(LeadActivity.activity_type == ActivityType.STATUS_CHANGE.value)
            .order_by(LeadActivity.lead_id, LeadActivity.created_at)
        )
        activities = result.scalars().all()

        # Group by lead_id, compute time in each old_status
        stage_durations: dict[str, list[float]] = {}
        prev_by_lead: dict[UUID, tuple[str, datetime]] = {}

        for activity in activities:
            meta = activity.activity_metadata or {}
            old_status = meta.get("old_status")
            if not old_status:
                continue

            lead_id = activity.lead_id
            if lead_id in prev_by_lead:
                prev_status, prev_time = prev_by_lead[lead_id]
                if prev_status == old_status:
                    days = (activity.created_at - prev_time).total_seconds() / 86400
                    if old_status not in stage_durations:
                        stage_durations[old_status] = []
                    stage_durations[old_status].append(days)

            prev_by_lead[lead_id] = (
                meta.get("new_status", old_status),
                activity.created_at,
            )

        # Calculate averages
        return {
            status: round(sum(days_list) / len(days_list), 2)
            for status, days_list in stage_durations.items()
            if days_list
        }
