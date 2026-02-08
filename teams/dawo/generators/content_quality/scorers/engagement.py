"""Engagement Prediction Scorer - Historical engagement prediction.

Scores predicted engagement based on content characteristics
and historical performance data.
"""

from dataclasses import dataclass
from typing import Protocol, Optional

from teams.dawo.generators.content_quality.schemas import (
    ComponentScore,
    EngagementPrediction,
)


class HistoricalDataProviderProtocol(Protocol):
    """Protocol for historical engagement data provider.

    Future integration point for historical data lookups.
    """

    async def get_similar_content_performance(
        self,
        content_type: str,
        source_type: str,
        hashtags: list[str],
    ) -> Optional[dict]:
        """Get performance data for similar historical content.

        Args:
            content_type: Type of content (feed, story, reel)
            source_type: Content source type
            hashtags: Content hashtags for similarity matching

        Returns:
            Dict with avg_score, data_points, or None if insufficient data
        """
        ...


@dataclass
class EngagementScorerConfig:
    """Configuration for engagement prediction scoring.

    Attributes:
        weight: Weight of engagement in total score (default 0.15)
        default_score: Default score when no historical data (default 5.0)
    """

    weight: float = 0.15
    default_score: float = 5.0


# Base scores by source type (content origin affects engagement)
SOURCE_TYPE_SCORES = {
    "trending": 8.0,    # Trending topics perform well
    "research": 7.5,    # Research-backed content performs well
    "scheduled": 6.5,   # Scheduled evergreen content
    "evergreen": 5.5,   # General evergreen content
}


class EngagementPredictionScorer:
    """Predicts engagement based on content characteristics.

    Uses source type scoring as baseline, with optional historical
    data integration for improved predictions.

    Attributes:
        config: Scorer configuration
        historical_provider: Optional provider for historical data
    """

    def __init__(
        self,
        config: Optional[EngagementScorerConfig] = None,
        historical_provider: Optional[HistoricalDataProviderProtocol] = None,
    ) -> None:
        """Initialize with optional configuration and data provider.

        Args:
            config: Optional scorer configuration
            historical_provider: Optional historical data provider for
                improved predictions (future integration)
        """
        self._config = config or EngagementScorerConfig()
        self._historical_provider = historical_provider

    async def score(
        self,
        source_type: str,
        content_type: Optional[str] = None,
        hashtags: Optional[list[str]] = None,
    ) -> ComponentScore:
        """Score predicted engagement.

        Predicts engagement based on content characteristics.
        Falls back to source-type scoring when no historical data.

        Args:
            source_type: Content source type (trending, research, etc.)
            content_type: Optional content type for historical lookup
            hashtags: Optional hashtags for historical lookup

        Returns:
            ComponentScore with engagement prediction details
        """
        predicted_score = SOURCE_TYPE_SCORES.get(
            source_type,
            self._config.default_score,
        )
        confidence = 0.5  # Low confidence without historical data
        similar_content_avg = None
        data_points = 0

        # Future: Use historical provider for better predictions
        if self._historical_provider is not None and content_type and hashtags:
            historical_data = await self._historical_provider.get_similar_content_performance(
                content_type=content_type,
                source_type=source_type,
                hashtags=hashtags,
            )
            if historical_data:
                similar_content_avg = historical_data.get("avg_score")
                data_points = historical_data.get("data_points", 0)

                # Blend source score with historical data
                if data_points >= 5:
                    predicted_score = (predicted_score * 0.3) + (similar_content_avg * 0.7)
                    confidence = min(0.9, 0.5 + (data_points / 100))

        prediction = EngagementPrediction(
            predicted_score=predicted_score,
            confidence=confidence,
            similar_content_avg=similar_content_avg,
            data_points=data_points,
        )

        return ComponentScore(
            component="engagement",
            raw_score=predicted_score,
            weight=self._config.weight,
            weighted_score=predicted_score * self._config.weight,
            details={
                "prediction": prediction,
                "source_type": source_type,
            },
        )
