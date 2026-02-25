"""Novel Food Catalogue change detector.

Epic 6, Story 6-2, Task 6: Change detector.

Detects changes between two sets of catalogue entries by comparing
them using composite key (species_latin, entry_name).
"""

import logging
from typing import Optional

from teams.dawo.scanners.novel_food.config import SpeciesConfig
from teams.dawo.scanners.novel_food.schemas import (
    NovelFoodEntryRecord,
    CatalogueChangeRecord,
)

logger = logging.getLogger(__name__)

# Fields to track for changes and their severity mapping
# (field_name, default_severity, dawo_product_severity)
SEVERITY_MAP: dict[str, tuple[str, str]] = {
    "novel_food_status": ("high", "critical"),
    "authorization_status": ("high", "critical"),
    "conditions_of_use": ("medium", "medium"),
    "regulation_reference": ("medium", "medium"),
    "union_list_entry": ("medium", "high"),
    "member_state_comments": ("low", "low"),
    "commission_comments": ("low", "low"),
    "history_of_consumption": ("low", "medium"),
}

# Fields that constitute a "status change" (special change_type)
STATUS_FIELDS = {"novel_food_status", "authorization_status"}

# Fields to compare for modifications
TRACKED_FIELDS = tuple(SEVERITY_MAP.keys())


def _make_key(entry: NovelFoodEntryRecord) -> tuple[str, str]:
    """Create composite key for entry matching."""
    return (entry.species_latin.lower().strip(), entry.entry_name.lower().strip())


class NovelFoodChangeDetector:
    """Detects changes between Novel Food Catalogue snapshots.

    Story 6-2, Task 6: Entry-level diff using composite key.

    Matches entries by (species_latin, entry_name) and detects:
    - NEW entries (in current, not in previous)
    - REMOVED entries (in previous, not in current)
    - MODIFIED entries (field-level changes)
    - STATUS_CHANGED (novel_food_status or authorization_status changed)

    Assigns severity based on field and whether species is a DAWO product.

    Attributes:
        _dawo_species: Set of latin names for DAWO products (lowercase)
    """

    def __init__(self, species_config: tuple[SpeciesConfig, ...]) -> None:
        """Initialize change detector.

        Args:
            species_config: Species configuration for DAWO product lookup
        """
        self._dawo_species: set[str] = {
            s.latin_name.lower().strip()
            for s in species_config
            if s.is_dawo_product
        }

    def detect(
        self,
        previous: list[NovelFoodEntryRecord],
        current: list[NovelFoodEntryRecord],
    ) -> list[CatalogueChangeRecord]:
        """Detect changes between two entry lists.

        Args:
            previous: Entries from previous snapshot
            current: Entries from current snapshot

        Returns:
            List of detected changes. Empty list for first run (empty previous).
        """
        # First run: no previous data, return empty (baseline, no changes to report)
        if not previous:
            return []

        prev_map = {_make_key(e): e for e in previous}
        curr_map = {_make_key(e): e for e in current}

        prev_keys = set(prev_map.keys())
        curr_keys = set(curr_map.keys())

        new_keys = curr_keys - prev_keys
        removed_keys = prev_keys - curr_keys
        common_keys = prev_keys & curr_keys

        changes: list[CatalogueChangeRecord] = []

        # Detect NEW entries
        for key in new_keys:
            entry = curr_map[key]
            is_dawo = entry.species_latin.lower().strip() in self._dawo_species
            changes.append(CatalogueChangeRecord(
                species_latin=entry.species_latin,
                entry_name=entry.entry_name,
                change_type="new",
                new_value=entry.novel_food_status,
                severity="high" if is_dawo else "medium",
            ))

        # Detect REMOVED entries
        for key in removed_keys:
            entry = prev_map[key]
            is_dawo = entry.species_latin.lower().strip() in self._dawo_species
            changes.append(CatalogueChangeRecord(
                species_latin=entry.species_latin,
                entry_name=entry.entry_name,
                change_type="removed",
                old_value=entry.novel_food_status,
                severity="high" if is_dawo else "medium",
            ))

        # Detect MODIFIED/STATUS_CHANGED entries
        for key in common_keys:
            prev_entry = prev_map[key]
            curr_entry = curr_map[key]
            is_dawo = curr_entry.species_latin.lower().strip() in self._dawo_species

            for field in TRACKED_FIELDS:
                old_val = getattr(prev_entry, field, "")
                new_val = getattr(curr_entry, field, "")

                if old_val != new_val:
                    default_sev, dawo_sev = SEVERITY_MAP[field]
                    severity = dawo_sev if is_dawo else default_sev

                    change_type = (
                        "status_changed" if field in STATUS_FIELDS else "modified"
                    )

                    changes.append(CatalogueChangeRecord(
                        species_latin=curr_entry.species_latin,
                        entry_name=curr_entry.entry_name,
                        change_type=change_type,
                        field_changed=field,
                        old_value=old_val,
                        new_value=new_val,
                        severity=severity,
                    ))

        logger.info(
            "Change detection: %d new, %d removed, %d modified/status_changed",
            len(new_keys),
            len(removed_keys),
            len(changes) - len(new_keys) - len(removed_keys),
        )

        return changes


__all__ = [
    "NovelFoodChangeDetector",
    "SEVERITY_MAP",
    "TRACKED_FIELDS",
]
