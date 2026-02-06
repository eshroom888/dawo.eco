"""YouTube Harvester - enriches videos with statistics and transcripts.

Implements the harvest stage of the Harvester Framework:
    Scanner -> [Harvester] -> InsightExtractor -> Transformer -> Validator -> Publisher -> Research Pool

The YouTubeHarvester takes raw videos from the scanner and enriches them
with full statistics (views, likes, comments) and transcript text.

Registration: team_spec.py as RegisteredService

Usage:
    # Created by Team Builder with injected dependencies
    harvester = YouTubeHarvester(youtube_client, transcript_client, config)

    # Harvest raw videos
    harvested = await harvester.harvest(raw_videos)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .config import YouTubeScannerConfig
from .schemas import RawYouTubeVideo, HarvestedVideo, TranscriptResult
from .tools import YouTubeClient, TranscriptClient, YouTubeAPIError, TranscriptError


# Module logger
logger = logging.getLogger(__name__)


class HarvesterError(Exception):
    """Exception raised for harvester-level errors.

    Attributes:
        message: Error description
        partial_results: Any videos harvested before error
    """

    def __init__(
        self,
        message: str,
        partial_results: Optional[list[HarvestedVideo]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.partial_results = partial_results or []


class YouTubeHarvester:
    """YouTube Harvester - enriches videos with statistics and transcripts.

    Implements the harvest stage of the Harvester Framework pipeline.
    Takes raw videos from scanner and fetches full details including
    view counts, like counts, and transcript text.

    Features:
        - Batch fetching of video statistics (up to 50 per request)
        - Transcript extraction with fallback handling
        - View count filtering (min_views from config)
        - Graceful handling of missing transcripts

    Configuration is injected via constructor - NEVER loads files directly.

    Attributes:
        _youtube_client: YouTube Data API client
        _transcript_client: Transcript extraction client
        _config: Scanner configuration
    """

    def __init__(
        self,
        youtube_client: YouTubeClient,
        transcript_client: TranscriptClient,
        config: YouTubeScannerConfig,
    ):
        """Initialize harvester with injected dependencies.

        Args:
            youtube_client: YouTube Data API client
            transcript_client: Transcript extraction client
            config: Scanner configuration with min_views filter
        """
        self._youtube_client = youtube_client
        self._transcript_client = transcript_client
        self._config = config

    async def harvest(
        self,
        raw_videos: list[RawYouTubeVideo],
    ) -> list[HarvestedVideo]:
        """Harvest full details for raw videos.

        Fetches statistics and transcripts for each video, filtering
        by minimum view count.

        Args:
            raw_videos: List of raw videos from scanner

        Returns:
            List of enriched HarvestedVideo objects

        Raises:
            HarvesterError: If critical error prevents harvesting
        """
        if not raw_videos:
            logger.info("No videos to harvest")
            return []

        logger.info(f"Harvesting {len(raw_videos)} videos")

        # Step 1: Batch fetch video statistics
        video_ids = [v.video_id for v in raw_videos]
        try:
            stats_map = await self._youtube_client.get_video_statistics(video_ids)
        except YouTubeAPIError as e:
            logger.error(f"Failed to fetch video statistics: {e}")
            raise HarvesterError(f"Statistics fetch failed: {e}") from e

        # Step 2: Filter by view count and enrich with transcripts
        harvested: list[HarvestedVideo] = []
        skipped_low_views = 0
        transcripts_extracted = 0
        transcripts_unavailable = 0

        for raw_video in raw_videos:
            video_stats = stats_map.get(raw_video.video_id, {})

            # Parse view count
            view_count = self._parse_view_count(video_stats)

            # Filter by minimum views
            if view_count < self._config.min_views:
                skipped_low_views += 1
                logger.debug(
                    f"Skipping {raw_video.video_id}: {view_count} views < {self._config.min_views}"
                )
                continue

            # Extract transcript
            transcript_result = await self._extract_transcript(raw_video.video_id)

            if transcript_result.available:
                transcripts_extracted += 1
            else:
                transcripts_unavailable += 1

            # Build harvested video
            harvested_video = self._build_harvested_video(
                raw_video=raw_video,
                stats=video_stats,
                transcript_result=transcript_result,
            )
            harvested.append(harvested_video)

        logger.info(
            f"Harvest complete: {len(harvested)} videos enriched, "
            f"{skipped_low_views} skipped (low views), "
            f"{transcripts_extracted} transcripts, "
            f"{transcripts_unavailable} without transcript"
        )

        return harvested

    def _parse_view_count(self, stats: dict) -> int:
        """Parse view count from video statistics.

        Args:
            stats: Video statistics from API

        Returns:
            View count as integer, 0 if unavailable
        """
        statistics = stats.get("statistics", {})
        view_count_str = statistics.get("viewCount", "0")
        try:
            return int(view_count_str)
        except (ValueError, TypeError):
            return 0

    def _parse_duration(self, stats: dict) -> int:
        """Parse video duration from content details.

        Args:
            stats: Video statistics from API

        Returns:
            Duration in seconds, 0 if unavailable
        """
        content_details = stats.get("contentDetails", {})
        duration_str = content_details.get("duration", "")

        # Parse ISO 8601 duration (e.g., "PT15M30S")
        if not duration_str:
            return 0

        try:
            # Remove PT prefix
            duration_str = duration_str.replace("PT", "")

            seconds = 0
            if "H" in duration_str:
                hours, duration_str = duration_str.split("H")
                seconds += int(hours) * 3600
            if "M" in duration_str:
                minutes, duration_str = duration_str.split("M")
                seconds += int(minutes) * 60
            if "S" in duration_str:
                secs = duration_str.replace("S", "")
                seconds += int(secs) if secs else 0

            return seconds
        except (ValueError, TypeError):
            return 0

    async def _extract_transcript(self, video_id: str) -> TranscriptResult:
        """Extract transcript with error handling.

        Args:
            video_id: YouTube video ID

        Returns:
            TranscriptResult (available=False if extraction fails)
        """
        try:
            return await self._transcript_client.get_transcript(video_id)
        except TranscriptError as e:
            logger.warning(f"Transcript extraction failed for {video_id}: {e}")
            return TranscriptResult(
                text="",
                available=False,
                reason="extraction_error",
            )
        except Exception as e:
            logger.warning(f"Unexpected error extracting transcript for {video_id}: {e}")
            return TranscriptResult(
                text="",
                available=False,
                reason="unexpected_error",
            )

    def _build_harvested_video(
        self,
        raw_video: RawYouTubeVideo,
        stats: dict,
        transcript_result: TranscriptResult,
    ) -> HarvestedVideo:
        """Build HarvestedVideo from raw video and fetched data.

        Args:
            raw_video: Original raw video from scanner
            stats: Video statistics from API
            transcript_result: Transcript extraction result

        Returns:
            Enriched HarvestedVideo object
        """
        statistics = stats.get("statistics", {})

        return HarvestedVideo(
            video_id=raw_video.video_id,
            title=raw_video.title,
            channel_id=raw_video.channel_id,
            channel_title=raw_video.channel_title,
            published_at=raw_video.published_at,
            description=raw_video.description,
            view_count=self._parse_view_count(stats),
            like_count=int(statistics.get("likeCount", 0)),
            comment_count=int(statistics.get("commentCount", 0)),
            duration_seconds=self._parse_duration(stats),
            thumbnail_url=raw_video.thumbnail_url,
            transcript=transcript_result.text,
            transcript_available=transcript_result.available,
            transcript_language=transcript_result.language,
            is_auto_generated=transcript_result.is_auto_generated,
        )
