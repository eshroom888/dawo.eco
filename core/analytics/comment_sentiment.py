"""Keyword-based comment sentiment scorer.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 3.2: CommentSentimentScorer with built-in Norwegian+English word lists.

Pure Python implementation — NO external ML/NLP libraries.
Uses simple word tokenization with negation handling.
"""

import re
from dataclasses import dataclass

from integrations.instagram.client import InstagramComment


@dataclass(frozen=True)
class CommentSentimentResult:
    """Result of comment sentiment analysis.

    Task 3.3: Frozen dataclass with sentiment counts and score.

    Attributes:
        positive_count: Number of comments classified as positive
        negative_count: Number of comments classified as negative
        neutral_count: Number of comments classified as neutral
        total_count: Total comments analyzed
        sentiment_ratio: positive / (positive + negative), 0.5 if no sentiment
        score: Mapped to 0-10 scale from sentiment_ratio
    """

    positive_count: int
    negative_count: int
    neutral_count: int
    total_count: int
    sentiment_ratio: float
    score: float


# Negation words that flip polarity of the following sentiment word
_NEGATION_WORDS = frozenset({
    # English
    "not", "no", "never", "dont", "doesn't", "didn't", "wasn't",
    "weren't", "isn't", "aren't", "won't", "wouldn't", "couldn't",
    # Norwegian
    "ikke", "aldri", "ingen",
})

# Strip punctuation pattern
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


class CommentSentimentScorer:
    """Keyword-based comment sentiment scorer.

    Task 3.2: Pure Python sentiment analysis using built-in
    Norwegian + English word lists. No external dependencies.

    Scoring approach:
    - Tokenize: lowercase + strip punctuation
    - Match words against positive/negative sets
    - Handle negation: 'not'/'ikke' preceding a sentiment word flips it
    - Ratio: positive / (positive + negative)
    - Score: map ratio to 0-10 scale
    - Empty comments: neutral score 5.0
    """

    def __init__(self) -> None:
        """Initialize with built-in sentiment word lists."""
        self._positive_words: frozenset[str] = frozenset({
            # English positive (~50 words)
            "great", "good", "amazing", "excellent", "wonderful", "love",
            "perfect", "awesome", "fantastic", "beautiful", "best",
            "brilliant", "outstanding", "superb", "incredible", "impressive",
            "lovely", "nice", "happy", "pleased", "delighted", "thrilled",
            "recommend", "recommended", "quality", "favorite", "favourite",
            "exceptional", "gorgeous", "fabulous", "magnificent", "enjoy",
            "enjoyed", "helpful", "grateful", "thankful", "inspired",
            "inspiring", "elegant", "premium", "luxurious", "fresh",
            "healthy", "natural", "pure", "organic", "effective",
            "reliable", "trustworthy", "genuine", "authentic", "worth",
            # Norwegian positive (~50 words)
            "bra", "fantastisk", "elsker", "anbefaler", "god", "perfekt",
            "utmerket", "flott", "nydelig", "herlig", "strålende",
            "vidunderlig", "beste", "unik", "imponerende", "vakker",
            "deilig", "glad", "fornøyd", "begeistret", "kvalitet",
            "favoritt", "anbefalt", "sunn", "naturlig", "ren",
            "effektiv", "pålitelig", "ekte", "verdt", "kjempebra",
            "superbra", "topp", "prima", "fin", "liker", "elsket",
            "praktfull", "enestående", "utrolig", "fortreffelig",
            "glimrende", "fenomenal", "velsmakende", "frisk", "ypperlig",
            "fantastiske", "kjempe", "herlige", "nydelige", "gode",
        })

        self._negative_words: frozenset[str] = frozenset({
            # English negative (~40 words)
            "bad", "terrible", "horrible", "awful", "worst", "hate",
            "scam", "fake", "disappointed", "disappointing", "waste",
            "poor", "cheap", "broken", "useless", "disgusting",
            "overpriced", "fraud", "trash", "garbage", "regret",
            "rubbish", "pathetic", "dreadful", "unacceptable", "toxic",
            "harmful", "dangerous", "ineffective", "unreliable",
            "ugly", "nasty", "mediocre", "inferior", "defective",
            "misleading", "dishonest", "ripoff", "junk", "sucks",
            # Norwegian negative (~40 words)
            "dårlig", "skuffet", "svindel", "falsk", "forferdelig",
            "fryktelig", "elendig", "verst", "hater", "avfall",
            "billig", "ødelagt", "ubrukelig", "overpriset", "bedrageri",
            "søppel", "angrer", "uakseptabelt", "giftig", "skadelig",
            "farlig", "ineffektiv", "upålitelig", "stygg", "middelmådig",
            "underlegen", "defekt", "misvisende", "uærlig",
            "skuffende", "dårlige", "elendige", "håpløs", "verdiløs",
            "bortkastet", "mislykket", "problemer", "klager",
            "skuffelsen", "frustrerende",
        })

    def score_comments(
        self, comments: list[InstagramComment]
    ) -> CommentSentimentResult:
        """Score a list of comments for sentiment.

        Args:
            comments: List of Instagram comments to analyze.

        Returns:
            CommentSentimentResult with counts, ratio, and score.
        """
        if not comments:
            return CommentSentimentResult(
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                total_count=0,
                sentiment_ratio=0.5,
                score=5.0,
            )

        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for comment in comments:
            sentiment = self._classify_comment(comment.text)
            if sentiment > 0:
                positive_count += 1
            elif sentiment < 0:
                negative_count += 1
            else:
                neutral_count += 1

        total_count = len(comments)
        total_sentiment = positive_count + negative_count

        if total_sentiment == 0:
            sentiment_ratio = 0.5
        else:
            sentiment_ratio = positive_count / total_sentiment

        # Map ratio (0.0-1.0) to score (0-10)
        score = round(sentiment_ratio * 10.0, 1)
        score = max(0.0, min(10.0, score))

        return CommentSentimentResult(
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            total_count=total_count,
            sentiment_ratio=sentiment_ratio,
            score=score,
        )

    def _classify_comment(self, text: str) -> int:
        """Classify a single comment as positive (1), negative (-1), or neutral (0).

        Uses word matching with negation handling.

        Args:
            text: Comment text.

        Returns:
            1 for positive, -1 for negative, 0 for neutral.
        """
        words = self._tokenize(text)
        pos_hits = 0
        neg_hits = 0

        for i, word in enumerate(words):
            # Check if this word is preceded by a negation word
            negated = (
                i > 0
                and words[i - 1] in _NEGATION_WORDS
            )

            if word in self._positive_words:
                if negated:
                    neg_hits += 1
                else:
                    pos_hits += 1
            elif word in self._negative_words:
                if negated:
                    pos_hits += 1
                else:
                    neg_hits += 1

        if pos_hits > neg_hits:
            return 1
        elif neg_hits > pos_hits:
            return -1
        return 0

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words with punctuation stripped.

        Args:
            text: Raw comment text.

        Returns:
            List of lowercase word tokens.
        """
        cleaned = _PUNCT_RE.sub(" ", text.lower())
        return cleaned.split()


__all__ = [
    "CommentSentimentResult",
    "CommentSentimentScorer",
]
