"""Scoring result schemas for research item scoring engine.

Defines the data structures for scoring results:
- ComponentScore: Result from a single scoring component (dataclass for internal use)
- ScoringResult: Combined result from composite scoring (dataclass for internal use)
- ComponentScoreResponse: Pydantic model for API responses
- ScoringResultResponse: Pydantic model for API responses
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import BaseModel, Field


@dataclass
class ComponentScore:
    """Result from a single scoring component.

    Attributes:
        component_name: Name of the scoring component (e.g., "relevance", "recency").
        raw_score: The component's raw score (0-10 scale).
        weighted_score: Score after weight is applied.
        notes: Explanation of how the score was calculated.
    """

    component_name: str
    raw_score: float
    weighted_score: float = 0.0
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate score values."""
        if self.raw_score < 0:
            raise ValueError(f"raw_score must be non-negative, got {self.raw_score}")
        if self.raw_score > 10.0:
            raise ValueError(f"raw_score cannot exceed 10.0, got {self.raw_score}")


@dataclass
class ScoringResult:
    """Combined result from composite scoring.

    Attributes:
        final_score: The final composite score (0-10).
        component_scores: Individual scores from each component.
        reasoning: Human-readable explanation of the scoring.
        scored_at: Timestamp when scoring was performed.
    """

    final_score: float
    component_scores: dict[str, ComponentScore] = field(default_factory=dict)
    reasoning: str = ""
    scored_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate final score."""
        if self.final_score < 0:
            raise ValueError(f"final_score must be non-negative, got {self.final_score}")
        if self.final_score > 10.0:
            raise ValueError(f"final_score cannot exceed 10.0, got {self.final_score}")

    def to_response(self) -> "ScoringResultResponse":
        """Convert to Pydantic response model for API serialization."""
        return ScoringResultResponse(
            final_score=self.final_score,
            component_scores={
                name: ComponentScoreResponse(
                    component_name=score.component_name,
                    raw_score=score.raw_score,
                    weighted_score=score.weighted_score,
                    notes=score.notes,
                )
                for name, score in self.component_scores.items()
            },
            reasoning=self.reasoning,
            scored_at=self.scored_at,
        )


# =============================================================================
# Pydantic API Response Models (Task 8.3)
# =============================================================================


class ComponentScoreResponse(BaseModel):
    """Pydantic model for component score API responses.

    Provides JSON serialization and OpenAPI schema generation.
    """

    component_name: str = Field(..., description="Name of the scoring component")
    raw_score: float = Field(..., ge=0, le=10, description="Raw score (0-10 scale)")
    weighted_score: float = Field(0.0, description="Score after weight applied")
    notes: str = Field("", description="Explanation of score calculation")

    model_config = {"json_schema_extra": {"example": {
        "component_name": "relevance",
        "raw_score": 8.0,
        "weighted_score": 2.0,
        "notes": "Primary: lion's mane; Secondary: cognition, focus"
    }}}


class ScoringResultResponse(BaseModel):
    """Pydantic model for scoring result API responses.

    Provides JSON serialization, validation, and OpenAPI schema generation.
    """

    final_score: float = Field(..., ge=0, le=10, description="Final composite score (0-10)")
    component_scores: dict[str, ComponentScoreResponse] = Field(
        default_factory=dict,
        description="Individual scores from each component"
    )
    reasoning: str = Field("", description="Human-readable explanation of scoring")
    scored_at: datetime = Field(..., description="Timestamp when scoring was performed")

    model_config = {"json_schema_extra": {"example": {
        "final_score": 8.5,
        "component_scores": {
            "relevance": {"component_name": "relevance", "raw_score": 8.0, "weighted_score": 2.0, "notes": "Primary: lion's mane"},
            "recency": {"component_name": "recency", "raw_score": 10.0, "weighted_score": 2.0, "notes": "Created today"}
        },
        "reasoning": "Final score: 8.5/10",
        "scored_at": "2026-02-06T12:00:00Z"
    }}}
