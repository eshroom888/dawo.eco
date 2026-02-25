"""B2B Leads Module for DAWO team.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Provides lead discovery, harvesting, and pipeline management for B2B outreach.

Exports:
    Scanner:
        - B2BLeadScanner: Main scanner agent for lead discovery
        - LeadHarvester: Enriches raw leads with Hunter.io data
        - LeadTransformer: Maps harvested data to Lead model
        - LeadDuplicateChecker: Deduplicates against existing leads
        - B2BLeadPipeline: Orchestrates the full discovery pipeline

    Tools:
        - HunterClient: Hunter.io API client

    Config:
        - HunterClientConfig: API credentials config
        - LeadScannerConfig: Scanner configuration

    Schemas:
        - RawLead: Initial lead from search
        - HarvestedLead: Enriched lead data
        - TransformedLead: Lead ready for database
        - ScanResult: Scanner output
        - PipelineResult: Full pipeline output

    Repository:
        - LeadRepository: Database operations for leads
"""

from teams.dawo.leads.scanner import (
    # Agent
    B2BLeadScanner,
    # Pipeline stages
    LeadHarvester,
    LeadTransformer,
    LeadDuplicateChecker,
    B2BLeadPipeline,
    # Tools
    HunterClient,
    # Config
    HunterClientConfig,
    LeadScannerConfig,
    # Schemas
    RawLead,
    HarvestedLead,
    HarvestedContact,
    TransformedLead,
    ScanResult,
    PipelineResult,
    PipelineStatus,
    ScanStatistics,
)

from teams.dawo.leads.repository import LeadRepository

# Pipeline module (Story 5-5)
from teams.dawo.leads.pipeline import (
    PipelineService,
    CSVExporter,
    VALID_MANUAL_TRANSITIONS,
    PipelineSummary,
    ConversionMetrics,
    WeeklyTrend,
    FollowUpCandidate,
    StageTimingStats,
)

__all__ = [
    # Agent
    "B2BLeadScanner",
    # Pipeline stages
    "LeadHarvester",
    "LeadTransformer",
    "LeadDuplicateChecker",
    "B2BLeadPipeline",
    # Tools
    "HunterClient",
    # Config
    "HunterClientConfig",
    "LeadScannerConfig",
    # Schemas
    "RawLead",
    "HarvestedLead",
    "HarvestedContact",
    "TransformedLead",
    "ScanResult",
    "PipelineResult",
    "PipelineStatus",
    "ScanStatistics",
    # Repository
    "LeadRepository",
    # Pipeline (Story 5-5)
    "PipelineService",
    "CSVExporter",
    "VALID_MANUAL_TRANSITIONS",
    "PipelineSummary",
    "ConversionMetrics",
    "WeeklyTrend",
    "FollowUpCandidate",
    "StageTimingStats",
]
