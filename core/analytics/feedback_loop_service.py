"""Feedback loop service orchestrator.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 5: FeedbackLoopService — orchestrates weekly analysis pipeline.

Runs all analysis components with graceful degradation (AC6):
each component can fail independently without breaking the report.
Missing sections are noted as "insufficient_data" in the report.
"""

import logging
from dataclasses import asdict
from datetime import UTC, date, datetime

from core.analytics.content_performance_analyzer import (
    ContentPerformanceAnalyzer,
    ContentTypeAnalysis,
    HashtagAnalysis,
    SourcePerformanceAnalysis,
    TimeSlotAnalysis,
)
from core.analytics.feedback_loop_models import (
    FeedbackReport,
    WeightAdjustmentRecord,
)
from core.analytics.feedback_loop_repository import FeedbackLoopRepository
from core.analytics.quality_scoring_repository import QualityScoringRepository
from core.analytics.weight_adjuster import WeightAdjuster, WeightAdjustmentProposal
from core.config import FeedbackLoopConfig

logger = logging.getLogger(__name__)


class FeedbackLoopService:
    """Orchestrates weekly performance feedback analysis.

    Task 5.1: Runs content type, posting time, hashtag, source, and weight
    analyses with graceful degradation. Each component that fails
    is logged and marked as a missing section in the report.
    """

    def __init__(
        self,
        content_analyzer: ContentPerformanceAnalyzer,
        weight_adjuster: WeightAdjuster,
        feedback_repo: FeedbackLoopRepository,
        quality_repo: QualityScoringRepository,
        config: FeedbackLoopConfig,
    ) -> None:
        self._content_analyzer = content_analyzer
        self._weight_adjuster = weight_adjuster
        self._feedback_repo = feedback_repo
        self._quality_repo = quality_repo
        self._config = config

    async def run_weekly_analysis(self) -> FeedbackReport:
        """Run the complete weekly feedback analysis pipeline.

        Task 5.1: Steps:
        1. Check post count >= min_posts_threshold
        2. Run content type analysis (graceful)
        3. Run posting time analysis (graceful)
        4. Run hashtag analysis (graceful)
        5. Run source performance analysis (graceful) — AC3
        6. Run weight adjustment proposal (graceful)
        7. Generate recommendations from available data
        8. Compose and save FeedbackReport
        9. Return report

        Returns:
            Persisted FeedbackReport with status "complete" or "partial".
        """
        missing_sections: list[str] = []
        total_posts = await self._quality_repo.get_scored_count()

        # Step 1: threshold gate
        if total_posts < self._config.min_posts_threshold:
            logger.info(
                "Only %d scored posts (need %d) — generating partial report",
                total_posts, self._config.min_posts_threshold,
            )
            missing_sections.append("insufficient_posts")
            report = FeedbackReport(
                report_date=date.today(),
                min_posts_threshold=self._config.min_posts_threshold,
                total_posts_analyzed=total_posts,
                status="partial",
                missing_sections=missing_sections,
            )
            return await self._feedback_repo.save_report(report)

        # Step 2: Content type analysis
        content_type_data: ContentTypeAnalysis | None = None
        content_type_json = None
        try:
            content_type_data = await self._content_analyzer.analyze_content_types(
                min_posts=self._config.min_posts_threshold,
            )
            content_type_json = asdict(content_type_data)
        except Exception:
            logger.exception("Content type analysis failed")
            missing_sections.append("content_type_rankings")

        # Step 3: Posting time analysis
        time_slot_data: TimeSlotAnalysis | None = None
        time_slot_json = None
        try:
            time_slot_data = await self._content_analyzer.analyze_posting_times()
            time_slot_json = asdict(time_slot_data)
        except Exception:
            logger.exception("Posting time analysis failed")
            missing_sections.append("time_slot_analysis")

        # Step 4: Hashtag analysis
        hashtag_data: HashtagAnalysis | None = None
        hashtag_json = None
        try:
            hashtag_data = await self._content_analyzer.analyze_hashtags(
                min_hashtag_posts=self._config.min_hashtag_posts,
                top_limit=self._config.top_hashtags_limit,
            )
            hashtag_json = asdict(hashtag_data)
        except Exception:
            logger.exception("Hashtag analysis failed")
            missing_sections.append("hashtag_rankings")

        # Step 5: Source performance analysis (AC3)
        source_data: SourcePerformanceAnalysis | None = None
        source_json = None
        try:
            source_data = await self._content_analyzer.analyze_source_performance()
            if source_data.insufficient_data:
                source_json = None
                missing_sections.append("source_performance")
            else:
                source_json = asdict(source_data)
        except Exception:
            logger.exception("Source performance analysis failed")
            missing_sections.append("source_performance")

        # Step 6: Weight adjustment proposal
        proposal: WeightAdjustmentProposal | None = None
        proposal_json = None
        try:
            proposal = await self._weight_adjuster.propose_weight_adjustment()
            if proposal is not None:
                proposal_json = asdict(proposal)
        except Exception:
            logger.exception("Weight adjustment proposal failed")
            missing_sections.append("weight_adjustment_proposal")

        # Step 7: Generate recommendations
        recommendations = self.generate_recommendations(
            content_type_data or ContentTypeAnalysis(rankings=[], total_posts=0, insufficient_data=True),
            time_slot_data or TimeSlotAnalysis(slots=[], top_slots=[], total_posts=0, insufficient_data=True),
            hashtag_data or HashtagAnalysis(rankings=[], total_posts=0, insufficient_data=True),
        )

        # Step 8: Compose and save report
        status = "complete" if not missing_sections else "partial"
        report = FeedbackReport(
            report_date=date.today(),
            min_posts_threshold=self._config.min_posts_threshold,
            total_posts_analyzed=total_posts,
            content_type_rankings=content_type_json,
            time_slot_analysis=time_slot_json,
            hashtag_rankings=hashtag_json,
            weight_adjustment_proposal=proposal_json,
            source_performance=source_json,
            recommendations=recommendations,
            status=status,
            missing_sections=missing_sections if missing_sections else None,
        )

        saved = await self._feedback_repo.save_report(report)

        # Save weight adjustment record if proposal was generated
        if proposal is not None:
            adjustment = WeightAdjustmentRecord(
                adjustment_type="quality_scoring",
                previous_weights=proposal.current_weights,
                new_weights=proposal.proposed_weights,
                correlation_data=proposal.correlations,
                feedback_report_id=saved.id,
            )
            await self._feedback_repo.save_weight_adjustment(adjustment)

        logger.info(
            "Weekly feedback analysis complete: status=%s, posts=%d, recommendations=%d",
            status, total_posts, len(recommendations),
        )

        return saved

    def generate_recommendations(
        self,
        content: ContentTypeAnalysis,
        time: TimeSlotAnalysis,
        hashtags: HashtagAnalysis,
    ) -> list[str]:
        """Generate rule-based strategy recommendations.

        Task 5.1: NO LLM call — purely rule-based from analysis data.

        Args:
            content: Content type analysis results.
            time: Time slot analysis results.
            hashtags: Hashtag analysis results.

        Returns:
            List of human-readable recommendation strings.
        """
        recs: list[str] = []

        # Content type recommendations
        if content.rankings and len(content.rankings) >= 2:
            best = content.rankings[0]
            worst = content.rankings[-1]
            if best.avg_score > worst.avg_score:
                recs.append(
                    f"Increase {best.content_type} content "
                    f"(avg score {best.avg_score} vs {worst.avg_score} "
                    f"for {worst.content_type})"
                )
        elif content.rankings:
            best = content.rankings[0]
            recs.append(
                f"Top content type: {best.content_type} "
                f"(avg score {best.avg_score}, {best.count} posts)"
            )

        # Time slot recommendations
        if time.top_slots:
            best_slot = time.top_slots[0]
            recs.append(
                f"Best posting time: {best_slot.day_of_week} "
                f"{best_slot.hour:02d}:00-{best_slot.hour:02d}:59 "
                f"(avg {best_slot.avg_score})"
            )

        # Hashtag recommendations
        if hashtags.rankings:
            top_tags = hashtags.rankings[:3]
            tag_str = ", ".join(f"{t.hashtag} ({t.avg_score})" for t in top_tags)
            recs.append(f"Top performing hashtags: {tag_str}")

        return recs


__all__ = [
    "FeedbackLoopService",
]
