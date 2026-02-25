"""Configuration for B2B Lead Research Scanner.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Provides configuration dataclasses for:
- HunterClientConfig: Hunter.io API credentials
- LeadScannerConfig: Scanner behavior settings
"""

from dataclasses import dataclass, field


# Configuration constants
DEFAULT_MIN_CONFIDENCE = 0.7
DEFAULT_MAX_LEADS_PER_SCAN = 50
DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE = 30  # Hunter.io Starter plan


@dataclass
class HunterClientConfig:
    """Hunter.io API client configuration.

    Credentials should be loaded from environment variables,
    NEVER hardcoded in source code.

    Attributes:
        api_key: Hunter.io API key
        base_url: API base URL (default: https://api.hunter.io/v2)
        timeout_seconds: Request timeout (default: 30)
        rate_limit_per_minute: Max requests per minute (default: 30)
    """

    api_key: str
    base_url: str = "https://api.hunter.io/v2"
    timeout_seconds: int = 30
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE


@dataclass
class LeadScannerConfig:
    """B2B Lead Scanner configuration.

    Loaded from config/dawo_lead_scanner.json via dependency injection.

    Attributes:
        industries: Target industries to search for
        search_keywords: Keywords for company search
        countries: Priority list of countries (in order)
        min_confidence: Minimum confidence for lead inclusion
        max_leads_per_scan: Maximum leads per scan cycle
        required_fields: Fields that must be present for valid lead
        preferred_positions: Job titles to prioritize
        rate_limit_per_minute: API rate limit
    """

    # Target industries for B2B retail partners
    industries: list[str] = field(default_factory=lambda: [
        "health food store",
        "wellness retailer",
        "organic shop",
        "specialty grocery",
        "supplement store",
        "natural products retailer",
        "health store",
        "apothecary",
    ])

    # Keywords for company search
    search_keywords: list[str] = field(default_factory=lambda: [
        "helsekost",  # Norwegian: health food
        "naturkost",  # Norwegian: natural food
        "kosttilskudd",  # Norwegian: dietary supplement
        "organic shop",
        "wellness store",
        "health food",
        "supplement retailer",
    ])

    # Location priorities (in order)
    countries: list[str] = field(default_factory=lambda: [
        "Norway",
        "Sweden",
        "Denmark",
        "Finland",
    ])

    # Minimum confidence for lead inclusion
    min_confidence: float = DEFAULT_MIN_CONFIDENCE

    # Maximum leads per scan cycle
    max_leads_per_scan: int = DEFAULT_MAX_LEADS_PER_SCAN

    # Required fields for valid lead
    required_fields: list[str] = field(default_factory=lambda: [
        "email",
        "company",
    ])

    # Preferred job titles (prioritize decision-makers)
    preferred_positions: list[str] = field(default_factory=lambda: [
        "owner",
        "ceo",
        "founder",
        "manager",
        "director",
        "buyer",
        "purchasing",
        "innkjøp",  # Norwegian: purchasing
        "daglig leder",  # Norwegian: general manager
    ])

    # API rate limit
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE

    # Schedule (for reference - actual scheduling done by ARQ)
    schedule_cron: str = "0 7 * * 1"  # Monday 7 AM
    schedule_timezone: str = "Europe/Oslo"

    def get_search_domains(self) -> list[str]:
        """Generate list of domains to search based on config.

        Returns domains for major retailers in target countries.
        This is a seed list - the scanner may discover more.
        """
        # Seed domains for Nordic health retailers
        # These are examples - actual list should be in config file
        return [
            # Norway
            "life.no",
            "sunkost.no",
            "helsekosten.no",
            # Sweden
            "life.se",
            "halsokost.se",
            # Denmark
            "helsam.dk",
            # Finland
            "ruohonjuuri.fi",
        ]
