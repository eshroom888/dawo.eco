"""Page change detector for Mattilsynet monitored pages.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.
Task 8: SHA-256 hash-based page change detection.
"""

import hashlib
import logging
from typing import Optional

from teams.dawo.scanners.mattilsynet.schemas import PageChangeResult

logger = logging.getLogger(__name__)


class PageChangeDetector:
    """Detects changes to monitored pages via SHA-256 hash comparison.

    Compares current content hash against a stored previous hash
    to determine if page content has changed.
    """

    def check_page(
        self,
        url: str,
        current_content: str,
        previous_hash: Optional[str],
    ) -> PageChangeResult:
        """Check if page content has changed.

        Args:
            url: Page URL
            current_content: Extracted main content text
            previous_hash: SHA-256 hash from previous check (None on first run)

        Returns:
            PageChangeResult with change status and new hash
        """
        current_hash = hashlib.sha256(
            current_content.encode("utf-8")
        ).hexdigest()

        if previous_hash is None:
            # First run — record hash without reporting change
            logger.info(
                "First check for '%s', recording baseline hash", url
            )
            return PageChangeResult(
                url=url,
                changed=False,
                current_hash=current_hash,
                content=None,
            )

        changed = current_hash != previous_hash

        if changed:
            logger.info("Page change detected for '%s'", url)

        return PageChangeResult(
            url=url,
            changed=changed,
            current_hash=current_hash,
            content=current_content if changed else None,
        )


__all__ = [
    "PageChangeDetector",
]
