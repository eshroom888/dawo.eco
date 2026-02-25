"""Tests for HealthClaimsMonitorConfig.

Story 6-1, Task 12.24: Config validation tests.
"""

import pytest

from teams.dawo.scanners.health_claims.config import (
    HealthClaimsMonitorConfig,
    build_health_claims_config,
)


class TestHealthClaimsMonitorConfig:
    """Tests for config validation."""

    def test_valid_config(self):
        config = HealthClaimsMonitorConfig(
            download_url="https://example.com/data.xls",
            mushroom_keywords=("beta-glucan",),
        )
        assert config.download_url == "https://example.com/data.xls"

    def test_empty_download_url_raises(self):
        with pytest.raises(ValueError, match="download_url is required"):
            HealthClaimsMonitorConfig(
                download_url="",
                mushroom_keywords=("beta-glucan",),
            )

    def test_no_keywords_raises(self):
        with pytest.raises(ValueError, match="At least one keyword list"):
            HealthClaimsMonitorConfig(
                download_url="https://example.com/data.xls",
            )

    def test_negative_delay_raises(self):
        with pytest.raises(ValueError, match="request_delay_seconds"):
            HealthClaimsMonitorConfig(
                download_url="https://example.com/data.xls",
                mushroom_keywords=("beta-glucan",),
                request_delay_seconds=-1,
            )

    def test_zero_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries"):
            HealthClaimsMonitorConfig(
                download_url="https://example.com/data.xls",
                mushroom_keywords=("beta-glucan",),
                max_retries=0,
            )

    def test_frozen(self):
        config = HealthClaimsMonitorConfig(
            download_url="https://example.com/data.xls",
            mushroom_keywords=("beta-glucan",),
        )
        with pytest.raises(AttributeError):
            config.download_url = "new_url"

    def test_multiple_keyword_lists_valid(self):
        config = HealthClaimsMonitorConfig(
            download_url="https://example.com/data.xls",
            adaptogen_keywords=("ashwagandha",),
            vitamin_mineral_keywords=("vitamin c",),
        )
        assert config.adaptogen_keywords == ("ashwagandha",)

    def test_only_vitamin_keywords_valid(self):
        config = HealthClaimsMonitorConfig(
            download_url="https://example.com/data.xls",
            vitamin_mineral_keywords=("vitamin c",),
        )
        assert len(config.vitamin_mineral_keywords) == 1


class TestBuildHealthClaimsConfig:
    """Tests for config builder function."""

    def test_builds_from_json(self):
        data = {
            "monitor": {
                "source_url": "https://data.europa.eu/datasets",
                "download_url": "https://ec.europa.eu/food/claims/test.xls",
                "schedule_cron": "0 5 * * 0",
                "request_delay_seconds": 5,
                "max_retries": 3,
            },
            "substances": {
                "mushroom": ["beta-glucan", "reishi"],
                "adaptogen": ["ashwagandha"],
                "vitamins_minerals": ["vitamin c"],
            },
            "alert_on_status_change": ["on_hold->authorised"],
        }
        config = build_health_claims_config(data)
        assert config.download_url == "https://ec.europa.eu/food/claims/test.xls"
        assert config.mushroom_keywords == ("beta-glucan", "reishi")
        assert config.adaptogen_keywords == ("ashwagandha",)
        assert config.vitamin_mineral_keywords == ("vitamin c",)
        assert config.alert_status_transitions == ("on_hold->authorised",)

    def test_builds_with_defaults(self):
        data = {
            "monitor": {"download_url": "https://example.com/test.xls"},
            "substances": {"mushroom": ["beta-glucan"]},
        }
        config = build_health_claims_config(data)
        assert config.schedule_cron == "0 5 * * 0"
        assert config.request_delay_seconds == 5
        assert config.max_retries == 3

    def test_empty_data_raises(self):
        with pytest.raises(ValueError):
            build_health_claims_config({})
