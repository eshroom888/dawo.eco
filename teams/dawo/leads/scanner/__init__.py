"""B2B Lead Research Scanner module.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Implements the lead discovery pipeline following the Harvester Framework pattern:
Scanner -> Harvester -> Transformer -> DuplicateChecker -> Repository

Exports:
    Agent:
        - B2BLeadScanner: Main scanner agent

    Pipeline Stages:
        - LeadHarvester: Enriches leads with Hunter.io data
        - LeadTransformer: Maps to Lead model schema
        - LeadDuplicateChecker: Deduplicates against database
        - B2BLeadPipeline: Orchestrates full pipeline

    Tools:
        - HunterClient: Hunter.io API client

    Config:
        - HunterClientConfig: API credentials
        - LeadScannerConfig: Scanner settings

    Schemas:
        - RawLead, HarvestedLead, HarvestedContact, TransformedLead
        - ScanResult, PipelineResult, PipelineStatus, ScanStatistics
"""

from teams.dawo.leads.scanner.agent import B2BLeadScanner
from teams.dawo.leads.scanner.harvester import LeadHarvester
from teams.dawo.leads.scanner.transformer import LeadTransformer
from teams.dawo.leads.scanner.duplicate_checker import LeadDuplicateChecker
from teams.dawo.leads.scanner.pipeline import B2BLeadPipeline
from teams.dawo.leads.scanner.tools import HunterClient
from teams.dawo.leads.scanner.config import (
    HunterClientConfig,
    LeadScannerConfig,
)
from teams.dawo.leads.scanner.schemas import (
    RawLead,
    HarvestedLead,
    HarvestedContact,
    TransformedLead,
    ScanResult,
    PipelineResult,
    PipelineStatus,
    ScanStatistics,
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
]
