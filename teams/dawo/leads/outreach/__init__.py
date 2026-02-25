"""Outreach Draft Generator module for B2B Sales Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides personalized outreach email generation for qualified B2B leads:
- Lead type classification
- Template selection and personalization
- LLM-powered draft generation
- Brand voice validation
- Approval queue integration

Exports:
    Schemas:
        - OutreachDraft: Generated email draft
        - OutreachTemplate: Email template structure
        - TemplateSelection: Template selection result
        - GenerationResult: Complete generation output
        - GenerationStatus: Generation status enum
        - LeadType: Lead classification types

    Config:
        - OutreachConfig: Outreach service configuration
        - TemplateConfig: Template configuration
        - MIN_CONFIDENCE_THRESHOLD: Minimum confidence for outreach
        - MIN_WORD_COUNT: Minimum draft word count
        - MAX_WORD_COUNT: Maximum draft word count
        - MIN_PERSONALIZATION_TOKENS: Minimum personalization elements
        - DEFAULT_BATCH_SIZE: Default batch processing size
"""

from teams.dawo.leads.outreach.schemas import (
    # Enums
    LeadType,
    GenerationStatus,
    # Dataclasses
    OutreachDraft,
    OutreachTemplate,
    TemplateSelection,
    GenerationResult,
)

from teams.dawo.leads.outreach.config import (
    # Config
    OutreachConfig,
    TemplateConfig,
    # Constants
    MIN_CONFIDENCE_THRESHOLD,
    MIN_WORD_COUNT,
    MAX_WORD_COUNT,
    MIN_PERSONALIZATION_TOKENS,
    DEFAULT_BATCH_SIZE,
)

from teams.dawo.leads.outreach.templates import OutreachTemplateRegistry

from teams.dawo.leads.outreach.classifier import (
    LeadTypeClassifier,
    ClassificationResult,
)

from teams.dawo.leads.outreach.personalization import PersonalizationEngine

from teams.dawo.leads.outreach.generator import OutreachDraftGenerator

from teams.dawo.leads.outreach.validator import (
    OutreachValidator,
    ValidationResult,
    FORBIDDEN_PATTERNS,
)

from teams.dawo.leads.outreach.service import OutreachService

from teams.dawo.leads.outreach.pipeline import OutreachPipeline, PipelineResult

from teams.dawo.leads.outreach.agent import OutreachDraftAgent, AgentResult

from teams.dawo.leads.outreach.approval_integration import OutreachApprovalIntegration


__all__ = [
    # Enums
    "LeadType",
    "GenerationStatus",
    # Dataclasses
    "OutreachDraft",
    "OutreachTemplate",
    "TemplateSelection",
    "GenerationResult",
    # Config
    "OutreachConfig",
    "TemplateConfig",
    # Templates
    "OutreachTemplateRegistry",
    # Classifier
    "LeadTypeClassifier",
    "ClassificationResult",
    # Personalization
    "PersonalizationEngine",
    # Generator
    "OutreachDraftGenerator",
    # Validator
    "OutreachValidator",
    "ValidationResult",
    "FORBIDDEN_PATTERNS",
    # Service
    "OutreachService",
    # Pipeline
    "OutreachPipeline",
    "PipelineResult",
    # Agent
    "OutreachDraftAgent",
    "AgentResult",
    # Approval Integration
    "OutreachApprovalIntegration",
    # Constants
    "MIN_CONFIDENCE_THRESHOLD",
    "MIN_WORD_COUNT",
    "MAX_WORD_COUNT",
    "MIN_PERSONALIZATION_TOKENS",
    "DEFAULT_BATCH_SIZE",
]
