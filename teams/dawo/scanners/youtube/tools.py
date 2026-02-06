"""YouTube API clients and tools for the YouTube Research Scanner.

Provides access to YouTube Data API v3 and transcript extraction with:
    - YouTubeClient: YouTube Data API v3 client
    - TranscriptClient: YouTube transcript extraction client
    - QuotaTracker: Daily quota management

ALL API calls go through retry middleware - NEVER make direct calls.

Usage:
    config = YouTubeClientConfig(api_key="...")
    retry = RetryMiddleware(RetryConfig())
    client = YouTubeClient(config, retry)

    videos = await client.search_videos("mushroom supplements", published_after)
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Any

from .config import (
    YouTubeClientConfig,
    TranscriptConfig,
    YOUTUBE_DAILY_QUOTA,
    SEARCH_QUOTA_COST,
    VIDEO_QUOTA_COST,
)
from .schemas import TranscriptResult

# Import youtube-transcript-api for transcript extraction
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


# Module logger
logger = logging.getLogger(__name__)

# YouTube API endpoints
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(Exception):
    """Exception raised for YouTube API errors.

    Attributes:
        message: Error description
        status_code: HTTP status code (if available)
        response_body: Raw response body (if available)
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class QuotaExhaustedError(YouTubeAPIError):
    """Exception raised when YouTube daily quota is exceeded."""

    pass


class YouTubeScanError(Exception):
    """Exception raised for scanner-level errors.

    Attributes:
        message: Error description
        partial_results: Any videos collected before error
    """

    def __init__(
        self,
        message: str,
        partial_results: Optional[list] = None,
    ):
        super().__init__(message)
        self.message = message
        self.partial_results = partial_results or []


class TranscriptError(Exception):
    """Exception raised for transcript extraction errors."""

    pass


class QuotaTracker:
    """Track YouTube API quota usage.

    YouTube has a daily quota of 10,000 units. This class tracks
    usage and prevents exceeding the limit.

    Attributes:
        _used_today: Units consumed today
        _reset_date: Date when quota resets
    """

    DAILY_LIMIT = YOUTUBE_DAILY_QUOTA

    def __init__(self) -> None:
        """Initialize quota tracker."""
        self._used_today = 0
        self._reset_date = datetime.now(timezone.utc).date()

    def check_and_use(self, cost: int) -> None:
        """Check if quota available and consume it.

        Args:
            cost: Quota units to consume

        Raises:
            QuotaExhaustedError: If operation would exceed daily quota
        """
        self._maybe_reset()

        if self._used_today + cost > self.DAILY_LIMIT:
            raise QuotaExhaustedError(
                f"Would exceed daily quota: {self._used_today + cost} > {self.DAILY_LIMIT}",
            )

        self._used_today += cost
        logger.debug(f"Quota used: {self._used_today}/{self.DAILY_LIMIT}")

    def get_remaining(self) -> int:
        """Get remaining quota units for today."""
        self._maybe_reset()
        return self.DAILY_LIMIT - self._used_today

    def _maybe_reset(self) -> None:
        """Reset counter if new day (Pacific Time - YouTube's reset timezone)."""
        today = datetime.now(timezone.utc).date()
        if today > self._reset_date:
            logger.info(f"Quota reset: new day {today}")
            self._used_today = 0
            self._reset_date = today


