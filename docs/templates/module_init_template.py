"""
Module __init__.py Template for DAWO.ECO

USAGE:
1. Copy this template when creating a new module directory
2. Replace placeholders with actual imports
3. ALWAYS include __all__ with ALL public exports

REMEMBER (from Epic 1 retrospective):
- Missing __all__ was caught 3x in code review
- Export ALL: classes, functions, enums, dataclasses, Protocol types
- Use tier names (scan/generate/strategize), NOT model names (haiku/sonnet/opus)
"""

# =============================================================================
# TEMPLATE START - Copy below this line
# =============================================================================

"""Module description - replace with actual description.

Exports:
    - MainClass: Primary class for this module
    - SupportingClass: Supporting functionality
    - ConfigDataclass: Configuration dataclass
    - StatusEnum: Status enumeration
    - ProtocolType: Protocol for dependency injection
"""

# Import from submodules
from .main_module import (
    MainClass,
    SupportingClass,
)
from .types import (
    ConfigDataclass,
    StatusEnum,
    ResultDataclass,
)
from .protocols import (
    ProtocolType,
)

# CRITICAL: Always define __all__ with ALL public exports
# This was a recurring issue in Epic 1 code reviews
__all__ = [
    # Classes
    "MainClass",
    "SupportingClass",
    # Dataclasses
    "ConfigDataclass",
    "ResultDataclass",
    # Enums
    "StatusEnum",
    # Protocols (for type hints and dependency injection)
    "ProtocolType",
]

# =============================================================================
# TEMPLATE END
# =============================================================================

# EXAMPLES FROM EPIC 1:

# Example 1: Validator module (eu_compliance)
"""
from .agent import (
    EUComplianceChecker,
    ComplianceResult,
    ComplianceStatus,
    OverallStatus,
    ContentComplianceCheck,
    NovelFoodCheck,
    RegulationRef,
    ComplianceScoring,
    LLMClient,
)
from .rules import ComplianceRules

__all__ = [
    "EUComplianceChecker",
    "ComplianceResult",
    "ComplianceStatus",
    "OverallStatus",
    "ContentComplianceCheck",
    "NovelFoodCheck",
    "RegulationRef",
    "ComplianceScoring",
    "LLMClient",
    "ComplianceRules",
]
"""

# Example 2: Config module (llm_tiers)
"""
from .llm_tiers import (
    LLMTierResolver,
    LLMTierConfig,
    TierConfig,
    TaskType,
    TierName,
    AgentOverride,
)
from .loader import load_llm_tier_config, LLMTierConfigError

__all__ = [
    "LLMTierResolver",
    "LLMTierConfig",
    "TierConfig",
    "TaskType",
    "TierName",
    "AgentOverride",
    "load_llm_tier_config",
    "LLMTierConfigError",
]
"""

# Example 3: Middleware module (retry)
"""
from .retry import (
    RetryMiddleware,
    RetryConfig,
    RetryResult,
)
from .http_client import RetryableHttpClient
from .operation_queue import (
    IncompleteOperation,
    OperationQueue,
)
from .discord_alerts import DiscordAlertManager

__all__ = [
    "RetryMiddleware",
    "RetryConfig",
    "RetryResult",
    "RetryableHttpClient",
    "IncompleteOperation",
    "OperationQueue",
    "DiscordAlertManager",
]
"""
