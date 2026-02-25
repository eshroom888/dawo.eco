"""Data schemas for Outreach Draft Generator.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Defines data structures for the outreach pipeline:
- LeadType: Classification types for B2B leads
- OutreachTemplate: Email template structure
- OutreachDraft: Generated email draft
- TemplateSelection: Template selection result
- GenerationResult: Complete generation output
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Optional
from uuid import UUID


class LeadType(str, Enum):
    """Types of B2B leads for template selection.

    Values:
        HEALTH_STORE: Helsekost butikk, natural products store
        GYM_FITNESS: Treningssenter, gym, fitness center
        ONLINE_RETAILER: Nettbutikk, e-commerce
        WELLNESS_CENTER: Spa, wellness, holistic health
        SPECIALTY_GROCER: Specialty food store, gourmet
        GENERIC: Cannot determine specific type (fallback)
    """

    HEALTH_STORE = "health_store"
    GYM_FITNESS = "gym_fitness"
    ONLINE_RETAILER = "online_retailer"
    WELLNESS_CENTER = "wellness_center"
    SPECIALTY_GROCER = "specialty_grocer"
    GENERIC = "generic"


class GenerationStatus(str, Enum):
    """Status of outreach draft generation.

    Values:
        SUCCESS: Draft generated successfully
        FAILED: Generation failed
        SKIPPED: Lead skipped (not qualified, already has draft, etc.)
        VALIDATION_FAILED: Draft failed brand voice validation
    """

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class OutreachTemplate:
    """Email template for outreach generation.

    Templates are selected based on lead type and contain placeholders
    for personalization.

    Attributes:
        template_id: Unique template identifier
        lead_type: Type of lead this template is designed for
        subject_template: Email subject with placeholders
        body_template: Email body with placeholders
        cta_type: Type of call-to-action (meeting_request, sample_offer, catalog_request)
    """

    template_id: str
    lead_type: LeadType
    subject_template: str
    body_template: str
    cta_type: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage.

        Returns:
            Dict representation of the template.
        """
        return {
            "template_id": self.template_id,
            "lead_type": self.lead_type.value,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
            "cta_type": self.cta_type,
        }


@dataclass
class OutreachDraft:
    """Generated outreach email draft.

    Represents a personalized email draft ready for approval.

    Attributes:
        lead_id: UUID of the lead this draft is for
        template_id: Template used for generation
        template_type: Lead type classification
        subject: Email subject line
        body: Email body text (Norwegian)
        word_count: Number of words in body (should be 150-250)
        personalization_hooks: List of personalization elements used
        personalization_score: Number of personalization tokens used
        suggested_send_time: Recommended send time (business hours)
        generated_at: When draft was generated
    """

    lead_id: UUID
    template_id: str
    template_type: LeadType
    subject: str
    body: str
    word_count: int
    personalization_hooks: list[str]
    personalization_score: int
    suggested_send_time: datetime
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSONB storage.

        Returns:
            Dict matching the outreach_data schema in Lead model.
        """
        return {
            "generated_at": self.generated_at.isoformat(),
            "template_type": self.template_type.value,
            "template_id": self.template_id,
            "draft": {
                "subject": self.subject,
                "body": self.body,
                "word_count": self.word_count,
            },
            "personalization": {
                "hooks_used": self.personalization_hooks,
                "personalization_score": self.personalization_score,
            },
            "suggested_send_time": self.suggested_send_time.isoformat(),
        }


@dataclass
class TemplateSelection:
    """Result of template selection for a lead.

    Tracks which template was selected and why.

    Attributes:
        lead_id: UUID of the lead
        template_id: Selected template ID
        lead_type: Classified lead type
        classification_confidence: Confidence in classification (0-1)
        classification_reasoning: Explanation for classification
        selected_at: When selection was made
    """

    lead_id: UUID
    template_id: str
    lead_type: LeadType
    classification_confidence: float
    classification_reasoning: str
    selected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage.

        Returns:
            Dict representation of the selection.
        """
        return {
            "lead_id": str(self.lead_id),
            "template_id": self.template_id,
            "lead_type": self.lead_type.value,
            "classification_confidence": self.classification_confidence,
            "classification_reasoning": self.classification_reasoning,
            "selected_at": self.selected_at.isoformat(),
        }


@dataclass
class GenerationResult:
    """Complete result of outreach draft generation.

    Aggregates the generation result for a single lead.

    Attributes:
        lead_id: UUID of the lead
        status: Generation status (success, failed, skipped, validation_failed)
        draft: Generated draft (if successful)
        template_selection: Template selection details
        validation_result: Brand voice validation result
        error: Error message (if failed)
        processed_at: When generation was processed
    """

    lead_id: UUID
    status: GenerationStatus
    draft: Optional[OutreachDraft] = None
    template_selection: Optional[TemplateSelection] = None
    validation_result: Optional[dict] = None
    error: Optional[str] = None
    processed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage.

        Returns:
            Dict representation of the result.
        """
        result = {
            "lead_id": str(self.lead_id),
            "status": self.status.value,
            "processed_at": self.processed_at.isoformat(),
        }

        if self.draft:
            result["draft"] = self.draft.to_dict()

        if self.template_selection:
            result["template_selection"] = self.template_selection.to_dict()

        if self.validation_result:
            result["validation_result"] = self.validation_result

        if self.error:
            result["error"] = self.error

        return result
