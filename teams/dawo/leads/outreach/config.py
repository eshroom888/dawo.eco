"""Configuration for Outreach Draft Generator.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides configuration dataclasses for:
- OutreachConfig: Main outreach service configuration
- TemplateConfig: Template and personalization settings
"""

from dataclasses import dataclass, field


# Configuration constants
MIN_CONFIDENCE_THRESHOLD = 6  # AC #1: confidence >= 6 for outreach
MIN_WORD_COUNT = 150  # AC #2: draft length 150-250 words
MAX_WORD_COUNT = 250  # AC #2: draft length 150-250 words
MIN_PERSONALIZATION_TOKENS = 2  # AC #2: minimum personalization elements
DEFAULT_BATCH_SIZE = 10


# Norwegian CTA options
DEFAULT_CTA_OPTIONS = {
    "meeting_request": "Kan vi ta en kort samtale for å diskutere hvordan DAWO kan styrke sortimentet deres?",
    "sample_offer": "Vi sender gjerne et prøveprodukt så dere kan oppleve kvaliteten selv.",
    "catalog_request": "Jeg legger ved vår produktkatalog - hvilke produkter ville være mest relevante for dere?",
}


# Norwegian value propositions
DEFAULT_VALUE_PROPOSITIONS = [
    "Premium norsk kvalitet med full sporbarhet",
    "Funksjonelle sopp-ekstrakter av høyeste kvalitet",
    "Bærekraftig produksjon med fokus på renhet",
    "Dokumentert effekt basert på tradisjonell bruk",
]


@dataclass
class TemplateConfig:
    """Template and personalization configuration.

    Defines template options, CTAs, and value propositions.

    Attributes:
        cta_options: Available CTA text options by type
        value_propositions: Norwegian value proposition options
        default_sender_name: Default sender name for emails
        default_signature: Default email signature
    """

    cta_options: dict[str, str] = field(
        default_factory=lambda: DEFAULT_CTA_OPTIONS.copy()
    )
    value_propositions: list[str] = field(
        default_factory=lambda: DEFAULT_VALUE_PROPOSITIONS.copy()
    )
    default_sender_name: str = "DAWO Team"
    default_signature: str = "Med vennlig hilsen,\nDAWO Team"


@dataclass
class OutreachConfig:
    """Outreach Draft Generator service configuration.

    Loaded via dependency injection from Team Builder.
    NEVER loads config files directly.

    Attributes:
        min_confidence_threshold: Minimum confidence score for outreach
        min_word_count: Minimum draft word count (AC #2)
        max_word_count: Maximum draft word count (AC #2)
        min_personalization_tokens: Minimum personalization elements required
        batch_size: Number of leads to process per batch
        template_config: Template configuration
        schedule_cron: Cron schedule for outreach agent
        schedule_timezone: Timezone for scheduling
    """

    # Qualification thresholds
    min_confidence_threshold: float = float(MIN_CONFIDENCE_THRESHOLD)

    # Draft requirements (AC #2)
    min_word_count: int = MIN_WORD_COUNT
    max_word_count: int = MAX_WORD_COUNT
    min_personalization_tokens: int = MIN_PERSONALIZATION_TOKENS

    # Pipeline settings
    batch_size: int = DEFAULT_BATCH_SIZE

    # Template configuration
    template_config: TemplateConfig = field(default_factory=TemplateConfig)

    # Schedule (for reference - actual scheduling done by ARQ)
    # Daily 9 AM Oslo time (after enrichment completes at 8 AM)
    schedule_cron: str = "0 9 * * *"
    schedule_timezone: str = "Europe/Oslo"

    def is_word_count_valid(self, word_count: int) -> bool:
        """Check if word count is within valid range.

        Args:
            word_count: Number of words in draft

        Returns:
            True if word count is between min and max (inclusive)
        """
        return self.min_word_count <= word_count <= self.max_word_count

    def is_qualified_for_outreach(self, confidence_score: float) -> bool:
        """Check if lead is qualified for outreach.

        Args:
            confidence_score: Lead's confidence score (0-10)

        Returns:
            True if confidence meets threshold
        """
        return confidence_score >= self.min_confidence_threshold
