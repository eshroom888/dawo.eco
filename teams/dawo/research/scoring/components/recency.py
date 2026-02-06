"""Recency scoring component for research items.

Calculates recency score based on time decay:
- Formula: 10 * (1 - days_old / decay_days)
- Items from today score 10
- Items at decay threshold score 0
- Items older than decay threshold score 0 (capped at minimum)

Default decay period is 30 days.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..schemas import ComponentScore

logger = logging.getLogger(__name__)

# Scoring constants
RECENCY_DECAY_DAYS: int = 30
MAX_RECENCY_SCORE: float = 10.0
MIN_RECENCY_SCORE: float = 0.0


@dataclass
class RecencyConfig:
    """Configuration for recency scoring.

    Attributes:
        decay_days: Number of days for full decay (default 30).
    """

    decay_days: int = RECENCY_DECAY_DAYS


class RecencyScorer:
    """Scores research items based on recency.

    Uses linear decay formula: 10 * (1 - days_old / decay_days)
    - Items from today score 10
    - Items at decay threshold (default 30 days) score 0
    - Older items also score 0 (capped at minimum)

    Attributes:
        _config: RecencyConfig with decay settings.
    """

    def __init__(self, config: RecencyConfig) -> None:
        """Initialize with configuration.

        Args:
            config: RecencyConfig with decay settings.
        """
        self._config = config

    def score(self, item: dict[str, Any]) -> ComponentScore:
        """Calculate recency score for a research item.

        Args:
            item: Dictionary with 'created_at' field (datetime).

        Returns:
            ComponentScore with recency score (0-10).
        """
        created_at = item.get("created_at")

        if created_at is None:
            logger.warning("Item missing created_at, defaulting to score 5")
            return ComponentScore(
                component_name="recency",
                raw_score=5.0,
                notes="Missing created_at timestamp",
            )

        # Calculate days since creation
        now = datetime.now(timezone.utc)

        # Handle timezone-naive datetimes
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        delta = now - created_at
        days_old = delta.total_seconds() / (24 * 60 * 60)

        # Apply decay formula
        decay_factor = 1 - (days_old / self._config.decay_days)
        raw_score = MAX_RECENCY_SCORE * decay_factor

        # Clamp to valid range
        raw_score = max(MIN_RECENCY_SCORE, min(MAX_RECENCY_SCORE, raw_score))

        # Round to 2 decimal places for cleaner output
        raw_score = round(raw_score, 2)

        # Build notes
        days_old_int = int(days_old)
        if days_old < 1:
            notes = "Created today (max recency)"
        elif days_old >= self._config.decay_days:
            notes = f"Created {days_old_int} days ago (beyond {self._config.decay_days}-day window)"
        else:
            notes = f"Created {days_old_int} days ago"

        logger.debug(f"Recency score: {raw_score} (days old: {days_old:.1f})")

        return ComponentScore(
            component_name="recency",
            raw_score=raw_score,
            notes=notes,
        )
