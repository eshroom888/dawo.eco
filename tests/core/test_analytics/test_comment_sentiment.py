"""Tests for CommentSentimentScorer.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 3.4: Write sentiment scorer tests.
"""

from datetime import UTC, datetime

import pytest

from core.analytics.comment_sentiment import (
    CommentSentimentResult,
    CommentSentimentScorer,
)
from integrations.instagram.client import InstagramComment


def _make_comment(text: str, username: str = "user1") -> InstagramComment:
    """Factory for creating test comments."""
    return InstagramComment(
        comment_id=f"comment-{id(text)}",
        text=text,
        username=username,
        timestamp=datetime.now(UTC),
    )


class TestCommentSentimentResult:
    """Tests for CommentSentimentResult frozen dataclass (Task 3.3)."""

    def test_frozen(self) -> None:
        result = CommentSentimentResult(
            positive_count=5,
            negative_count=2,
            neutral_count=3,
            total_count=10,
            sentiment_ratio=0.71,
            score=7.1,
        )
        with pytest.raises(AttributeError):
            result.score = 8.0  # type: ignore[misc]

    def test_default_values(self) -> None:
        result = CommentSentimentResult(
            positive_count=0,
            negative_count=0,
            neutral_count=0,
            total_count=0,
            sentiment_ratio=0.0,
            score=5.0,
        )
        assert result.total_count == 0


class TestCommentSentimentScorerInit:
    """Test scorer initialization (Task 3.2)."""

    def test_no_dependencies(self) -> None:
        scorer = CommentSentimentScorer()
        assert scorer is not None

    def test_has_positive_words(self) -> None:
        scorer = CommentSentimentScorer()
        assert len(scorer._positive_words) > 0

    def test_has_negative_words(self) -> None:
        scorer = CommentSentimentScorer()
        assert len(scorer._negative_words) > 0

    def test_positive_includes_norwegian(self) -> None:
        scorer = CommentSentimentScorer()
        assert "fantastisk" in scorer._positive_words

    def test_positive_includes_english(self) -> None:
        scorer = CommentSentimentScorer()
        assert "great" in scorer._positive_words

    def test_negative_includes_norwegian(self) -> None:
        scorer = CommentSentimentScorer()
        assert "skuffet" in scorer._negative_words

    def test_negative_includes_english(self) -> None:
        scorer = CommentSentimentScorer()
        assert "bad" in scorer._negative_words


class TestScoreComments:
    """Tests for score_comments method (Task 3.2)."""

    def test_empty_comments_returns_neutral(self) -> None:
        scorer = CommentSentimentScorer()
        result = scorer.score_comments([])
        assert result.score == 5.0
        assert result.total_count == 0
        assert result.sentiment_ratio == 0.5

    def test_all_positive_comments(self) -> None:
        scorer = CommentSentimentScorer()
        comments = [
            _make_comment("This is amazing and great!"),
            _make_comment("I love this product, excellent quality"),
        ]
        result = scorer.score_comments(comments)
        assert result.positive_count > 0
        assert result.negative_count == 0
        assert result.score > 5.0

    def test_all_negative_comments(self) -> None:
        scorer = CommentSentimentScorer()
        comments = [
            _make_comment("This is terrible and bad"),
            _make_comment("Such a scam, very disappointing"),
        ]
        result = scorer.score_comments(comments)
        assert result.negative_count > 0
        assert result.positive_count == 0
        assert result.score < 5.0

    def test_mixed_comments(self) -> None:
        scorer = CommentSentimentScorer()
        comments = [
            _make_comment("Great product!"),
            _make_comment("Terrible experience"),
            _make_comment("Just okay, nothing special"),
        ]
        result = scorer.score_comments(comments)
        assert result.positive_count > 0
        assert result.negative_count > 0
        assert result.total_count == 3

    def test_norwegian_positive(self) -> None:
        scorer = CommentSentimentScorer()
        comments = [_make_comment("Fantastisk produkt, anbefaler dette")]
        result = scorer.score_comments(comments)
        assert result.positive_count > 0
        assert result.score > 5.0

    def test_norwegian_negative(self) -> None:
        scorer = CommentSentimentScorer()
        comments = [_make_comment("Veldig skuffet over kvaliteten")]
        result = scorer.score_comments(comments)
        assert result.negative_count > 0
        assert result.score < 5.0

    def test_negation_flips_positive_to_negative(self) -> None:
        """'not great' should be negative, not positive."""
        scorer = CommentSentimentScorer()
        comments = [_make_comment("not great at all")]
        result = scorer.score_comments(comments)
        assert result.negative_count > 0
        assert result.positive_count == 0

    def test_norwegian_negation(self) -> None:
        """'ikke bra' should be negative."""
        scorer = CommentSentimentScorer()
        comments = [_make_comment("ikke bra i det hele tatt")]
        result = scorer.score_comments(comments)
        assert result.negative_count > 0
        assert result.positive_count == 0

    def test_negation_flips_negative_to_positive(self) -> None:
        """'not bad' should be positive."""
        scorer = CommentSentimentScorer()
        comments = [_make_comment("not bad at all")]
        result = scorer.score_comments(comments)
        assert result.positive_count > 0
        assert result.negative_count == 0

    def test_score_range_clamped(self) -> None:
        scorer = CommentSentimentScorer()
        # Many positive comments
        comments = [
            _make_comment("Amazing great excellent wonderful love perfect")
            for _ in range(10)
        ]
        result = scorer.score_comments(comments)
        assert 0.0 <= result.score <= 10.0

    def test_neutral_comments_counted(self) -> None:
        scorer = CommentSentimentScorer()
        comments = [_make_comment("I bought this yesterday")]
        result = scorer.score_comments(comments)
        assert result.neutral_count == 1
        assert result.total_count == 1

    def test_punctuation_stripped(self) -> None:
        """Punctuation should not prevent word matching."""
        scorer = CommentSentimentScorer()
        comments = [_make_comment("great! amazing!!! love...")]
        result = scorer.score_comments(comments)
        assert result.positive_count > 0

    def test_case_insensitive(self) -> None:
        scorer = CommentSentimentScorer()
        comments = [_make_comment("GREAT product, AMAZING quality")]
        result = scorer.score_comments(comments)
        assert result.positive_count > 0

    def test_sentiment_ratio_calculation(self) -> None:
        scorer = CommentSentimentScorer()
        comments = [
            _make_comment("great"),
            _make_comment("bad"),
        ]
        result = scorer.score_comments(comments)
        # 1 positive, 1 negative -> ratio = 1/(1+1) = 0.5
        assert result.sentiment_ratio == 0.5
