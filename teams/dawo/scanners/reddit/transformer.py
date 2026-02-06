"""Reddit Transformer - standardizes posts for Research Pool.

Implements the transform stage of the Harvester Framework pipeline:
    Scanner → Harvester → [Transformer] → Validator → Publisher → Research Pool

The transformer takes harvested posts and converts them to the
TransformedResearch schema required by the Research Pool.

Usage:
    transformer = RedditTransformer()
    standardized = await transformer.transform(harvested_posts)
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from teams.dawo.research import TransformedResearch, ResearchSource

from .schemas import HarvestedPost
from .config import MAX_CONTENT_LENGTH, DEFAULT_KEYWORDS


# Module logger
logger = logging.getLogger(__name__)

# Reddit URL base
REDDIT_URL_BASE = "https://reddit.com"

# Markdown removal patterns
MARKDOWN_PATTERNS = [
    (r"\*\*(.+?)\*\*", r"\1"),  # Bold
    (r"\*(.+?)\*", r"\1"),  # Italic
    (r"~~(.+?)~~", r"\1"),  # Strikethrough
    (r"`(.+?)`", r"\1"),  # Code
    (r"\[(.+?)\]\(.+?\)", r"\1"),  # Links
    (r"^#+\s*", ""),  # Headers
    (r"^>\s*", ""),  # Block quotes
    (r"^[\*\-]\s*", ""),  # List items
]


class TransformerError(Exception):
    """Exception raised for transformer-level errors.

    Attributes:
        message: Error description
        post_id: ID of post being transformed when error occurred
    """

    def __init__(self, message: str, post_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.post_id = post_id


class RedditTransformer:
    """Reddit Transformer - converts posts to Research Pool schema.

    Takes harvested posts and transforms them to the standardized
    TransformedResearch format required by the Research Pool.

    Features:
        - Field mapping to Research Pool schema
        - Auto-tag generation from content
        - Markdown removal from content
        - Content length truncation
        - Timestamp conversion

    No external dependencies - pure transformation logic.
    """

    def __init__(self, keywords: Optional[list[str]] = None):
        """Initialize transformer with optional keyword list for tagging.

        Args:
            keywords: Keywords to detect for auto-tagging (default: mushroom keywords)
        """
        self._keywords = keywords or DEFAULT_KEYWORDS

    async def transform(
        self,
        harvested_posts: list[HarvestedPost],
    ) -> list[TransformedResearch]:
        """Transform harvested posts to Research Pool schema.

        Maps Reddit-specific fields to the standardized TransformedResearch
        schema and generates tags from content.

        Args:
            harvested_posts: Posts from harvester stage

        Returns:
            List of TransformedResearch objects ready for validation
        """
        logger.info("Transforming %d posts", len(harvested_posts))

        transformed: list[TransformedResearch] = []

        for post in harvested_posts:
            try:
                item = self._transform_single(post)
                transformed.append(item)
            except Exception as e:
                logger.error(
                    "Failed to transform post %s: %s",
                    post.id,
                    e,
                )
                # Continue with remaining posts

        logger.info("Transformed %d posts successfully", len(transformed))
        return transformed

    def _transform_single(self, post: HarvestedPost) -> TransformedResearch:
        """Transform a single post to Research Pool schema.

        Args:
            post: Harvested post to transform

        Returns:
            TransformedResearch object
        """
        # Get content (body text or title for link posts)
        content = self._get_content(post)

        # Sanitize content
        content = self._sanitize_content(content)

        # Generate tags from content
        tags = self._generate_tags(post.title, content)

        # Build source metadata
        source_metadata = {
            "subreddit": post.subreddit,
            "author": post.author,
            "upvotes": post.score,
            "upvote_ratio": post.upvote_ratio,
            "comment_count": post.num_comments,
            "permalink": post.permalink,
            "is_self": post.is_self,
        }

        # Convert timestamp
        created_at = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)

        return TransformedResearch(
            source=ResearchSource.REDDIT,
            title=post.title[:500],  # Enforce max title length
            content=content,
            url=post.url,
            tags=tags,
            source_metadata=source_metadata,
            created_at=created_at,
        )

    def _get_content(self, post: HarvestedPost) -> str:
        """Extract content from post.

        For text posts, uses selftext body.
        For link posts (empty selftext), uses title as content.

        Args:
            post: Harvested post

        Returns:
            Post content string
        """
        if post.selftext and post.selftext.strip():
            return post.selftext
        # Link posts - use title as content
        return post.title

    def _sanitize_content(self, content: str) -> str:
        """Sanitize content by removing markdown and truncating.

        Args:
            content: Raw content string

        Returns:
            Sanitized content string
        """
        # Remove markdown formatting
        sanitized = content
        for pattern, replacement in MARKDOWN_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.MULTILINE)

        # Remove extra whitespace
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        # Truncate if too long
        if len(sanitized) > MAX_CONTENT_LENGTH:
            sanitized = sanitized[:MAX_CONTENT_LENGTH - 3] + "..."

        return sanitized

    def _generate_tags(self, title: str, content: str) -> list[str]:
        """Generate tags from title and content.

        Searches for mushroom keywords and generates normalized tags.

        Args:
            title: Post title
            content: Post content

        Returns:
            List of tag strings
        """
        tags: set[str] = set()
        combined_text = f"{title} {content}".lower()

        # Keyword-based tags
        keyword_to_tag = {
            "lion's mane": "lions_mane",
            "lions mane": "lions_mane",
            "chaga": "chaga",
            "reishi": "reishi",
            "cordyceps": "cordyceps",
            "shiitake": "shiitake",
            "maitake": "maitake",
        }

        for keyword, tag in keyword_to_tag.items():
            if keyword in combined_text:
                tags.add(tag)

        # Topic-based tags
        topic_keywords = {
            "cognitive": ["brain", "focus", "memory", "cognitive", "mental"],
            "immune": ["immune", "immunity", "cold", "flu", "sick"],
            "energy": ["energy", "fatigue", "tired", "stamina", "endurance"],
            "sleep": ["sleep", "insomnia", "rest", "tired"],
            "anxiety": ["anxiety", "stress", "calm", "relax"],
            "nootropic": ["nootropic", "stack", "supplement"],
        }

        for tag, keywords in topic_keywords.items():
            if any(kw in combined_text for kw in keywords):
                tags.add(tag)

        # Subreddit-based tags (from content mentioning subreddit names)
        subreddit_tags = {
            "nootropics": "nootropics",
            "supplements": "supplements",
            "biohacking": "biohackers",
        }

        for keyword, tag in subreddit_tags.items():
            if keyword in combined_text:
                tags.add(tag)

        return sorted(list(tags))
