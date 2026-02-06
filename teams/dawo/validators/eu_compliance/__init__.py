"""EU Compliance Checker - EU Health Claims Regulation validator.

This module provides compliance checking against EC 1924/2006.
All content must pass this validator before entering the approval queue.

Exports:
    EUComplianceChecker: Main validator agent class
    ComplianceStatus: Phrase classification enum (PROHIBITED, BORDERLINE, PERMITTED)
    OverallStatus: Content status enum (COMPLIANT, WARNING, REJECTED)
    ComplianceResult: Individual phrase check result
    ContentComplianceCheck: Full content check result
    NovelFoodCheck: Novel Food classification validation result
    RegulationRef: EU regulation reference constants
    LLMClient: Protocol for LLM client interface
    ComplianceScoring: Constants for score calculations
"""

from .agent import (
    EUComplianceChecker,
    ComplianceStatus,
    OverallStatus,
    ComplianceResult,
    ContentComplianceCheck,
    NovelFoodCheck,
    RegulationRef,
    LLMClient,
    ComplianceScoring,
)

__all__: list[str] = [
    "EUComplianceChecker",
    "ComplianceStatus",
    "OverallStatus",
    "ComplianceResult",
    "ContentComplianceCheck",
    "NovelFoodCheck",
    "RegulationRef",
    "LLMClient",
    "ComplianceScoring",
]
