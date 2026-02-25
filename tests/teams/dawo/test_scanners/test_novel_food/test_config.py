"""Tests for Novel Food Monitor configuration.

Story 6-2, Task 3: Create Novel Food config.
Tests frozen dataclass config, validation, and builder function.
"""

import pytest

from teams.dawo.scanners.novel_food.config import (
    SpeciesConfig,
    NovelFoodMonitorConfig,
    build_novel_food_config,
)


class TestSpeciesConfig:
    """Tests for SpeciesConfig frozen dataclass."""

    def test_create_with_defaults(self):
        config = SpeciesConfig(latin_name="Hericium erinaceus")
        assert config.latin_name == "Hericium erinaceus"
        assert config.common_names == ()
        assert config.is_dawo_product is False

    def test_create_full(self):
        config = SpeciesConfig(
            latin_name="Hericium erinaceus",
            common_names=("Lion's Mane", "Yamabushitake"),
            is_dawo_product=True,
        )
        assert config.latin_name == "Hericium erinaceus"
        assert "Lion's Mane" in config.common_names
        assert config.is_dawo_product is True

    def test_is_frozen(self):
        config = SpeciesConfig(latin_name="Test")
        with pytest.raises(AttributeError):
            config.latin_name = "Changed"


class TestNovelFoodMonitorConfig:
    """Tests for NovelFoodMonitorConfig frozen dataclass."""

    def _make_valid_config(self, **overrides):
        defaults = {
            "search_url": "https://ec.europa.eu/food/food-feed-portal/backend/novel-food-catalogue/search",
            "portal_url": "https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search",
            "species": (SpeciesConfig(latin_name="Hericium erinaceus"),),
        }
        defaults.update(overrides)
        return NovelFoodMonitorConfig(**defaults)

    def test_create_valid(self):
        config = self._make_valid_config()
        assert config.search_url.startswith("https://")
        assert len(config.species) == 1

    def test_default_values(self):
        config = self._make_valid_config()
        assert config.schedule_cron == "30 5 * * 0"
        assert config.request_delay_seconds == 10
        assert config.max_retries == 3
        assert config.timeout_seconds == 30
        assert config.user_agent == "DAWO-ECO-RegulatoryMonitor/1.0"

    def test_is_frozen(self):
        config = self._make_valid_config()
        with pytest.raises(AttributeError):
            config.search_url = "changed"

    def test_validation_empty_search_url(self):
        with pytest.raises(ValueError, match="search_url"):
            NovelFoodMonitorConfig(
                search_url="",
                species=(SpeciesConfig(latin_name="Test"),),
            )

    def test_validation_empty_species(self):
        with pytest.raises(ValueError, match="species"):
            NovelFoodMonitorConfig(
                search_url="https://example.com",
                species=(),
            )

    def test_validation_multiple_errors(self):
        with pytest.raises(ValueError) as exc_info:
            NovelFoodMonitorConfig(search_url="", species=())
        assert "search_url" in str(exc_info.value)
        assert "species" in str(exc_info.value)


class TestBuildNovelFoodConfig:
    """Tests for build_novel_food_config builder function."""

    def test_build_from_dict(self):
        data = {
            "monitor": {
                "search_url": "https://ec.europa.eu/food/food-feed-portal/backend/novel-food-catalogue/search",
                "portal_url": "https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search",
                "schedule_cron": "30 5 * * 0",
                "request_delay_seconds": 10,
                "max_retries": 3,
                "timeout_seconds": 30,
                "user_agent": "DAWO-ECO-RegulatoryMonitor/1.0",
            },
            "species": [
                {
                    "latin_name": "Hericium erinaceus",
                    "common_names": ["Lion's Mane"],
                    "is_dawo_product": True,
                },
                {
                    "latin_name": "Inonotus obliquus",
                    "common_names": ["Chaga"],
                    "is_dawo_product": True,
                },
            ],
        }
        config = build_novel_food_config(data)
        assert config.search_url == data["monitor"]["search_url"]
        assert len(config.species) == 2
        assert config.species[0].latin_name == "Hericium erinaceus"
        assert config.species[0].is_dawo_product is True

    def test_build_converts_lists_to_tuples(self):
        data = {
            "monitor": {
                "search_url": "https://example.com",
            },
            "species": [
                {
                    "latin_name": "Test",
                    "common_names": ["Name1", "Name2"],
                    "is_dawo_product": False,
                },
            ],
        }
        config = build_novel_food_config(data)
        assert isinstance(config.species, tuple)
        assert isinstance(config.species[0].common_names, tuple)

    def test_build_with_alert_transitions(self):
        data = {
            "monitor": {
                "search_url": "https://example.com",
            },
            "species": [{"latin_name": "Test"}],
            "alert_on_status_change": ["novel_to_not_novel", "not_determined_to_novel"],
        }
        config = build_novel_food_config(data)
        assert len(config.alert_status_transitions) == 2
