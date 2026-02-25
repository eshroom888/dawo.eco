"""Health Claims relevance filter.

Epic 6, Story 6-1, Task 6: Relevance filter.

Filters EU Health Claims for substances relevant to DAWO products
(mushrooms, adaptogens, vitamins/minerals).
"""

import logging
from typing import Optional

import pandas as pd

from teams.dawo.scanners.health_claims.schemas import FilterStats

logger = logging.getLogger(__name__)


class RelevanceFilter:
    """Filter EU Health Claims for DAWO-relevant substances.

    Story 6-1, Task 6: Keyword-based relevance filtering.

    Matches claims against configured keyword lists (case-insensitive)
    across substance, claim_text, and conditions_of_use columns.

    Attributes:
        _mushroom_keywords: Mushroom substance keywords
        _adaptogen_keywords: Adaptogen substance keywords
        _vitamin_mineral_keywords: Vitamin/mineral keywords
    """

    def __init__(
        self,
        mushroom_keywords: tuple[str, ...] = (),
        adaptogen_keywords: tuple[str, ...] = (),
        vitamin_mineral_keywords: tuple[str, ...] = (),
    ) -> None:
        """Initialize relevance filter.

        Args:
            mushroom_keywords: Keywords for mushroom matching
            adaptogen_keywords: Keywords for adaptogen matching
            vitamin_mineral_keywords: Keywords for vitamin/mineral matching
        """
        self._mushroom_keywords = mushroom_keywords
        self._adaptogen_keywords = adaptogen_keywords
        self._vitamin_mineral_keywords = vitamin_mineral_keywords

    def filter(self, df: pd.DataFrame) -> tuple[pd.DataFrame, FilterStats]:
        """Filter DataFrame for relevant claims.

        Args:
            df: DataFrame with health claims data

        Returns:
            Tuple of (filtered DataFrame with is_relevant and relevance_category columns,
                      FilterStats with match statistics)
        """
        if df.empty:
            return df, FilterStats()

        # Create a copy to avoid modifying original
        df = df.copy()
        df["is_relevant"] = False
        df["relevance_category"] = None

        stats = FilterStats(total_claims=len(df))

        # Build searchable text from multiple columns (case-insensitive)
        search_cols = ["substance", "claim_text", "conditions_of_use"]
        df["_search_text"] = ""
        for col in search_cols:
            if col in df.columns:
                df["_search_text"] = df["_search_text"] + " " + df[col].fillna("").astype(str).str.lower()

        # Match each keyword category
        mushroom_mask = self._match_keywords(df["_search_text"], self._mushroom_keywords)
        adaptogen_mask = self._match_keywords(df["_search_text"], self._adaptogen_keywords)
        vitamin_mask = self._match_keywords(df["_search_text"], self._vitamin_mineral_keywords)

        # Apply categories (priority: mushroom > adaptogen > vitamin_mineral)
        df.loc[vitamin_mask, "is_relevant"] = True
        df.loc[vitamin_mask, "relevance_category"] = "vitamin_mineral"
        stats.vitamin_mineral_matches = int(vitamin_mask.sum())

        df.loc[adaptogen_mask, "is_relevant"] = True
        df.loc[adaptogen_mask, "relevance_category"] = "adaptogen"
        stats.adaptogen_matches = int(adaptogen_mask.sum())

        df.loc[mushroom_mask, "is_relevant"] = True
        df.loc[mushroom_mask, "relevance_category"] = "mushroom"
        stats.mushroom_matches = int(mushroom_mask.sum())

        # Clean up temp column
        df = df.drop(columns=["_search_text"])

        relevant = df[df["is_relevant"]].copy()
        stats.relevant_claims = len(relevant)

        logger.info(
            "Relevance filter: %d/%d relevant (mushroom=%d, adaptogen=%d, vitamin=%d)",
            stats.relevant_claims,
            stats.total_claims,
            stats.mushroom_matches,
            stats.adaptogen_matches,
            stats.vitamin_mineral_matches,
        )

        return df, stats

    def _match_keywords(
        self, search_text: pd.Series, keywords: tuple[str, ...]
    ) -> pd.Series:
        """Match keywords against search text.

        Args:
            search_text: Lowercased concatenated search text
            keywords: Keywords to match

        Returns:
            Boolean Series indicating matches
        """
        if not keywords:
            return pd.Series(False, index=search_text.index)

        mask = pd.Series(False, index=search_text.index)
        for keyword in keywords:
            mask = mask | search_text.str.contains(keyword.lower(), na=False, regex=False)
        return mask


__all__ = [
    "RelevanceFilter",
]
