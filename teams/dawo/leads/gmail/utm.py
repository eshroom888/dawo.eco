"""UTM Parameter Injector for email tracking.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Injects UTM tracking parameters into URLs found in email body text.
Preserves existing query parameters and skips mailto: links.
"""

import logging
import re
from typing import Optional
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from uuid import UUID

logger = logging.getLogger(__name__)


class UTMInjector:
    """Inject UTM tracking parameters into email URLs.

    Finds all HTTP(S) URLs in email body and appends UTM parameters
    for campaign tracking. Skips mailto: links and preserves
    existing query parameters.
    """

    URL_PATTERN = re.compile(r'https?://[^\s<>"\']+')

    def inject_utm(
        self,
        body: str,
        lead_id: UUID,
        campaign: str = "b2b_outreach",
    ) -> str:
        """Add UTM params to all URLs in email body.

        Args:
            body: Email body text
            lead_id: Lead UUID for utm_content
            campaign: Campaign name for utm_campaign

        Returns:
            Body with UTM parameters appended to URLs
        """
        def replace_url(match: re.Match) -> str:
            url = match.group(0)
            if url.startswith("mailto:"):
                return url
            return self._add_utm_to_url(url, lead_id, campaign)

        return self.URL_PATTERN.sub(replace_url, body)

    def build_utm_params(
        self,
        lead_id: UUID,
        campaign: str = "b2b_outreach",
    ) -> dict:
        """Build standardized UTM parameter dict.

        Args:
            lead_id: Lead UUID
            campaign: Campaign name

        Returns:
            Dict of UTM parameters
        """
        return {
            "utm_source": "email",
            "utm_medium": "outreach",
            "utm_campaign": campaign,
            "utm_content": str(lead_id),
        }

    def _add_utm_to_url(self, url: str, lead_id: UUID, campaign: str) -> str:
        """Add UTM parameters to a single URL.

        Preserves existing query parameters.

        Args:
            url: URL to modify
            lead_id: Lead UUID
            campaign: Campaign name

        Returns:
            URL with UTM parameters
        """
        parsed = urlparse(url)
        existing_params = parse_qs(parsed.query)
        utm_params = self.build_utm_params(lead_id, campaign)

        # Merge: UTM params overwrite existing UTM params
        for key, value in utm_params.items():
            existing_params[key] = [value]

        new_query = urlencode(existing_params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))


__all__ = [
    "UTMInjector",
]
