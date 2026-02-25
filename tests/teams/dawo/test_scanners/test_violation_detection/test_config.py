"""Tests for ViolationDetectionConfig (Story 6-7, Task 1).

RED phase: These tests define the expected config behavior.
"""

import pytest

from teams.dawo.scanners.violation_detection.config import (
    ViolationDetectionConfig,
    build_violation_detection_config,
)


@pytest.fixture
def valid_config_data() -> dict:
    """Valid JSON config data for building ViolationDetectionConfig."""
    return {
        "enabled": True,
        "batch_size": 50,
        "min_confidence": 70,
        "auto_violation_categories": ["treatment"],
        "register_check_categories": ["prevention", "enhancement"],
        "suspect_categories": ["general_wellness"],
        "severity_mapping": {
            "treatment": "high",
            "prevention": "high",
            "enhancement": "medium",
            "general_wellness": "low",
        },
        "regulation_mapping": {
            "treatment": "EC 1924/2006 Art. 10",
            "prevention": "EC 1924/2006 Art. 14.1a",
            "enhancement": "EC 1924/2006 Art. 13.1",
            "general_wellness": "EC 1924/2006 Art. 13.1",
        },
        "mushroom_substances": [
            "reishi",
            "lion's mane",
            "chaga",
            "cordyceps",
            "turkey tail",
            "maitake",
            "shiitake",
            "hericium erinaceus",
            "ganoderma lucidum",
            "inonotus obliquus",
            "trametes versicolor",
            "lentinula edodes",
            "ophiocordyceps sinensis",
            "grifola frondosa",
        ],
    }


class TestViolationDetectionConfig:
    """Tests for ViolationDetectionConfig frozen dataclass."""

    def test_valid_config_creation(self, valid_config_data: dict) -> None:
        """Valid config data produces a valid ViolationDetectionConfig."""
        config = build_violation_detection_config(valid_config_data)

        assert config.enabled is True
        assert config.batch_size == 50
        assert config.min_confidence == 70
        assert config.auto_violation_categories == ("treatment",)
        assert config.register_check_categories == ("prevention", "enhancement")
        assert config.suspect_categories == ("general_wellness",)
        assert config.severity_mapping["treatment"] == "high"
        assert config.regulation_mapping["treatment"] == "EC 1924/2006 Art. 10"
        assert "reishi" in config.mushroom_substances

    def test_empty_auto_violation_categories_raises(
        self, valid_config_data: dict
    ) -> None:
        """Empty auto_violation_categories raises ValueError."""
        valid_config_data["auto_violation_categories"] = []
        with pytest.raises(ValueError, match="auto_violation_categories"):
            build_violation_detection_config(valid_config_data)

    def test_invalid_severity_value_raises(
        self, valid_config_data: dict
    ) -> None:
        """Invalid severity value in severity_mapping raises ValueError."""
        valid_config_data["severity_mapping"]["treatment"] = "extreme"
        with pytest.raises(ValueError, match="severity"):
            build_violation_detection_config(valid_config_data)

    def test_non_positive_batch_size_raises(
        self, valid_config_data: dict
    ) -> None:
        """Non-positive batch_size raises ValueError."""
        valid_config_data["batch_size"] = 0
        with pytest.raises(ValueError, match="batch_size"):
            build_violation_detection_config(valid_config_data)

    def test_confidence_threshold_out_of_range_raises(
        self, valid_config_data: dict
    ) -> None:
        """min_confidence outside 0-100 raises ValueError."""
        valid_config_data["min_confidence"] = 101
        with pytest.raises(ValueError, match="min_confidence"):
            build_violation_detection_config(valid_config_data)

        valid_config_data["min_confidence"] = -1
        with pytest.raises(ValueError, match="min_confidence"):
            build_violation_detection_config(valid_config_data)

    def test_build_function_from_json_dict(
        self, valid_config_data: dict
    ) -> None:
        """build_violation_detection_config creates config from dict."""
        config = build_violation_detection_config(valid_config_data)

        assert isinstance(config, ViolationDetectionConfig)
        assert config.batch_size == 50
        assert len(config.mushroom_substances) == 14

    def test_frozen_immutability(self, valid_config_data: dict) -> None:
        """Config is frozen — attributes cannot be reassigned."""
        config = build_violation_detection_config(valid_config_data)

        with pytest.raises(AttributeError):
            config.batch_size = 100  # type: ignore[misc]

    def test_missing_category_in_severity_mapping_raises(
        self, valid_config_data: dict
    ) -> None:
        """All categories must appear in severity_mapping."""
        del valid_config_data["severity_mapping"]["general_wellness"]
        with pytest.raises(ValueError, match="severity_mapping"):
            build_violation_detection_config(valid_config_data)

    def test_missing_category_in_regulation_mapping_raises(
        self, valid_config_data: dict
    ) -> None:
        """All categories must appear in regulation_mapping."""
        del valid_config_data["regulation_mapping"]["enhancement"]
        with pytest.raises(ValueError, match="regulation_mapping"):
            build_violation_detection_config(valid_config_data)
