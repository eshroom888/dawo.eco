"""Evidence Collection package (Story 6-8, 6-10).

Captures screenshots of violation evidence using Playwright,
stores with SHA-256 integrity hashing, manages immutable evidence records,
and generates on-demand violation report PDFs.
"""

from teams.dawo.scanners.evidence_collection.collector import EvidenceCollector
from teams.dawo.scanners.evidence_collection.config import (
    EvidenceCollectionConfig,
    build_evidence_collection_config,
)
from teams.dawo.scanners.evidence_collection.repository import EvidenceRepository
from teams.dawo.scanners.evidence_collection.schemas import (
    CaptureResult,
    CollectionBatchResult,
    EvidenceCreateDTO,
    ImmutableEvidenceError,
)
from teams.dawo.scanners.evidence_collection.screenshot_service import (
    PlaywrightScreenshotService,
    ScreenshotServiceProtocol,
)
from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService
from teams.dawo.scanners.evidence_collection.download import EvidenceDownloadService
from teams.dawo.scanners.evidence_collection.report_config import (
    ViolationReportConfig,
    build_violation_report_config,
)
from teams.dawo.scanners.evidence_collection.report_generator import (
    WeasyPrintPDFGenerator,
)
from teams.dawo.scanners.evidence_collection.report_schemas import (
    PDFGeneratorProtocol,
    ReportMetadata,
    ReportResult,
    ReportStorageProtocol,
    ViolationReportRequest,
)
from teams.dawo.scanners.evidence_collection.report_storage import (
    ReportStorageService,
)

__all__ = [
    "CaptureResult",
    "CollectionBatchResult",
    "EvidenceCollectionConfig",
    "EvidenceCollector",
    "EvidenceCreateDTO",
    "EvidenceDownloadService",
    "EvidenceRepository",
    "EvidenceStorageService",
    "ImmutableEvidenceError",
    "PDFGeneratorProtocol",
    "PlaywrightScreenshotService",
    "ReportMetadata",
    "ReportResult",
    "ReportStorageProtocol",
    "ReportStorageService",
    "ScreenshotServiceProtocol",
    "ViolationReportConfig",
    "ViolationReportRequest",
    "WeasyPrintPDFGenerator",
    "build_evidence_collection_config",
    "build_violation_report_config",
]
