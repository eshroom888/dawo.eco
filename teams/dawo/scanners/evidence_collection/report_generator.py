"""WeasyPrint PDF Generator (Story 6-10, Task 4).

Generates violation report PDFs from evidence data using Jinja2 templates
and WeasyPrint for HTML-to-PDF conversion.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from teams.dawo.scanners.evidence_collection.report_config import (
    ViolationReportConfig,
)
from teams.dawo.scanners.evidence_collection.report_schemas import (
    PDFGeneratorProtocol,
    ReportResult,
    ViolationReportRequest,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from core.regulatory.models import Evidence, EvidenceAuditLog
    from teams.dawo.scanners.evidence_collection.repository import (
        EvidenceRepository,
    )
    from teams.dawo.scanners.evidence_collection.storage import (
        EvidenceStorageService,
    )

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _import_weasyprint_html() -> type:
    """Lazy import WeasyPrint HTML class.

    Returns:
        The weasyprint.HTML class.
    """
    from weasyprint import HTML  # noqa: WPS433

    return HTML


class WeasyPrintPDFGenerator:
    """Generates violation report PDFs via Jinja2 + WeasyPrint.

    Implements PDFGeneratorProtocol. WeasyPrint is imported lazily
    to allow tests to run without system dependencies.

    Args:
        repository: Evidence data access.
        storage_service: Screenshot integrity verification.
        config: Report generation configuration.
        session: Database session for audit logging.
    """

    def __init__(
        self,
        repository: EvidenceRepository,
        storage_service: EvidenceStorageService,
        config: ViolationReportConfig,
        session: AsyncSession,
    ) -> None:
        self._repository = repository
        self._storage = storage_service
        self._config = config
        self._session = session
        self._jinja_env: Any | None = None

    def _get_jinja_env(self) -> Any:
        """Lazy-initialize Jinja2 environment.

        Returns:
            Configured Jinja2 Environment.
        """
        if self._jinja_env is None:
            from jinja2 import Environment, FileSystemLoader  # noqa: WPS433

            self._jinja_env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=True,
            )
        return self._jinja_env

    async def generate_report(
        self, request: ViolationReportRequest
    ) -> ReportResult:
        """Generate a PDF violation report.

        Args:
            request: Report generation parameters.

        Returns:
            ReportResult with PDF bytes and metadata.

        Raises:
            ValueError: If no evidence records found.
        """
        # 1. Resolve evidence
        evidence_list = await self._resolve_evidence(request)
        if not evidence_list:
            raise ValueError("No evidence records found for report generation")

        # 2. Enforce max limit
        evidence_list = evidence_list[: self._config.max_evidence_per_report]

        # 3. Encode screenshots
        evidence_items = []
        for ev in evidence_list:
            screenshot_data = await self._encode_screenshot(ev)
            evidence_items.append(
                _EvidenceItem(evidence=ev, screenshot_data=screenshot_data)
            )

        # 4. Build template context
        context = self._build_template_context(evidence_items, request)

        # 5. Render HTML
        env = self._get_jinja_env()
        template_name = f"{request.template_type}.html"
        template = env.get_template(template_name)
        html_string = template.render(**context)

        # 6. Generate PDF (sync WeasyPrint wrapped in to_thread)
        html_cls = _import_weasyprint_html()
        pdf_bytes = await asyncio.to_thread(
            lambda: html_cls(string=html_string).write_pdf(
                pdf_variant=self._config.pdf_variant
            )
        )

        # 7. Compute hash and deterministic report_id
        sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
        report_id = UUID(sha256_hash[:32])

        # 8. Count pages (approximate from WeasyPrint output)
        page_count = _estimate_page_count(pdf_bytes)

        # 9. Build filename
        now = datetime.now(UTC)
        date_str = now.strftime("%Y-%m-%d")
        competitor_part = (
            f"-{request.competitor_name.lower().replace(' ', '-')}"
            if request.competitor_name
            else ""
        )
        filename = (
            f"violation-report-{date_str}{competitor_part}"
            f"-{request.template_type}.pdf"
        )

        # 10. Log audit entries
        for ev in evidence_list:
            await self._log_audit(
                ev.id,
                "report_included",
                "report_generator",
                {"report_id": str(report_id), "template": request.template_type},
            )

        return ReportResult(
            pdf_bytes=pdf_bytes,
            report_id=report_id,
            filename=filename,
            page_count=page_count,
            evidence_count=len(evidence_list),
            generated_at=now,
            sha256_hash=sha256_hash,
            template_type=request.template_type,
        )

    async def _resolve_evidence(
        self, request: ViolationReportRequest
    ) -> list[Any]:
        """Resolve evidence records from request parameters.

        Args:
            request: Report request with filters.

        Returns:
            List of Evidence ORM objects.
        """
        if request.evidence_ids:
            fetched = await asyncio.gather(
                *(self._repository.get_by_id(eid) for eid in request.evidence_ids)
            )
            return [ev for ev in fetched if ev is not None]

        evidence_list, _ = await self._repository.search(
            competitor_name=request.competitor_name,
            date_from=request.date_from,
            date_to=request.date_to,
            limit=self._config.max_evidence_per_report,
            offset=0,
        )
        return evidence_list

    async def _encode_screenshot(self, evidence: Any) -> str | None:
        """Read and encode screenshot as base64 data URI.

        Verifies SHA-256 integrity before encoding. Returns None
        if file missing or integrity check fails.

        Args:
            evidence: Evidence ORM object.

        Returns:
            Base64 data URI string or None.
        """
        is_valid = await self._storage.verify_integrity(
            evidence.screenshot_path, evidence.screenshot_hash
        )
        if not is_valid:
            logger.warning(
                "Screenshot integrity failed for evidence %s, skipping image",
                evidence.id,
            )
            return None

        try:
            path = Path(evidence.screenshot_path)
            screenshot_bytes = await asyncio.to_thread(path.read_bytes)
            encoded = base64.b64encode(screenshot_bytes).decode("ascii")
            return f"data:image/png;base64,{encoded}"
        except OSError:
            logger.warning(
                "Could not read screenshot for evidence %s", evidence.id
            )
            return None

    def _build_template_context(
        self,
        evidence_items: list[_EvidenceItem],
        request: ViolationReportRequest,
    ) -> dict[str, Any]:
        """Build Jinja2 template context dictionary.

        Args:
            evidence_items: Evidence with encoded screenshots.
            request: Original report request.

        Returns:
            Template context dict.
        """
        severity_counts = defaultdict(int)
        competitors: set[str] = set()
        competitor_timeline: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        items_for_template = []
        for item in evidence_items:
            ev = item.evidence
            severity_counts[ev.severity] += 1
            competitors.add(ev.competitor_name)
            month_key = ev.captured_at.strftime("%Y-%m")
            competitor_timeline[ev.competitor_name][month_key] += 1

            items_for_template.append(
                {
                    "id": str(ev.id),
                    "competitor_name": ev.competitor_name,
                    "source_url": ev.source_url,
                    "source_type": ev.source_type,
                    "claim_text": ev.claim_text,
                    "claim_category": ev.claim_category,
                    "violation_type": ev.violation_type,
                    "severity": ev.severity,
                    "regulation_violated": ev.regulation_violated,
                    "detection_reasoning": ev.detection_reasoning,
                    "confidence": ev.confidence,
                    "screenshot_hash": ev.screenshot_hash,
                    "screenshot_size_bytes": getattr(
                        ev, "screenshot_size_bytes", 0
                    ),
                    "captured_at": ev.captured_at.strftime("%Y-%m-%d %H:%M UTC"),
                    "screenshot_data": item.screenshot_data,
                    "audit_logs": [
                        {
                            "created_at": log.created_at.strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                            "action": log.action,
                            "actor": log.actor,
                            "details": str(log.details) if log.details else "",
                        }
                        for log in getattr(ev, "audit_logs", []) or []
                    ],
                }
            )

        now = datetime.now(UTC)
        date_range_display = "All time"
        if request.date_from and request.date_to:
            date_range_display = (
                f"{request.date_from.strftime('%Y-%m-%d')} to "
                f"{request.date_to.strftime('%Y-%m-%d')}"
            )
        elif request.date_from:
            date_range_display = f"From {request.date_from.strftime('%Y-%m-%d')}"
        elif request.date_to:
            date_range_display = f"Until {request.date_to.strftime('%Y-%m-%d')}"

        return {
            "report_title": request.report_title
            or f"Violation Report - {now.strftime('%Y-%m-%d')}",
            "company_name": self._config.company_name,
            "competitor_name": request.competitor_name,
            "evidence_count": len(evidence_items),
            "date_range": date_range_display,
            "date_range_display": date_range_display,
            "template_type": request.template_type,
            "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
            "report_hash": "",  # Hash computed post-generation, available in report metadata
            "screenshot_max_width": self._config.screenshot_max_width_px,
            "severity_counts": {
                "high": severity_counts.get("high", 0),
                "medium": severity_counts.get("medium", 0),
                "low": severity_counts.get("low", 0),
            },
            "competitor_count": len(competitors),
            "competitor_timeline": dict(competitor_timeline),
            "evidence_list": items_for_template,
        }

    async def _log_audit(
        self,
        evidence_id: UUID,
        action: str,
        actor: str,
        details: dict[str, str] | None = None,
    ) -> None:
        """Create an audit log entry.

        Args:
            evidence_id: Evidence record ID.
            action: Audit action type.
            actor: Who performed the action.
            details: Additional context.
        """
        from core.regulatory.models import EvidenceAuditLog  # noqa: WPS433

        audit = EvidenceAuditLog(
            evidence_id=evidence_id,
            action=action,
            actor=actor,
            details=details,
        )
        self._session.add(audit)


class _EvidenceItem:
    """Internal wrapper pairing Evidence with encoded screenshot."""

    __slots__ = ("evidence", "screenshot_data")

    def __init__(self, evidence: Any, screenshot_data: str | None) -> None:
        self.evidence = evidence
        self.screenshot_data = screenshot_data


def _estimate_page_count(pdf_bytes: bytes) -> int:
    """Estimate page count from PDF bytes.

    Counts /Type /Page occurrences (excluding /Pages).

    Args:
        pdf_bytes: Raw PDF bytes.

    Returns:
        Estimated page count (minimum 1).
    """
    count = pdf_bytes.count(b"/Type /Page")
    # Subtract /Type /Pages occurrences
    pages_count = pdf_bytes.count(b"/Type /Pages")
    return max(count - pages_count, 1)


__all__ = [
    "WeasyPrintPDFGenerator",
]
