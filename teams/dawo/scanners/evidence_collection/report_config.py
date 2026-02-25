"""Violation Report Configuration (Story 6-10, Task 2).

Frozen dataclass for violation report settings.
Loaded via dependency injection from config/dawo_violation_reports.json.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ViolationReportConfig:
    """Configuration for on-demand violation report generation.

    Attributes:
        enabled: Whether report generation is active.
        storage_path: Base directory for generated report storage.
        default_template: Default report template variant.
        company_name: Company name for report headers.
        max_evidence_per_report: Maximum evidence records per report.
        screenshot_max_width_px: Max screenshot display width in PDF.
        available_templates: List of valid template type names.
        pdf_variant: PDF standard variant for WeasyPrint output.
    """

    enabled: bool = True
    storage_path: str = "evidence/reports"
    default_template: str = "standard"
    company_name: str = "DAWO.ECO"
    max_evidence_per_report: int = 100
    screenshot_max_width_px: int = 600
    available_templates: list[str] = field(
        default_factory=lambda: ["standard", "mattilsynet", "eu_authority", "legal"]
    )
    pdf_variant: str = "pdf/a-3u"

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_evidence_per_report <= 0:
            raise ValueError("max_evidence_per_report must be positive")
        if self.screenshot_max_width_px <= 0:
            raise ValueError("screenshot_max_width_px must be positive")
        if not self.storage_path:
            raise ValueError("storage_path must not be empty")
        if not self.available_templates:
            raise ValueError("available_templates must not be empty")


def build_violation_report_config(data: dict) -> ViolationReportConfig:
    """Build ViolationReportConfig from a JSON-compatible dict.

    Args:
        data: Configuration dictionary (e.g., from JSON file).

    Returns:
        Validated ViolationReportConfig instance.
    """
    return ViolationReportConfig(
        enabled=data.get("enabled", True),
        storage_path=data.get("storage_path", "evidence/reports"),
        default_template=data.get("default_template", "standard"),
        company_name=data.get("company_name", "DAWO.ECO"),
        max_evidence_per_report=data.get("max_evidence_per_report", 100),
        screenshot_max_width_px=data.get("screenshot_max_width_px", 600),
        available_templates=data.get(
            "available_templates",
            ["standard", "mattilsynet", "eu_authority", "legal"],
        ),
        pdf_variant=data.get("pdf_variant", "pdf/a-3u"),
    )


__all__ = [
    "ViolationReportConfig",
    "build_violation_report_config",
]
