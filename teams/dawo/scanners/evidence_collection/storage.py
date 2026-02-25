"""Evidence Storage Service (Story 6-8, Task 6).

Handles screenshot file I/O with SHA-256 integrity hashing.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from teams.dawo.scanners.evidence_collection.config import EvidenceCollectionConfig

logger = logging.getLogger(__name__)


class EvidenceStorageService:
    """Service for storing and verifying evidence screenshots.

    Stores screenshots with SHA-256 hash verification and
    read-only file permissions (best-effort on Windows).

    Args:
        config: Evidence collection configuration.
    """

    def __init__(self, config: EvidenceCollectionConfig) -> None:
        self._config = config

    async def store_screenshot(
        self, screenshot_bytes: bytes, evidence_id: UUID
    ) -> tuple[str, str, int]:
        """Store screenshot to filesystem with integrity verification.

        Computes hash BEFORE writing, writes to disk, sets read-only,
        then verifies by re-reading and comparing hash.

        Args:
            screenshot_bytes: Raw screenshot image bytes.
            evidence_id: UUID to use as filename.

        Returns:
            Tuple of (relative_path, sha256_hash, file_size_bytes).

        Raises:
            RuntimeError: If hash verification fails after write.
        """
        # 1. Hash BEFORE writing
        sha256_hash = hashlib.sha256(screenshot_bytes).hexdigest()

        # 2. Build path: {base}/{YYYY-MM}/{evidence_id}.{format}
        now = datetime.now(UTC)
        month_dir = now.strftime("%Y-%m")
        relative_path = (
            f"{self._config.storage_base_path}/{month_dir}/"
            f"{evidence_id}.{self._config.screenshot_format}"
        )
        output_path = Path(relative_path)

        # 3. Create directory and write (non-blocking)
        await asyncio.to_thread(
            output_path.parent.mkdir, parents=True, exist_ok=True
        )
        await asyncio.to_thread(output_path.write_bytes, screenshot_bytes)

        # 4. Set read-only (best-effort on Windows)
        try:
            output_path.chmod(0o444)
        except OSError:
            logger.warning("Could not set read-only: %s", output_path)

        # 5. Verify by re-reading (non-blocking)
        written_bytes = await asyncio.to_thread(output_path.read_bytes)
        verification_hash = hashlib.sha256(written_bytes).hexdigest()
        if sha256_hash != verification_hash:
            raise RuntimeError(f"Hash mismatch after write for {output_path}")

        file_size = len(screenshot_bytes)
        logger.debug(
            "Stored screenshot: path=%s hash=%s size=%d",
            relative_path,
            sha256_hash,
            file_size,
        )

        return relative_path, sha256_hash, file_size

    async def verify_integrity(
        self, screenshot_path: str, expected_hash: str
    ) -> bool:
        """Verify screenshot file integrity against expected hash.

        Args:
            screenshot_path: Path to screenshot file.
            expected_hash: Expected SHA-256 hex digest.

        Returns:
            True if hash matches, False if mismatch or file missing.
        """
        path = Path(screenshot_path)
        exists = await asyncio.to_thread(path.exists)
        if not exists:
            logger.warning("Evidence file missing: %s", screenshot_path)
            return False

        try:
            file_bytes = await asyncio.to_thread(path.read_bytes)
            actual_hash = hashlib.sha256(file_bytes).hexdigest()
            matches = actual_hash == expected_hash
            if not matches:
                logger.error(
                    "Evidence hash mismatch: path=%s expected=%s actual=%s",
                    screenshot_path,
                    expected_hash,
                    actual_hash,
                )
            return matches
        except OSError as e:
            logger.error("Error reading evidence file %s: %s", screenshot_path, e)
            return False


__all__ = [
    "EvidenceStorageService",
]
