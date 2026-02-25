"""EU Violation Detection module (Story 6-7).

Detects EU regulation violations in extracted competitor health claims.
"""

from teams.dawo.scanners.violation_detection.classifier import ViolationClassifier
from teams.dawo.scanners.violation_detection.config import (
    ViolationDetectionConfig,
    build_violation_detection_config,
)
from teams.dawo.scanners.violation_detection.detector import ViolationDetector
from teams.dawo.scanners.violation_detection.repository import ViolationRepository
from teams.dawo.scanners.violation_detection.schemas import (
    AuthorizedClaimInfo,
    DetectionBatchResult,
    ViolationResult,
)

__all__ = [
    "AuthorizedClaimInfo",
    "DetectionBatchResult",
    "ViolationClassifier",
    "ViolationDetectionConfig",
    "ViolationDetector",
    "ViolationRepository",
    "ViolationResult",
    "build_violation_detection_config",
]
