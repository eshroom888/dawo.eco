"""FastAPI routers for UI Backend.

Provides API routers for all UI backend endpoints.

Exports:
    - approval_queue_router: Approval queue endpoints
    - schedule_router: Content scheduling endpoints (Story 4-4, 4-5)
    - health_router: Health check and metrics endpoints
    - websocket_router: WebSocket endpoints for real-time events (Epic 4 debt)
    - pipeline_router: Lead pipeline dashboard endpoints (Story 5-5)
    - evidence_router: Evidence search/filter endpoints (Story 6-9)
    - reports_router: Violation report generation endpoints (Story 6-10)
    - redirect_router: Short link redirect endpoint (Story 7-2)
    - webhook_router: Shopify webhook endpoints (Story 7-3)
    - agent_schedules_router: Agent schedule configuration endpoints (Story 7-6)
    - triggers_router: Manual agent/team trigger endpoints (Story 7-7)
    - executions_router: Execution dashboard endpoints (Story 7-8)
    - calendar_router: Google Calendar sync endpoints (Story 7-9)
    - degradation_router: System status and recovery endpoints (Story 7-10)
"""

from .approval_queue import router as approval_queue_router
from .calendar import router as calendar_router
from .degradation import router as degradation_router
from .evidence import router as evidence_router
from .executions import router as executions_router
from .schedule import router as schedule_router
from .schedules import router as agent_schedules_router
from .health import router as health_router
from .websocket import router as websocket_router
from .pipeline import router as pipeline_router
from .reports import router as reports_router
from .redirect import redirect_router
from .triggers import router as triggers_router
from .webhooks import webhook_router

__all__ = [
    "agent_schedules_router",
    "approval_queue_router",
    "calendar_router",
    "degradation_router",
    "evidence_router",
    "executions_router",
    "schedule_router",
    "health_router",
    "triggers_router",
    "websocket_router",
    "pipeline_router",
    "redirect_router",
    "reports_router",
    "webhook_router",
]
