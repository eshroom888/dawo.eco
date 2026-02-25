"""Health Claims change detector.

Epic 6, Story 6-1, Task 7: Change detector.

Detects differences between two register snapshots using pandas merge/compare.
"""

import logging
from typing import Optional

import pandas as pd

from core.regulatory.models import ChangeType, ChangeSeverity
from teams.dawo.scanners.health_claims.parser import TRACKED_COLUMNS
from teams.dawo.scanners.health_claims.schemas import ClaimChangeRecord

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Detect changes between EU Health Claims Register snapshots.

    Story 6-1, Task 7: DataFrame diff using pandas merge.

    Uses pandas merge with outer join to identify NEW, REMOVED, MODIFIED,
    and STATUS_CHANGED claims between two snapshots. Assigns severity
    based on relevance and change type.

    Attributes:
        _relevant_keywords: Combined keyword set for severity escalation
    """

    def __init__(
        self,
        mushroom_keywords: tuple[str, ...] = (),
        adaptogen_keywords: tuple[str, ...] = (),
        vitamin_mineral_keywords: tuple[str, ...] = (),
    ) -> None:
        """Initialize change detector.

        Args:
            mushroom_keywords: Keywords for mushroom substance matching
            adaptogen_keywords: Keywords for adaptogen substance matching
            vitamin_mineral_keywords: Keywords for vitamin/mineral matching
        """
        self._relevant_keywords = set()
        for kw in mushroom_keywords:
            self._relevant_keywords.add(kw.lower())
        for kw in adaptogen_keywords:
            self._relevant_keywords.add(kw.lower())
        for kw in vitamin_mineral_keywords:
            self._relevant_keywords.add(kw.lower())

    def detect(
        self,
        previous: pd.DataFrame,
        current: pd.DataFrame,
    ) -> list[ClaimChangeRecord]:
        """Detect changes between two register snapshots.

        Args:
            previous: Previous snapshot DataFrame (may be empty for first run)
            current: Current snapshot DataFrame

        Returns:
            List of detected changes
        """
        changes: list[ClaimChangeRecord] = []

        if previous.empty and current.empty:
            return changes

        # First run — no previous snapshot
        if previous.empty:
            logger.info("First run: %d claims in baseline, no changes detected", len(current))
            return changes

        # Ensure claim_id is string for consistent comparison
        prev = previous.copy()
        curr = current.copy()
        prev["claim_id"] = prev["claim_id"].astype(str)
        curr["claim_id"] = curr["claim_id"].astype(str)

        # Outer merge to find new, removed, and common claims
        merged = curr.merge(
            prev,
            on="claim_id",
            how="outer",
            indicator=True,
            suffixes=("_curr", "_prev"),
        )

        # NEW claims (in current only)
        new_claims = merged[merged["_merge"] == "left_only"]
        for _, row in new_claims.iterrows():
            claim_id = str(row["claim_id"])
            substance = str(row.get("substance_curr", ""))
            claim_text = str(row.get("claim_text_curr", "")) if pd.notna(row.get("claim_text_curr")) else ""
            cond_use = str(row.get("conditions_of_use_curr", "")) if pd.notna(row.get("conditions_of_use_curr")) else ""
            is_relevant = self._is_relevant(substance, claim_text, cond_use)
            changes.append(ClaimChangeRecord(
                claim_id=claim_id,
                change_type=ChangeType.NEW.value,
                new_value=substance,
                is_relevant=is_relevant,
                severity=ChangeSeverity.HIGH.value if is_relevant else ChangeSeverity.LOW.value,
            ))

        # REMOVED claims (in previous only)
        removed_claims = merged[merged["_merge"] == "right_only"]
        for _, row in removed_claims.iterrows():
            claim_id = str(row["claim_id"])
            substance = str(row.get("substance_prev", ""))
            claim_text = str(row.get("claim_text_prev", "")) if pd.notna(row.get("claim_text_prev")) else ""
            cond_use = str(row.get("conditions_of_use_prev", "")) if pd.notna(row.get("conditions_of_use_prev")) else ""
            is_relevant = self._is_relevant(substance, claim_text, cond_use)
            changes.append(ClaimChangeRecord(
                claim_id=claim_id,
                change_type=ChangeType.REMOVED.value,
                old_value=substance,
                is_relevant=is_relevant,
                severity=ChangeSeverity.MEDIUM.value if is_relevant else ChangeSeverity.LOW.value,
            ))

        # MODIFIED / STATUS_CHANGED (in both)
        common = merged[merged["_merge"] == "both"]
        for _, row in common.iterrows():
            claim_id = str(row["claim_id"])
            substance = str(row.get("substance_curr", ""))
            claim_text = str(row.get("claim_text_curr", "")) if pd.notna(row.get("claim_text_curr")) else ""
            cond_use = str(row.get("conditions_of_use_curr", "")) if pd.notna(row.get("conditions_of_use_curr")) else ""
            is_relevant = self._is_relevant(substance, claim_text, cond_use)

            for col in TRACKED_COLUMNS:
                if col == "claim_id":
                    continue

                curr_col = f"{col}_curr"
                prev_col = f"{col}_prev"

                if curr_col not in row.index or prev_col not in row.index:
                    continue

                curr_val = str(row[curr_col]) if pd.notna(row[curr_col]) else ""
                prev_val = str(row[prev_col]) if pd.notna(row[prev_col]) else ""

                if curr_val != prev_val:
                    # Status change is special — elevated severity
                    if col == "status":
                        changes.append(ClaimChangeRecord(
                            claim_id=claim_id,
                            change_type=ChangeType.STATUS_CHANGED.value,
                            field_changed=col,
                            old_value=prev_val,
                            new_value=curr_val,
                            is_relevant=is_relevant,
                            severity=ChangeSeverity.CRITICAL.value if is_relevant else ChangeSeverity.MEDIUM.value,
                        ))
                    else:
                        changes.append(ClaimChangeRecord(
                            claim_id=claim_id,
                            change_type=ChangeType.MODIFIED.value,
                            field_changed=col,
                            old_value=prev_val,
                            new_value=curr_val,
                            is_relevant=is_relevant,
                            severity=ChangeSeverity.MEDIUM.value if is_relevant else ChangeSeverity.LOW.value,
                        ))

        logger.info(
            "Change detection: %d changes found (%d new, %d removed, %d modified/status)",
            len(changes),
            len(new_claims),
            len(removed_claims),
            len(changes) - len(new_claims) - len(removed_claims),
        )

        return changes

    def _is_relevant(self, substance: str, claim_text: str = "", conditions_of_use: str = "") -> bool:
        """Check if claim matches any relevant keyword.

        Searches substance, claim_text, and conditions_of_use (matching
        RelevanceFilter's multi-column search behavior).

        Args:
            substance: Substance name to check
            claim_text: Full claim wording
            conditions_of_use: Usage conditions

        Returns:
            True if any field contains a relevant keyword
        """
        if not self._relevant_keywords:
            return False
        search_text = f"{substance} {claim_text} {conditions_of_use}".lower()
        return any(kw in search_text for kw in self._relevant_keywords)


__all__ = [
    "ChangeDetector",
]
