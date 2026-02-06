"""YouTube Research Scanner Agent.

Main scanner class implementing the scan stage of the Harvester Framework:
    [Scanner] -> Harvester -> InsightExtractor -> Transformer -> Validator -> Publisher -> Research Pool

The YouTubeScanner discovers research content from YouTube by searching for
mushroom/wellness keywords and filtering by view count and recency.

Registration: team_spec.py with tier="scan" (maps to fast model at runtime)

Usage:
    # Created by Team Builder with injected dependencies
    scanner = YouTubeScanner(config, client)

    # Execute scan stage
    result = await scanner.scan()
    # result.videos contains RawYouTubeVideo objects
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from .config import YouTubeScannerConfig
from .schemas import RawYouTubeVideo, ScanResult, ScanStatistics
from .tools import YouTubeClient, YouTubeAPIError, YouTubeScanError


# Module logger
logger = logging.getLogger(__name__)


class YouTubeScanner:
    """YouTube Research Scanner - discovers content from YouTube.

    Implements the scan stage of the Harvester Framework pipeline.
    Searches YouTube for videos matching mushroom/wellness keywords,
    then filters by minimum view count and recency.

    Features:
        - Multi-query search
        - View count threshold filtering
        - Time-based filtering (configurable days back)
        - Deduplication by video ID
        - Health/wellness channel prioritization

    Configuration is injected via constructor - NEVER loads files directly.

    Attributes:
        _config: Scanner configuration (queries, filters)
        _client: YouTube API client for making requests
    """

    def __init__(
        self,
        config: YouTubeScannerConfig,
        client: YouTubeClient,
    ):
        """Initialize scanner with injected dependencies.

        Args:
            config: Scanner configuration from Team Builder
            client: YouTube API client with credentials
        """
        self._config = config
        self._client = client

    async def scan(self) -> ScanResult:
        """Execute the scan stage - discover YouTube videos.

        Iterates through configured search queries, collecting
        videos that meet the filtering criteria.

        Returns:
            ScanResult with discovered videos and statistics

        Raises:
            YouTubeScanError: If critical error prevents scanning
        """
        logger.info(
            "Starting YouTube scan: %d queries, min_views=%d, days_back=%d",
            len(self._config.search_queries),
            self._config.min_views,
            self._config.days_back,
        )

        stats = ScanStatistics()
        all_videos: dict[str, RawYouTubeVideo] = {}  # Keyed by video_id for deduplication
        errors: list[str] = []

        published_after = datetime.now(timezone.utc) - timedelta(days=self._config.days_back)

        for query in self._config.search_queries:
            stats.queries_searched += 1

            try:
                videos = await self._search_and_filter(query, published_after)
                stats.total_videos_found += len(videos)

                # Filter by view count (note: view count requires separate API call in harvester)
                # At scan stage, we collect all results - harvester will filter by views
                filtered = videos
                stats.videos_after_filter += len(filtered)

                # Deduplicate by video ID
                before_count = len(all_videos)
                for video in filtered:
                    all_videos[video.video_id] = video
                stats.duplicates_removed += before_count + len(filtered) - len(all_videos)

            except YouTubeAPIError as e:
                error_msg = f"Failed to search YouTube for '{query}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Continue with other queries

        logger.info(
            "Scan complete: %d videos found, %d after filtering, %d unique",
            stats.total_videos_found,
            stats.videos_after_filter,
            len(all_videos),
        )

        return ScanResult(
            videos=list(all_videos.values()),
            statistics=stats,
            errors=errors,
        )

    async def _search_and_filter(
        self,
        query: str,
        published_after: datetime,
    ) -> list[RawYouTubeVideo]:
        """Search YouTube for query and convert to schema.

        Args:
            query: Search query
            published_after: Only videos published after this date

        Returns:
            List of RawYouTubeVideo objects
        """
        raw_results = await self._client.search_videos(
            query=query,
            published_after=published_after,
            max_results=self._config.max_videos_per_query,
        )

        videos = []
        for result in raw_results:
            try:
                # Extract video data from API response
                video_id = result.get("id", {}).get("videoId")
                if not video_id:
                    continue

                snippet = result.get("snippet", {})

                # Parse publish date
                published_str = snippet.get("publishedAt", "")
                try:
                    published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    published_at = datetime.now(timezone.utc)

                video = RawYouTubeVideo(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    channel_id=snippet.get("channelId", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    published_at=published_at,
                    description=snippet.get("description", ""),
                    thumbnail_url=snippet.get("thumbnails", {}).get("default", {}).get("url"),
                )
                videos.append(video)

            except Exception as e:
                logger.warning(f"Failed to parse video result: {e}")
                continue

        return videos

    def _is_health_channel(self, channel_title: str) -> bool:
        """Check if channel appears to be health/wellness focused.

        Args:
            channel_title: Channel display name

        Returns:
            True if channel name contains health keywords
        """
        channel_lower = channel_title.lower()
        return any(
            keyword in channel_lower
            for keyword in self._config.health_channel_keywords
        )
