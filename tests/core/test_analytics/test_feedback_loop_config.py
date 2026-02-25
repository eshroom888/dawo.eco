"""Tests for FeedbackLoopConfig and ARQ job.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 6.5: Write config + job tests (target: 12+ tests).
"""

import sys
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from core.config import FeedbackLoopConfig


# ============================================================
# FeedbackLoopConfig Tests (Task 6.1)
# ============================================================


class TestFeedbackLoopConfig:
    """Tests for FeedbackLoopConfig frozen dataclass."""

    def test_default_values(self) -> None:
        cfg = FeedbackLoopConfig()
        assert cfg.min_posts_threshold == 100
        assert cfg.weight_change_threshold == 0.05
        assert cfg.min_hashtag_posts == 3
        assert cfg.top_hashtags_limit == 20
        assert cfg.enabled is True

    def test_custom_values(self) -> None:
        cfg = FeedbackLoopConfig(
            min_posts_threshold=200,
            weight_change_threshold=0.10,
            min_hashtag_posts=5,
            top_hashtags_limit=50,
            enabled=False,
        )
        assert cfg.min_posts_threshold == 200
        assert cfg.weight_change_threshold == 0.10
        assert cfg.min_hashtag_posts == 5
        assert cfg.top_hashtags_limit == 50
        assert cfg.enabled is False

    def test_frozen(self) -> None:
        cfg = FeedbackLoopConfig()
        with pytest.raises(AttributeError):
            cfg.enabled = False  # type: ignore[misc]

    def test_frozen_min_posts(self) -> None:
        cfg = FeedbackLoopConfig()
        with pytest.raises(AttributeError):
            cfg.min_posts_threshold = 500  # type: ignore[misc]


class TestBuildFeedbackLoopConfig:
    """Tests for _build_feedback_loop_config builder."""

    def test_builds_from_json_data(self) -> None:
        from core.config import _build_feedback_loop_config

        data = {
            "feedback_loop": {
                "min_posts_threshold": 150,
                "weight_change_threshold": 0.08,
                "min_hashtag_posts": 5,
                "top_hashtags_limit": 30,
                "enabled": False,
            }
        }
        cfg = _build_feedback_loop_config(data)
        assert cfg.min_posts_threshold == 150
        assert cfg.weight_change_threshold == 0.08
        assert cfg.enabled is False

    def test_defaults_when_section_missing(self) -> None:
        from core.config import _build_feedback_loop_config

        cfg = _build_feedback_loop_config({})
        assert cfg.min_posts_threshold == 100
        assert cfg.enabled is True

    def test_partial_override(self) -> None:
        from core.config import _build_feedback_loop_config

        data = {"feedback_loop": {"min_posts_threshold": 50}}
        cfg = _build_feedback_loop_config(data)
        assert cfg.min_posts_threshold == 50
        assert cfg.weight_change_threshold == 0.05  # default


# ============================================================
# ARQ Job Tests (Task 6.3)
# ============================================================


class TestRunFeedbackLoopJob:
    """Tests for _run_feedback_loop ARQ job."""

    async def test_returns_skipped_when_disabled(self) -> None:
        from core.scheduling.jobs import _run_feedback_loop

        mock_cfg = MagicMock()
        mock_cfg.enabled = False

        with patch("core.scheduling.jobs._get_feedback_config", return_value=mock_cfg):
            result = await _run_feedback_loop({})
            assert result["status"] == "skipped"

    async def test_returns_complete_on_success(self) -> None:
        from core.scheduling.jobs import _run_feedback_loop

        mock_report = MagicMock()
        mock_report.status = "complete"
        mock_report.total_posts_analyzed = 200
        mock_report.recommendations = ["rec1", "rec2"]

        mock_cfg = MagicMock()
        mock_cfg.enabled = True

        mock_service = AsyncMock()
        mock_service.run_weekly_analysis.return_value = mock_report

        mock_session = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = False

        mock_db_module = MagicMock()
        mock_db_module.get_async_session.return_value = mock_cm

        with (
            patch("core.scheduling.jobs._get_feedback_config", return_value=mock_cfg),
            patch("core.analytics.feedback_loop_service.FeedbackLoopService", return_value=mock_service),
            patch.dict(sys.modules, {"core.database": mock_db_module}),
            patch("core.config.get_config") as mock_get_config,
        ):
            mock_get_config.return_value = MagicMock()
            result = await _run_feedback_loop({})
            assert result["status"] == "complete"
            assert result["posts_analyzed"] == 200
            assert result["recommendations"] == 2

    async def test_returns_error_on_failure(self) -> None:
        from core.scheduling.jobs import _run_feedback_loop

        mock_cfg = MagicMock()
        mock_cfg.enabled = True

        mock_db_module = MagicMock()
        mock_db_module.get_async_session.side_effect = Exception("db down")

        with (
            patch("core.scheduling.jobs._get_feedback_config", return_value=mock_cfg),
            patch.dict(sys.modules, {"core.database": mock_db_module}),
            patch("core.config.get_config") as mock_get_config,
        ):
            mock_get_config.return_value = MagicMock()
            result = await _run_feedback_loop({})
            assert result["status"] == "error"
            assert "db down" in result["error"]

    async def test_returns_partial_status(self) -> None:
        from core.scheduling.jobs import _run_feedback_loop

        mock_report = MagicMock()
        mock_report.status = "partial"
        mock_report.total_posts_analyzed = 50
        mock_report.recommendations = []

        mock_cfg = MagicMock()
        mock_cfg.enabled = True

        mock_service = AsyncMock()
        mock_service.run_weekly_analysis.return_value = mock_report

        mock_session = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = False

        mock_db_module = MagicMock()
        mock_db_module.get_async_session.return_value = mock_cm

        with (
            patch("core.scheduling.jobs._get_feedback_config", return_value=mock_cfg),
            patch("core.analytics.feedback_loop_service.FeedbackLoopService", return_value=mock_service),
            patch.dict(sys.modules, {"core.database": mock_db_module}),
            patch("core.config.get_config") as mock_get_config,
        ):
            mock_get_config.return_value = MagicMock()
            result = await _run_feedback_loop({})
            assert result["status"] == "partial"

    async def test_skipped_result_has_zero_counts(self) -> None:
        from core.scheduling.jobs import _run_feedback_loop

        mock_cfg = MagicMock()
        mock_cfg.enabled = False

        with patch("core.scheduling.jobs._get_feedback_config", return_value=mock_cfg):
            result = await _run_feedback_loop({})
            assert result["posts_analyzed"] == 0
            assert result["recommendations"] == 0
