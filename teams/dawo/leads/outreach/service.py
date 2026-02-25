"""Outreach Service for B2B Sales Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides orchestration for outreach generation:
- OutreachService: Main service coordinating all components

Accepts all dependencies via constructor injection.
NEVER loads config files directly.
"""

import logging
from typing import Any, Protocol

from teams.dawo.leads.outreach.schemas import (
    LeadType,
    OutreachDraft,
    OutreachTemplate,
    GenerationResult,
    GenerationStatus,
)
from teams.dawo.leads.outreach.config import MIN_CONFIDENCE_THRESHOLD


logger = logging.getLogger(__name__)


class LeadTypeClassifierProtocol(Protocol):
    """Protocol for lead type classifier."""

    async def classify(self, lead_id: Any, enrichment_data: dict) -> Any:
        """Classify a lead into a type."""
        ...


class OutreachTemplateRegistryProtocol(Protocol):
    """Protocol for template registry."""

    def get_template(self, lead_type: LeadType) -> OutreachTemplate:
        """Get template for lead type."""
        ...

    def log_template_selection(self, template_id: str, lead_id: Any) -> None:
        """Log template selection."""
        ...


class OutreachDraftGeneratorProtocol(Protocol):
    """Protocol for draft generator."""

    async def generate(
        self,
        lead_id: Any,
        contact_name: str,
        company: str,
        enrichment_data: dict,
        lead_type: LeadType,
    ) -> OutreachDraft:
        """Generate outreach draft."""
        ...


class OutreachValidatorProtocol(Protocol):
    """Protocol for outreach validator."""

    async def validate(self, draft: OutreachDraft) -> Any:
        """Validate outreach draft."""
        ...


class OutreachService:
    """Service for orchestrating outreach generation.

    Coordinates classification, template selection, draft generation,
    and validation for B2B outreach emails.

    Accepts all dependencies via constructor injection.
    NEVER loads config files directly.

    Attributes:
        _classifier: Lead type classifier
        _template_registry: Template registry
        _generator: Draft generator
        _validator: Outreach validator
    """

    def __init__(
        self,
        classifier: LeadTypeClassifierProtocol,
        template_registry: OutreachTemplateRegistryProtocol,
        generator: OutreachDraftGeneratorProtocol,
        validator: OutreachValidatorProtocol,
    ) -> None:
        """Initialize OutreachService with dependencies.

        Args:
            classifier: Lead type classifier
            template_registry: Template registry for outreach emails
            generator: Draft generator for personalized emails
            validator: Validator for brand voice compliance
        """
        self._classifier = classifier
        self._template_registry = template_registry
        self._generator = generator
        self._validator = validator

    async def generate_outreach(self, lead: Any) -> GenerationResult:
        """Generate personalized outreach for a lead.

        Orchestrates the full outreach generation process:
        1. Classify lead type
        2. Select appropriate template
        3. Generate personalized draft
        4. Validate against brand voice

        Args:
            lead: Lead object to generate outreach for

        Returns:
            GenerationResult with draft or error information
        """
        # Track current step for error reporting
        current_step = "classification"

        try:
            # Extract enrichment data for classification
            enrichment_data = getattr(lead, "enrichment_data", {}) or {}

            # Step 1: Classify lead type
            classification = await self._classifier.classify(
                lead_id=lead.id,
                enrichment_data=enrichment_data,
            )
            lead_type = classification.lead_type

            # Step 2: Select template
            current_step = "template_selection"
            template = self._template_registry.get_template(lead_type)
            self._template_registry.log_template_selection(template.template_id, lead.id)

            # Step 3: Generate draft
            current_step = "generation"
            # Extract fields from lead for generator
            contact_name = getattr(lead, "first_name", "")
            company = getattr(lead, "company", "")

            draft = await self._generator.generate(
                lead_id=lead.id,
                contact_name=contact_name,
                company=company,
                enrichment_data=enrichment_data,
                lead_type=lead_type,
            )

            # Step 4: Validate draft
            current_step = "validation"
            validation_result = await self._validator.validate(draft)

            if not validation_result.is_valid:
                logger.warning(
                    "Outreach draft validation failed",
                    extra={
                        "lead_id": str(lead.id),
                        "issues": validation_result.issues,
                    }
                )
                return GenerationResult(
                    lead_id=lead.id,
                    status=GenerationStatus.VALIDATION_FAILED,
                    draft=draft,
                    template_selection=None,
                    error=f"Validation failed: {', '.join(validation_result.issues)}",
                )

            logger.info(
                "Outreach draft generated successfully",
                extra={
                    "lead_id": str(lead.id),
                    "template_id": template.template_id,
                    "word_count": draft.word_count,
                }
            )

            return GenerationResult(
                lead_id=lead.id,
                status=GenerationStatus.SUCCESS,
                draft=draft,
                template_selection=None,
            )

        except Exception as e:
            logger.exception(
                f"Outreach {current_step} failed",
                extra={"lead_id": str(lead.id)},
            )
            return GenerationResult(
                lead_id=lead.id,
                status=GenerationStatus.FAILED,
                draft=None,
                template_selection=None,
                error=f"Outreach {current_step} failed: {str(e)}",
            )

    def prepare_for_approval(self, draft: OutreachDraft, lead: Any) -> dict:
        """Prepare outreach draft for approval queue.

        Creates approval queue data including:
        - Lead summary
        - Personalization used
        - Suggested send time

        Args:
            draft: Generated outreach draft
            lead: Lead object

        Returns:
            Dict containing approval queue data
        """
        return {
            "lead_summary": {
                "lead_id": str(lead.id),
                "company": lead.company,
                "contact_name": getattr(lead, "contact_name", None),
            },
            "personalization": {
                "hooks_used": draft.personalization_hooks,
                "personalization_score": draft.personalization_score,
            },
            "template_type": draft.template_type.value,
            "suggested_send_time": draft.suggested_send_time.isoformat() if draft.suggested_send_time else None,
            "draft": {
                "subject": draft.subject,
                "body": draft.body,
                "word_count": draft.word_count,
            },
        }

    def is_qualified_for_outreach(self, lead: Any) -> bool:
        """Check if lead is qualified for outreach.

        Verifies lead meets minimum confidence threshold.

        Args:
            lead: Lead object to check

        Returns:
            True if lead is qualified for outreach
        """
        confidence = getattr(lead, "confidence_score", 0)
        return confidence >= MIN_CONFIDENCE_THRESHOLD
