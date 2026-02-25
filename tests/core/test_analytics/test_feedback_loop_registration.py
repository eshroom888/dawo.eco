"""Tests for feedback loop service registration and exports.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 7.3: Write registration tests (target: 5+ tests).
"""

import pytest


class TestAnalyticsExports:
    """Tests that all feedback loop classes are exported from analytics __init__."""

    def test_feedback_loop_repository_exported(self) -> None:
        from core.analytics import FeedbackLoopRepository
        assert FeedbackLoopRepository is not None

    def test_feedback_loop_service_exported(self) -> None:
        from core.analytics import FeedbackLoopService
        assert FeedbackLoopService is not None

    def test_content_performance_analyzer_exported(self) -> None:
        from core.analytics import ContentPerformanceAnalyzer
        assert ContentPerformanceAnalyzer is not None

    def test_weight_adjuster_exported(self) -> None:
        from core.analytics import WeightAdjuster
        assert WeightAdjuster is not None

    def test_weight_adjustment_proposal_exported(self) -> None:
        from core.analytics import WeightAdjustmentProposal
        assert WeightAdjustmentProposal is not None

    def test_feedback_report_exported(self) -> None:
        from core.analytics import FeedbackReport
        assert FeedbackReport is not None

    def test_weight_adjustment_record_exported(self) -> None:
        from core.analytics import WeightAdjustmentRecord
        assert WeightAdjustmentRecord is not None

    def test_source_performance_analysis_exported(self) -> None:
        from core.analytics import SourcePerformanceAnalysis
        assert SourcePerformanceAnalysis is not None

    def test_source_ranking_exported(self) -> None:
        from core.analytics import SourceRanking
        assert SourceRanking is not None


class TestTeamSpecRegistration:
    """Tests that services are registered in team_spec.py."""

    def test_feedback_loop_repository_registered(self) -> None:
        from teams.dawo.team_spec import SERVICES
        names = [s.name for s in SERVICES]
        assert "feedback_loop_repository" in names

    def test_content_performance_analyzer_registered(self) -> None:
        from teams.dawo.team_spec import SERVICES
        names = [s.name for s in SERVICES]
        assert "content_performance_analyzer" in names

    def test_weight_adjuster_registered(self) -> None:
        from teams.dawo.team_spec import SERVICES
        names = [s.name for s in SERVICES]
        assert "weight_adjuster" in names

    def test_feedback_loop_service_registered(self) -> None:
        from teams.dawo.team_spec import SERVICES
        names = [s.name for s in SERVICES]
        assert "feedback_loop_service" in names

    def test_feedback_loop_repo_requires_session(self) -> None:
        from teams.dawo.team_spec import SERVICES
        repo = next(s for s in SERVICES if s.name == "feedback_loop_repository")
        assert repo.requires_session is True

    def test_feedback_loop_service_no_session(self) -> None:
        from teams.dawo.team_spec import SERVICES
        svc = next(s for s in SERVICES if s.name == "feedback_loop_service")
        assert svc.requires_session is False
