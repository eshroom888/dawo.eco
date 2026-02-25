"""Evidence Download Service (Story 6-9, Task 5).

Creates downloadable evidence packages (ZIP with screenshot + metadata).
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService

if TYPE_CHECKING:
    from core.regulatory.models import Evidence

logger = logging.getLogger(__name__)


class EvidenceDownloadService:
    """Creates downloadable evidence packages (ZIP with screenshot + metadata).

    Args:
        storage_service: For integrity verification.
    """

    def __init__(self, storage_service: EvidenceStorageService) -> None:
        self._storage = storage_service

    async def create_evidence_package(self, evidence: Evidence) -> bytes:
        """Create ZIP package: screenshot.png + metadata.json + integrity.txt.

        Args:
            evidence: Evidence ORM object with screenshot data.

        Returns:
            ZIP file bytes.

        Raises:
            FileNotFoundError: If screenshot file doesn't exist.
            RuntimeError: If screenshot hash doesn't match (integrity failure).
        """
        # 1. Read and verify screenshot integrity
        screenshot_path = Path(evidence.screenshot_path)
        if not screenshot_path.exists():
            raise FileNotFoundError(
                f"Screenshot not found: {evidence.screenshot_path}"
            )

        screenshot_bytes = screenshot_path.read_bytes()
        actual_hash = hashlib.sha256(screenshot_bytes).hexdigest()
        if actual_hash != evidence.screenshot_hash:
            raise RuntimeError(
                f"Integrity check failed for evidence {evidence.id}"
            )

        # 2. Build metadata JSON
        metadata = {
            "evidence_id": str(evidence.id),
            "competitor_name": evidence.competitor_name,
            "source_url": evidence.source_url,
            "source_type": evidence.source_type,
            "claim_text": evidence.claim_text,
            "claim_category": evidence.claim_category,
            "violation_type": evidence.violation_type,
            "severity": evidence.severity,
            "regulation_violated": evidence.regulation_violated,
            "confidence": evidence.confidence,
            "captured_at": evidence.captured_at.isoformat(),
            "screenshot_hash": evidence.screenshot_hash,
            "screenshot_size_bytes": evidence.screenshot_size_bytes,
        }

        # 3. Build integrity file
        integrity_text = (
            f"SHA-256: {evidence.screenshot_hash}\n"
            f"File: screenshot.png\n"
            f"Captured: {evidence.captured_at.isoformat()}\n"
            f"Verify: sha256sum screenshot.png\n"
        )

        # 4. Create ZIP
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("screenshot.png", screenshot_bytes)
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))
            zf.writestr("integrity.txt", integrity_text)

        logger.debug("Created evidence package for %s", evidence.id)
        return buffer.getvalue()


__all__ = [
    "EvidenceDownloadService",
]
