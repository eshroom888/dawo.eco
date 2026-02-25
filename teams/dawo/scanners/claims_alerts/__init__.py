"""Claims Alerts Module.

Epic 6, Story 6-4: New Claims Activation Alerts.

Subscribes to regulatory events from Stories 6-1/6-2/6-3 and routes
relevant alerts to Discord for operator notification.

Usage:
    from teams.dawo.scanners.claims_alerts import (
        ClaimsAlertConfig,
        ClaimsAlertFormatter,
        ClaimsAlertBatcher,
        DAWORelevanceFilter,
        ClaimsAlertService,
        RegulatoryAlertSubscriber,
        AlertResult,
        AlertStatus,
        AlertCategory,
    )
"""

from teams.dawo.scanners.claims_alerts.config import (
    ClaimsAlertConfig,
    build_claims_alert_config,
)
from teams.dawo.scanners.claims_alerts.formatter import ClaimsAlertFormatter
from teams.dawo.scanners.claims_alerts.batcher import ClaimsAlertBatcher
from teams.dawo.scanners.claims_alerts.relevance_filter import DAWORelevanceFilter
from teams.dawo.scanners.claims_alerts.service import (
    ClaimsAlertService,
    NotificationQueueProtocol,
)
from teams.dawo.scanners.claims_alerts.subscriber import RegulatoryAlertSubscriber
from teams.dawo.scanners.claims_alerts.schemas import (
    AlertResult,
    AlertStatus,
    AlertCategory,
    categorize_event,
)

__all__ = [
    "ClaimsAlertConfig",
    "build_claims_alert_config",
    "ClaimsAlertFormatter",
    "ClaimsAlertBatcher",
    "DAWORelevanceFilter",
    "ClaimsAlertService",
    "NotificationQueueProtocol",
    "RegulatoryAlertSubscriber",
    "AlertResult",
    "AlertStatus",
    "AlertCategory",
    "categorize_event",
]
