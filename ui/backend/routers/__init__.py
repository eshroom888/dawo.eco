"""FastAPI routers for UI Backend.

Provides API routers for all UI backend endpoints.

Exports:
    - approval_queue_router: Approval queue endpoints
    - schedule_router: Content scheduling endpoints (Story 4-4, 4-5)
    - health_router: Health check and metrics endpoints
"""

from .approval_queue import router as approval_queue_router
from .schedule import router as schedule_router
from .health import router as health_router

__all__ = [
    "approval_queue_router",
    "schedule_router",
    "health_router",
]
