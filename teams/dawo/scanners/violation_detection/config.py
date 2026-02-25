"""Violation Detection Configuration (Story 6-7, Task 1).

Frozen dataclass for EU violation detection settings.
Loaded from config/dawo_violation_detection.json via builder function.
"""

from dataclasses import dataclass, field


VALID_SEVERITY_VALUES = ("high", "medium", "low")


@dataclass(frozen=True)
class ViolationDetectionConfig:
    """Configuration for EU violation detection engine.

    Attributes:
        enabled: Whether violation detection is active.
        batch_size: Maximum claims to process per run.
        min_confidence: Minimum claim confidence score (0-100) for evaluation.
        auto_violation_categories: Categories always classified as VIOLATION.
        register_check_categories: Categories checked against EU register.
        suspect_categories: Categories always classified as SUSPECT.
        severity_mapping: Category -> severity level mapping.
        regulation_mapping: Category -> EU regulation article mapping.
        mushroom_substances: Substance keywords for cross-referencing EU register.
    """

    enabled: bool = True
    batch_size: int = 50
    min_confidence: int = 70
    auto_violation_categories: tuple[str, ...] = ("treatment",)
    register_check_categories: tuple[str, ...] = ("prevention", "enhancement")
    suspect_categories: tuple[str, ...] = ("general_wellness",)
    severity_mapping: dict[str, str] = field(default_factory=lambda: {
        "treatment": "high",
        "prevention": "high",
        "enhancement": "medium",
        "general_wellness": "low",
    })
    regulation_mapping: dict[str, str] = field(default_factory=lambda: {
        "treatment": "EC 1924/2006 Art. 10",
        "prevention": "EC 1924/2006 Art. 14.1a",
        "enhancement": "EC 1924/2006 Art. 13.1",
        "general_wellness": "EC 1924/2006 Art. 13.1",
    })
    mushroom_substances: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        if self.batch_size <= 0:
            raise ValueError(
                f"batch_size must be positive, got {self.batch_size}"
            )
        if not (0 <= self.min_confidence <= 100):
            raise ValueError(
                f"min_confidence must be 0-100, got {self.min_confidence}"
            )
        if not self.auto_violation_categories:
            raise ValueError(
                "auto_violation_categories must contain at least 1 category"
            )
        # Validate severity values
        for category, severity in self.severity_mapping.items():
            if severity not in VALID_SEVERITY_VALUES:
                raise ValueError(
                    f"Invalid severity '{severity}' for category '{category}'. "
                    f"Must be one of: {VALID_SEVERITY_VALUES}"
                )
        # Validate all categories appear in severity_mapping
        all_categories = (
            self.auto_violation_categories
            + self.register_check_categories
            + self.suspect_categories
        )
        for cat in all_categories:
            if cat not in self.severity_mapping:
                raise ValueError(
                    f"Category '{cat}' missing from severity_mapping. "
                    f"All categories must have severity_mapping entries."
                )
            if cat not in self.regulation_mapping:
                raise ValueError(
                    f"Category '{cat}' missing from regulation_mapping. "
                    f"All categories must have regulation_mapping entries."
                )


def build_violation_detection_config(
    data: dict,
) -> ViolationDetectionConfig:
    """Build ViolationDetectionConfig from a JSON-loaded dict.

    Args:
        data: Dictionary from JSON config file.

    Returns:
        Validated ViolationDetectionConfig instance.

    Raises:
        ValueError: If config validation fails.
    """
    return ViolationDetectionConfig(
        enabled=data.get("enabled", True),
        batch_size=data.get("batch_size", 50),
        min_confidence=data.get("min_confidence", 70),
        auto_violation_categories=tuple(
            data.get("auto_violation_categories", ["treatment"])
        ),
        register_check_categories=tuple(
            data.get("register_check_categories", ["prevention", "enhancement"])
        ),
        suspect_categories=tuple(
            data.get("suspect_categories", ["general_wellness"])
        ),
        severity_mapping=data.get("severity_mapping", {
            "treatment": "high",
            "prevention": "high",
            "enhancement": "medium",
            "general_wellness": "low",
        }),
        regulation_mapping=data.get("regulation_mapping", {
            "treatment": "EC 1924/2006 Art. 10",
            "prevention": "EC 1924/2006 Art. 14.1a",
            "enhancement": "EC 1924/2006 Art. 13.1",
            "general_wellness": "EC 1924/2006 Art. 13.1",
        }),
        mushroom_substances=tuple(
            data.get("mushroom_substances", [])
        ),
    )


__all__ = [
    "ViolationDetectionConfig",
    "build_violation_detection_config",
    "VALID_SEVERITY_VALUES",
]
