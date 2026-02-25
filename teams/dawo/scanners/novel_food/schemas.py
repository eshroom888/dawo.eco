"""Novel Food Catalogue Monitor data transfer objects.

Epic 6, Story 6-2: Novel Food Catalogue Monitor.

Dataclasses for passing data between pipeline stages.
These are NOT SQLAlchemy models — they are plain data containers.

Reuses MonitorStatus and MonitorResult from health_claims schemas.
"""

from dataclasses import dataclass
from typing import Optional

from teams.dawo.scanners.health_claims.schemas import MonitorStatus, MonitorResult


@dataclass
class NovelFoodEntryRecord:
    """DTO for a parsed Novel Food Catalogue entry.

    Passed between parser, change detector, and repository.
    NOT a SQLAlchemy model.

    Attributes:
        species_latin: Latin species name (e.g., "Hericium erinaceus")
        species_common: Common name (e.g., "Lion's Mane")
        entry_name: Catalogue entry name
        novel_food_status: Normalized status value
        authorization_status: Normalized authorization value
        history_of_consumption: History of consumption text
        member_state_comments: Member state comments text
        commission_comments: Commission comments text
        conditions_of_use: Conditions of use text
        regulation_reference: EU regulation reference
        union_list_entry: Union List entry reference
        source_url: URL the data was queried from
        raw_html_hash: SHA-256 hash of raw response bytes
    """

    species_latin: str
    species_common: str = ""
    entry_name: str = ""
    novel_food_status: str = ""
    authorization_status: str = ""
    history_of_consumption: str = ""
    member_state_comments: str = ""
    commission_comments: str = ""
    conditions_of_use: str = ""
    regulation_reference: str = ""
    union_list_entry: str = ""
    source_url: str = ""
    raw_html_hash: str = ""


@dataclass
class CatalogueChangeRecord:
    """DTO for a detected change in the catalogue.

    Passed between change detector and repository.
    NOT a SQLAlchemy model.

    Attributes:
        species_latin: Latin species name
        entry_name: Catalogue entry name
        change_type: Type of change (ChangeType.value)
        field_changed: Which field changed (None for NEW/REMOVED)
        old_value: Previous value (None for NEW)
        new_value: New value (None for REMOVED)
        severity: Alert severity level
    """

    species_latin: str
    entry_name: str
    change_type: str
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    severity: str = "low"


__all__ = [
    "NovelFoodEntryRecord",
    "CatalogueChangeRecord",
    "MonitorStatus",
    "MonitorResult",
]
