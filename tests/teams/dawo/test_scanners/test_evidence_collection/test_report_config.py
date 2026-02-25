"""Tests for ViolationReportConfig (Story 6-10, Task 2).

Validates frozen dataclass, defaults, validation, and factory function.
"""

import pytest

from teams.dawo.scanners.evidence_collection.report_config import (
    ViolationReportConfig,
    build_violation_report_config,
)


class TestViolationReportConfig:
    """Tests for ViolationReportConfig frozen dataclass."""

    def test_defaults(self) -> None:
        """Config has correct defaults."""
        config = ViolationReportConfig()
        assert config.enabled is True
        assert config.storage_path == "evidence/reports"
        assert config.default_template == "standard"
        assert config.company_name == "DAWO.ECO"
        assert config.max_evidence_per_report == 100
        assert config.screenshot_max_width_px == 600
        assert config.available_templates == [
            "standard",
            "mattilsynet",
            "eu_authority",
            "legal",
        ]
        assert config.pdf_variant == "pdf/a-3u"

    def test_is_frozen(self) -> None:
        """Config is immutable."""
        config = ViolationReportConfig()
        with pytest.raises(AttributeError):
            config.enabled = False  # type: ignore[misc]

    def test_validation_max_evidence_positive(self) -> None:
        """max_evidence_per_report must be positive."""
        with pytest.raises(ValueError, match="max_evidence_per_report"):
            ViolationReportConfig(max_evidence_per_report=0)

    def test_validation_screenshot_width_positive(self) -> None:
        """screenshot_max_width_px must be positive."""
        with pytest.raises(ValueError, match="screenshot_max_width_px"):
            ViolationReportConfig(screenshot_max_width_px=0)

    def test_validation_storage_path_not_empty(self) -> None:
        """storage_path must not be empty."""
        with pytest.raises(ValueError, match="storage_path"):
            ViolationReportConfig(storage_path="")

    def test_validation_available_templates_not_empty(self) -> None:
        """available_templates must not be empty."""
        with pytest.raises(ValueError, match="available_templates"):
            ViolationReportConfig(available_templates=[])


class TestBuildViolationReportConfig:
    """Tests for build_violation_report_config factory."""

    def test_from_full_dict(self) -> None:
        """Factory builds config from complete dict."""
        data = {
            "enabled": False,
            "storage_path": "custom/reports",
            "default_template": "legal",
            "company_name": "TestCo",
            "max_evidence_per_report": 50,
            "screenshot_max_width_px": 400,
            "available_templates": ["standard", "legal"],
            "pdf_variant": "pdf/a-1b",
        }
        config = build_violation_report_config(data)
        assert config.enabled is False
        assert config.storage_path == "custom/reports"
        assert config.default_template == "legal"
        assert config.company_name == "TestCo"
        assert config.max_evidence_per_report == 50
        assert config.screenshot_max_width_px == 400
        assert config.available_templates == ["standard", "legal"]
        assert config.pdf_variant == "pdf/a-1b"

    def test_from_empty_dict(self) -> None:
        """Factory uses defaults for missing keys."""
        config = build_violation_report_config({})
        assert config.enabled is True
        assert config.storage_path == "evidence/reports"

    def test_from_partial_dict(self) -> None:
        """Factory merges provided keys with defaults."""
        config = build_violation_report_config({"company_name": "Other"})
        assert config.company_name == "Other"
        assert config.max_evidence_per_report == 100
