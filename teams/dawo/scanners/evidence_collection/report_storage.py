"""Report Storage Service (Story 6-10, Task 5).

Handles saving, retrieving, and listing generated violation report PDFs.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from teams.dawo.scanners.evidence_collection.report_config import (
    ViolationReportConfig,
)
from teams.dawo.scanners.evidence_collection.report_schemas import (
    ReportMetadata,
    ReportResult,
    ReportStorageProtocol,
)

logger = logging.getLogger(__name__)


class ReportStorageService:
    """Service for storing and retrieving generated PDF reports.

    Reports are organized by month: {storage_path}/{YYYY-MM}/{report_id}.pdf

    Args:
        config: Report configuration with storage_path.
    """

    def __init__(self, config: ViolationReportConfig) -> None:
        self._config = config

    async def save_report(self, result: ReportResult) -> str:
        """Save a generated report PDF to storage.

        Args:
            result: Report generation result with PDF bytes.

        Returns:
            Relative file path where the report was saved.
        """
        now = datetime.now(UTC)
        month_dir = now.strftime("%Y-%m")
        relative_path = (
            f"{self._config.storage_path}/{month_dir}/{result.report_id}.pdf"
        )
        output_path = Path(relative_path)

        await asyncio.to_thread(
            output_path.parent.mkdir, parents=True, exist_ok=True
        )
        await asyncio.to_thread(output_path.write_bytes, result.pdf_bytes)

        # Save metadata sidecar for efficient listing
        meta_path = output_path.with_suffix(".json")
        meta_data = {
            "report_id": str(result.report_id),
            "filename": result.filename,
            "evidence_count": result.evidence_count,
            "template_type": result.template_type,
            "generated_at": result.generated_at.isoformat(),
            "sha256_hash": result.sha256_hash,
            "page_count": result.page_count,
            "file_size_bytes": len(result.pdf_bytes),
        }
        await asyncio.to_thread(
            meta_path.write_text, json.dumps(meta_data), "utf-8"
        )

        logger.debug(
            "Saved report %s to %s (%d bytes)",
            result.report_id,
            relative_path,
            len(result.pdf_bytes),
        )
        return relative_path

    async def get_report(self, report_id: UUID) -> bytes | None:
        """Retrieve a report's PDF bytes by ID.

        Searches storage directory for the report file.

        Args:
            report_id: Report identifier.

        Returns:
            PDF bytes or None if not found.
        """
        base_path = Path(self._config.storage_path)
        if not await asyncio.to_thread(base_path.exists):
            return None

        # Search month directories for the report
        pattern = f"**/{report_id}.pdf"
        matches = await asyncio.to_thread(
            lambda: list(base_path.glob(pattern))
        )

        if not matches:
            return None

        return await asyncio.to_thread(matches[0].read_bytes)

    async def list_reports(
        self, limit: int = 25, offset: int = 0
    ) -> tuple[list[ReportMetadata], int]:
        """List stored reports with pagination.

        Scans storage directory for PDF files and returns metadata
        sorted by modification time (most recent first).

        Args:
            limit: Maximum reports to return.
            offset: Number of reports to skip.

        Returns:
            Tuple of (report metadata list, total count).
        """
        base_path = Path(self._config.storage_path)
        if not await asyncio.to_thread(base_path.exists):
            return [], 0

        all_pdfs = await asyncio.to_thread(
            lambda: sorted(
                base_path.glob("**/*.pdf"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        )

        total = len(all_pdfs)
        page_pdfs = all_pdfs[offset : offset + limit]

        metadata_list = []
        for pdf_path in page_pdfs:
            meta = await self._build_metadata(pdf_path)
            if meta is not None:
                metadata_list.append(meta)

        return metadata_list, total

    async def verify_report_integrity(
        self, report_id: UUID, expected_hash: str
    ) -> bool:
        """Verify report file integrity via SHA-256.

        Args:
            report_id: Report identifier.
            expected_hash: Expected SHA-256 hex digest.

        Returns:
            True if hash matches, False otherwise.
        """
        pdf_bytes = await self.get_report(report_id)
        if pdf_bytes is None:
            return False

        actual_hash = hashlib.sha256(pdf_bytes).hexdigest()
        return actual_hash == expected_hash

    async def _build_metadata(self, pdf_path: Path) -> ReportMetadata | None:
        """Build ReportMetadata from a PDF file path.

        Reads the JSON sidecar if available for accurate metadata.
        Falls back to file-system heuristics for legacy reports.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            ReportMetadata or None if path cannot be parsed.
        """
        try:
            report_id_str = pdf_path.stem
            report_id = UUID(report_id_str)

            # Try reading metadata sidecar first
            meta_path = pdf_path.with_suffix(".json")
            if await asyncio.to_thread(meta_path.exists):
                raw = await asyncio.to_thread(meta_path.read_text, "utf-8")
                data = json.loads(raw)
                return ReportMetadata(
                    report_id=UUID(data["report_id"]),
                    filename=data["filename"],
                    evidence_count=data["evidence_count"],
                    competitor_name=data.get("competitor_name"),
                    template_type=data["template_type"],
                    generated_at=datetime.fromisoformat(data["generated_at"]),
                    sha256_hash=data["sha256_hash"],
                    page_count=data["page_count"],
                    file_size_bytes=data["file_size_bytes"],
                )

            # Fallback: derive from file system (legacy reports without sidecar)
            stat = await asyncio.to_thread(pdf_path.stat)
            file_bytes = await asyncio.to_thread(pdf_path.read_bytes)
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()

            return ReportMetadata(
                report_id=report_id,
                filename=pdf_path.name,
                evidence_count=0,
                competitor_name=None,
                template_type="unknown",
                generated_at=datetime.fromtimestamp(
                    stat.st_mtime, tz=UTC
                ),
                sha256_hash=sha256_hash,
                page_count=0,
                file_size_bytes=stat.st_size,
            )
        except (ValueError, OSError, KeyError) as e:
            logger.warning("Could not parse report metadata from %s: %s", pdf_path, e)
            return None


__all__ = [
    "ReportStorageService",
]