class YouTubeClient:
    """YouTube Data API v3 client.

    Accepts API key via dependency injection - NEVER loads from file.
    All API calls go through retry middleware for resilience.

    Features:
        - Video search by keywords
        - Video details retrieval (statistics, duration)
        - Quota tracking and management
        - Retry middleware integration

    Attributes:
        _config: YouTube API credentials
        _retry: Retry middleware for API calls
        _quota: Quota tracking instance
        _session: HTTPX async client
    """

    SEARCH_COST = SEARCH_QUOTA_COST
    VIDEO_COST = VIDEO_QUOTA_COST

    def __init__(
        self,
        config: YouTubeClientConfig,
        retry_middleware: Any,  # RetryMiddleware type
        quota_tracker: Optional[QuotaTracker] = None,
    ):
        """Initialize YouTube client with injected dependencies.

        Args:
            config: YouTube API credentials (from environment)
            retry_middleware: Retry middleware for API calls
            quota_tracker: Optional shared quota tracker
        """
        self._config = config
        self._retry = retry_middleware
        self._quota = quota_tracker or QuotaTracker()
        self._session: Optional[Any] = None  # httpx.AsyncClient

    async def __aenter__(self) -> "YouTubeClient":
        """Async context manager entry."""
        import httpx
        self._session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.aclose()
            self._session = None

    async def search_videos(
        self,
        query: str,
        published_after: datetime,
        max_results: int = 50,
    ) -> list[dict]:
        """Search for videos matching query.

        Args:
            query: Search keywords
            published_after: Only videos published after this date
            max_results: Max results (YouTube caps at 50)

        Returns:
            List of video search results

        Raises:
            QuotaExhaustedError: If daily quota exceeded
            YouTubeAPIError: If search fails
        """
        logger.debug(
            f"Searching YouTube for '{query}' (published_after={published_after}, max={max_results})"
        )

        # Check and consume quota
        self._quota.check_and_use(self.SEARCH_COST)

        url = f"{YOUTUBE_API_BASE}/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "publishedAfter": published_after.isoformat().replace("+00:00", "Z"),
            "maxResults": min(max_results, 50),  # YouTube caps at 50
            "order": "relevance",
            "relevanceLanguage": "en",
            "key": self._config.api_key,
        }

        async def make_request() -> dict:
            if not self._session:
                import httpx
                self._session = httpx.AsyncClient(timeout=30.0)

            response = await self._session.get(url, params=params)
            response.raise_for_status()
            return response.json()

        result = await self._retry.execute_with_retry(
            make_request,
            context=f"youtube_search_{query[:20]}",
        )

        if not result.success:
            logger.error(f"YouTube search failed: {result.last_error}")
            raise YouTubeAPIError(f"Search failed after retries: {result.last_error}")

        response_data = result.response
        items = response_data.get("items", [])

        logger.debug(f"Search returned {len(items)} videos for '{query}'")
        return items

    async def get_video_statistics(
        self,
        video_ids: list[str],
    ) -> dict[str, dict]:
        """Get statistics for multiple videos (batch).

        Args:
            video_ids: List of video IDs (max 50)

        Returns:
            Dict mapping video_id to statistics

        Raises:
            QuotaExhaustedError: If daily quota exceeded
            YouTubeAPIError: If request fails
        """
        if not video_ids:
            return {}

        # Batch limit is 50 videos per request
        batch_ids = video_ids[:50]
        quota_cost = len(batch_ids) * self.VIDEO_COST

        logger.debug(f"Fetching statistics for {len(batch_ids)} videos")

        # Check and consume quota
        self._quota.check_and_use(quota_cost)

        url = f"{YOUTUBE_API_BASE}/videos"
        params = {
            "part": "statistics,contentDetails,snippet",
            "id": ",".join(batch_ids),
            "key": self._config.api_key,
        }

        async def make_request() -> dict:
            if not self._session:
                import httpx
                self._session = httpx.AsyncClient(timeout=30.0)

            response = await self._session.get(url, params=params)
            response.raise_for_status()
            return response.json()

        result = await self._retry.execute_with_retry(
            make_request,
            context=f"youtube_videos_{len(batch_ids)}",
        )

        if not result.success:
            logger.error(f"YouTube video statistics failed: {result.last_error}")
            raise YouTubeAPIError(f"Video statistics failed after retries: {result.last_error}")

        response_data = result.response
        items = response_data.get("items", [])

        # Map by video ID for easy lookup
        stats_map = {}
        for item in items:
            video_id = item.get("id")
            if video_id:
                stats_map[video_id] = item

        logger.debug(f"Retrieved statistics for {len(stats_map)} videos")
        return stats_map

    @property
    def quota_remaining(self) -> int:
        """Get remaining quota units for today."""
        return self._quota.get_remaining()


class TranscriptClient:
    """YouTube transcript extraction client.

    Uses youtube-transcript-api package for transcript retrieval.
    Prefers manual captions over auto-generated when available.

    Attributes:
        _config: Transcript configuration
        _retry: Retry middleware for API calls
    """

    def __init__(
        self,
        config: TranscriptConfig,
        retry_middleware: Any,  # RetryMiddleware type
    ):
        """Initialize transcript client with injected dependencies.

        Args:
            config: Transcript extraction settings
            retry_middleware: Retry middleware for API calls
        """
        self._config = config
        self._retry = retry_middleware

    async def get_transcript(
        self,
        video_id: str,
        languages: Optional[list[str]] = None,
    ) -> TranscriptResult:
        """Extract transcript from YouTube video.

        Args:
            video_id: YouTube video ID
            languages: Preferred languages (falls back to auto-generated)

        Returns:
            TranscriptResult with text and metadata
        """
        languages = languages or self._config.preferred_languages

        logger.debug(f"Extracting transcript for video {video_id} (languages={languages})")

        try:
            # Get available transcripts for the video using instance-based API
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)

            is_auto_generated = False

            try:
                # Prefer manual captions over auto-generated
                transcript = transcript_list.find_manually_created_transcript(languages)
                is_auto_generated = False
                logger.debug(f"Found manual transcript for {video_id}")
            except NoTranscriptFound:
                # Fall back to auto-generated
                transcript = transcript_list.find_generated_transcript(languages)
                is_auto_generated = True
                logger.debug(f"Using auto-generated transcript for {video_id}")

            # Fetch and concatenate segments
            segments = transcript.fetch()
            full_text = " ".join(seg["text"] for seg in segments)

            # Calculate duration from last segment
            duration_seconds = 0
            if segments:
                last_seg = segments[-1]
                duration_seconds = int(last_seg["start"] + last_seg["duration"])

            # Truncate if exceeds max length
            if len(full_text) > self._config.max_transcript_length:
                full_text = full_text[: self._config.max_transcript_length]
                logger.debug(f"Truncated transcript to {self._config.max_transcript_length} chars")

            return TranscriptResult(
                text=full_text,
                language=transcript.language_code,
                is_auto_generated=is_auto_generated,
                available=True,
                duration_seconds=duration_seconds,
            )

        except TranscriptsDisabled:
            logger.warning(f"Transcripts disabled for video {video_id}")
            return TranscriptResult(
                text="",
                available=False,
                reason="disabled",
            )

        except NoTranscriptFound:
            logger.warning(f"No transcript found for video {video_id}")
            return TranscriptResult(
                text="",
                available=False,
                reason="not_found",
            )

        except Exception as e:
            logger.error(f"Transcript extraction failed for {video_id}: {e}")
            raise TranscriptError(f"Failed to extract transcript: {e}") from e
