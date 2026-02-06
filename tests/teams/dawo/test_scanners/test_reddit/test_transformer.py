"""Tests for Reddit Transformer.

Tests:
    - Transformer initialization
    - Field mapping
    - Content sanitization
    - Tag generation
"""

import pytest
from datetime import datetime, timezone

from teams.dawo.scanners.reddit import HarvestedPost
from teams.dawo.scanners.reddit.transformer import RedditTransformer
from teams.dawo.research import TransformedResearch, ResearchSource


class TestRedditTransformerInit:
    """Tests for RedditTransformer initialization."""

    def test_transformer_creation(self) -> None:
        """Transformer should be created with default keywords."""
        transformer = RedditTransformer()
        assert transformer._keywords is not None
        assert len(transformer._keywords) > 0

    def test_transformer_custom_keywords(self) -> None:
        """Transformer should accept custom keywords."""
        keywords = ["test", "keyword"]
        transformer = RedditTransformer(keywords=keywords)
        assert transformer._keywords == keywords


class TestRedditTransformerTransform:
    """Tests for transform() method."""

    @pytest.mark.asyncio
    async def test_transform_returns_list(
        self,
        harvested_post: HarvestedPost,
    ) -> None:
        """Transform should return list of TransformedResearch."""
        transformer = RedditTransformer()
        result = await transformer.transform([harvested_post])

        assert len(result) == 1
        assert isinstance(result[0], TransformedResearch)

    @pytest.mark.asyncio
    async def test_transform_empty_list(self) -> None:
        """Transform with empty list should return empty list."""
        transformer = RedditTransformer()
        result = await transformer.transform([])

        assert result == []

    @pytest.mark.asyncio
    async def test_transform_maps_source(
        self,
        harvested_post: HarvestedPost,
    ) -> None:
        """Source should be set to REDDIT."""
        transformer = RedditTransformer()
        result = await transformer.transform([harvested_post])

        assert result[0].source == ResearchSource.REDDIT

    @pytest.mark.asyncio
    async def test_transform_maps_fields(
        self,
        harvested_post: HarvestedPost,
    ) -> None:
        """All required fields should be mapped correctly."""
        transformer = RedditTransformer()
        result = await transformer.transform([harvested_post])

        item = result[0]
        assert item.title == harvested_post.title
        assert item.url == harvested_post.url
        assert isinstance(item.created_at, datetime)

    @pytest.mark.asyncio
    async def test_transform_includes_metadata(
        self,
        harvested_post: HarvestedPost,
    ) -> None:
        """Source metadata should include Reddit-specific fields."""
        transformer = RedditTransformer()
        result = await transformer.transform([harvested_post])

        metadata = result[0].source_metadata
        assert "subreddit" in metadata
        assert "author" in metadata
        assert "upvotes" in metadata
        assert "upvote_ratio" in metadata
        assert "comment_count" in metadata
        assert "permalink" in metadata


class TestRedditTransformerContent:
    """Tests for content handling."""

    @pytest.mark.asyncio
    async def test_uses_selftext_as_content(self) -> None:
        """Text posts should use selftext as content."""
        post = HarvestedPost(
            id="test123",
            subreddit="Test",
            title="Title",
            selftext="This is the body content",
            author="user",
            score=100,
            permalink="/r/Test/comments/test123/",
            url="https://reddit.com/r/Test/comments/test123/",
            created_utc=1707177600,
        )

        transformer = RedditTransformer()
        result = await transformer.transform([post])

        assert "body content" in result[0].content

    @pytest.mark.asyncio
    async def test_uses_title_for_link_posts(self) -> None:
        """Link posts (empty selftext) should use title as content."""
        post = HarvestedPost(
            id="test123",
            subreddit="Test",
            title="Link post title",
            selftext="",  # Empty for link posts
            author="user",
            score=100,
            permalink="/r/Test/comments/test123/",
            url="https://reddit.com/r/Test/comments/test123/",
            created_utc=1707177600,
            is_self=False,
        )

        transformer = RedditTransformer()
        result = await transformer.transform([post])

        assert result[0].content == "Link post title"

    @pytest.mark.asyncio
    async def test_sanitizes_markdown(self) -> None:
        """Markdown formatting should be removed."""
        post = HarvestedPost(
            id="test123",
            subreddit="Test",
            title="Title",
            selftext="**Bold** and *italic* and [link](http://example.com)",
            author="user",
            score=100,
            permalink="/r/Test/comments/test123/",
            url="https://reddit.com/r/Test/comments/test123/",
            created_utc=1707177600,
        )

        transformer = RedditTransformer()
        result = await transformer.transform([post])

        # Markdown should be stripped
        assert "**" not in result[0].content
        assert "*" not in result[0].content
        assert "[link]" not in result[0].content

    @pytest.mark.asyncio
    async def test_truncates_long_content(self) -> None:
        """Content exceeding max length should be truncated."""
        long_text = "x" * 15000  # Exceeds MAX_CONTENT_LENGTH
        post = HarvestedPost(
            id="test123",
            subreddit="Test",
            title="Title",
            selftext=long_text,
            author="user",
            score=100,
            permalink="/r/Test/comments/test123/",
            url="https://reddit.com/r/Test/comments/test123/",
            created_utc=1707177600,
        )

        transformer = RedditTransformer()
        result = await transformer.transform([post])

        assert len(result[0].content) <= 10000
        assert result[0].content.endswith("...")


class TestRedditTransformerTags:
    """Tests for tag generation."""

    @pytest.mark.asyncio
    async def test_generates_mushroom_tags(self) -> None:
        """Mushroom keywords should generate tags."""
        post = HarvestedPost(
            id="test123",
            subreddit="Nootropics",
            title="My experience with lion's mane and chaga",
            selftext="Been taking lion's mane for focus",
            author="user",
            score=100,
            permalink="/r/Nootropics/comments/test123/",
            url="https://reddit.com/r/Nootropics/comments/test123/",
            created_utc=1707177600,
        )

        transformer = RedditTransformer()
        result = await transformer.transform([post])

        tags = result[0].tags
        assert "lions_mane" in tags
        assert "chaga" in tags

    @pytest.mark.asyncio
    async def test_generates_topic_tags(self) -> None:
        """Topic keywords should generate tags."""
        post = HarvestedPost(
            id="test123",
            subreddit="Nootropics",
            title="Lion's mane for brain fog and focus",
            selftext="Improved my cognitive function",
            author="user",
            score=100,
            permalink="/r/Nootropics/comments/test123/",
            url="https://reddit.com/r/Nootropics/comments/test123/",
            created_utc=1707177600,
        )

        transformer = RedditTransformer()
        result = await transformer.transform([post])

        tags = result[0].tags
        assert "cognitive" in tags

    @pytest.mark.asyncio
    async def test_tags_are_sorted(self) -> None:
        """Generated tags should be sorted alphabetically."""
        post = HarvestedPost(
            id="test123",
            subreddit="Nootropics",
            title="Chaga, lion's mane, and reishi stack",
            selftext="My nootropic supplement stack",
            author="user",
            score=100,
            permalink="/r/Nootropics/comments/test123/",
            url="https://reddit.com/r/Nootropics/comments/test123/",
            created_utc=1707177600,
        )

        transformer = RedditTransformer()
        result = await transformer.transform([post])

        tags = result[0].tags
        assert tags == sorted(tags)
