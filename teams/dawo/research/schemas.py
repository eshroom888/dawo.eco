"""Pydantic schemas for Research Pool API.

Provides data validation schemas for creating and updating research items.
Uses Pydantic v2 for validation and serialization.

Schemas:
    - ResearchItemCreate: Schema for creating new research items
    - ResearchItemUpdate: Schema for partial updates to research items
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

import re

from pydantic import BaseModel, Field, field_validator

from .models import ResearchSource, ComplianceStatus, MAX_SCORE, MIN_SCORE


# URL validation pattern - must start with http:// or https://
URL_PATTERN = re.compile(r"^https?://\S+$")


class ResearchItemCreate(BaseModel):
    """Schema for creating a new research item.

    All required fields must be provided. Optional fields have defaults.
    """

    id: Optional[UUID] = Field(
        default=None,
        description="Optional UUID; generated if not provided",
    )
    source: ResearchSource = Field(
        ...,
        description="Source of the research item",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Title or headline of the research",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Full content or transcript excerpt",
    )
    url: str = Field(
        ...,
        max_length=2048,
        description="Source URL for reference",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Topic/theme tags for categorization",
    )
    source_metadata: dict = Field(
        default_factory=dict,
        description="Source-specific metadata",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Discovery timestamp; defaults to now",
    )
    score: float = Field(
        default=0.0,
        ge=MIN_SCORE,
        le=MAX_SCORE,
        description="Content potential score (0-10)",
    )
    compliance_status: ComplianceStatus = Field(
        default=ComplianceStatus.COMPLIANT,
        description="EU compliance check result",
    )

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        """Ensure tags is a list of strings."""
        if v is None:
            return []
        if isinstance(v, list):
            return [str(tag) for tag in v]
        return [str(v)]

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format - must start with http:// or https://."""
        if not URL_PATTERN.match(v):
            raise ValueError("URL must start with http:// or https://")
        return v

    model_config = {
        "from_attributes": True,
    }


class ResearchItemUpdate(BaseModel):
    """Schema for updating an existing research item.

    All fields are optional - only provided fields will be updated.
    """

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
    )
    content: Optional[str] = Field(
        default=None,
        min_length=1,
    )
    url: Optional[str] = Field(
        default=None,
        max_length=2048,
    )
    tags: Optional[list[str]] = Field(
        default=None,
    )
    source_metadata: Optional[dict] = Field(
        default=None,
    )
    score: Optional[float] = Field(
        default=None,
        ge=MIN_SCORE,
        le=MAX_SCORE,
    )
    compliance_status: Optional[ComplianceStatus] = Field(
        default=None,
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided - must start with http:// or https://."""
        if v is not None and not URL_PATTERN.match(v):
            raise ValueError("URL must start with http:// or https://")
        return v

    model_config = {
        "from_attributes": True,
    }
