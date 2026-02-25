"""Email Signature Builder.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Builds email signatures and GDPR footers for outreach emails.
Norwegian Marketing Act + GDPR compliant.
"""

import logging

from teams.dawo.leads.gmail.config import GmailConfig

logger = logging.getLogger(__name__)


class SignatureBuilder:
    """Builds email signatures and GDPR compliance footers.

    Generates Norwegian-language signatures with:
    - Sender identification
    - Company details (GDPR requirement)
    - Unsubscribe mechanism
    - "Why you received this" explanation

    Configuration is injected via GmailConfig.
    """

    def __init__(self, config: GmailConfig) -> None:
        """Initialize with injected configuration.

        Args:
            config: Gmail configuration with sender details
        """
        self._config = config

    def build_signature(self) -> str:
        """Build email signature block.

        Returns:
            Formatted signature string
        """
        return (
            f"\n---\n"
            f"{self._config.sender_name}\n"
            f"{self._config.sender_role}\n"
            f"DAWO | {self._config.company_name}\n"
            f"{self._config.company_address}\n"
            f"{self._config.sender_email}"
        )

    def build_gdpr_footer(self, unsubscribe_url: str = "") -> str:
        """Build GDPR compliance footer.

        Required by Norwegian Marketing Act and GDPR for B2B outreach.

        Args:
            unsubscribe_url: One-click unsubscribe URL (optional,
                falls back to reply-based unsubscribe)

        Returns:
            Formatted GDPR footer string
        """
        unsubscribe_text = (
            f"Klikk her for å melde deg av: {unsubscribe_url}"
            if unsubscribe_url
            else 'Ikke interessert? Svar på denne e-posten med "avmeld" '
                 "så fjerner vi deg umiddelbart."
        )

        return (
            f"\n---\n"
            f"Hvorfor mottok du denne e-posten?\n"
            f"Vi kontakter deg fordi vi mener DAWO-produktene "
            f"kan være relevante for din virksomhet.\n"
            f"\n"
            f"{unsubscribe_text}\n"
            f"\n"
            f"{self._config.company_name} | {self._config.company_address}"
        )

    def build_full_footer(self, unsubscribe_url: str = "") -> str:
        """Build complete footer: signature + GDPR footer.

        Args:
            unsubscribe_url: Optional unsubscribe URL

        Returns:
            Combined signature and GDPR footer
        """
        return self.build_signature() + self.build_gdpr_footer(unsubscribe_url)


__all__ = [
    "SignatureBuilder",
]
