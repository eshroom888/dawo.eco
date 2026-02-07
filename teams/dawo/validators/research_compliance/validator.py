"""Research Compliance Validator - EU compliance checking for research items.

Validates research items for EU Health Claims compliance before pool entry.
Bridges the EU Compliance Checker (Story 1.2) with all scanner validators.

This is a SHARED COMPONENT used by all research scanners (Reddit, YouTube,
Instagram, News, PubMed) for consistent EU compliance checking.

Key Features:
- Scientific citation detection (DOI, PMID, URLs)
- Source-specific validation rules (PubMed vs social sources)
- Batch validation with partial failure handling
- Citation-aware status adjustment (REJECTED + citation = WARNING)

Usage:
    validator = ResearchComplianceValidator(eu_compliance_checker)
    result = await validator.validate(transformed_research_item)
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Tuple

from teams.dawo.research import TransformedResearch, ComplianceStatus
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ContentComplianceCheck,
    OverallStatus,
    ComplianceResult,
)

from .schemas import (
    CitationInfo,
    ComplianceValidationResult,
    ValidationStats,
    ValidationError,
)

# Module logger
logger = logging.getLogger(__name__)


class ValidatedResearch:
    """Research item with compliance validation results.

    Extends the input TransformedResearch with compliance status and notes.
    This is the output of the validation stage, ready for pool entry.

    Attributes:
        source: Research source identifier
        title: Research title
        content: Research content
        url: Source URL
        tags: Topic tags
        source_metadata: Source-specific metadata
        score: Research relevance score
        created_at: Discovery timestamp
        compliance_status: EU compliance status (COMPLIANT, WARNING, REJECTED)
        compliance_notes: Human-readable compliance explanation
        flagged_phrases: List of flagged compliance issues
        has_scientific_citation: True if DOI/PMID/scientific URL found
    """

    def __init__(
        self,
        source: str,
        title: str,
        content: str,
        url: str,
        tags: list[str],
        source_metadata: dict,
        score: float,
        created_at: datetime,
        compliance_status: ComplianceStatus,
        compliance_notes: str,
        flagged_phrases: list[ComplianceResult],
        has_scientific_citation: bool,
    ):
        self.source = source
        self.title = title
        self.content = content
        self.url = url
        self.tags = tags
        self.source_metadata = source_metadata
        self.score = score
        self.created_at = created_at
        self.compliance_status = compliance_status
        self.compliance_notes = compliance_notes
        self.flagged_phrases = flagged_phrases
        self.has_scientific_citation = has_scientific_citation


class ResearchComplianceValidator:
    """Validates research items for EU compliance before pool entry.

    Bridges EU Compliance Checker (Story 1.2) with all scanner validators.
    Applies source-specific rules and citation detection.

    CRITICAL: Accepts EUComplianceChecker via injection - NEVER loads config directly.

    Attributes:
        _compliance_checker: EU Compliance Checker instance
    """

    # DOI pattern: 10.xxxx/xxxxx
    DOI_PATTERN = re.compile(r'10\.\d{4,}/[^\s]+')

    # PMID pattern: "PMID: 12345678" or "PMID:12345678" or standalone 8+ digits
    PMID_PATTERN = re.compile(r'(?:PMID|pmid)[:\s]*(\d{7,})')

    # Scientific URL patterns
    SCIENTIFIC_URL_PATTERNS = [
        re.compile(r'pubmed\.ncbi\.nlm\.nih\.gov/\d+'),
        re.compile(r'doi\.org/10\.\d{4,}'),
        re.compile(r'ncbi\.nlm\.nih\.gov/pmc/articles/PMC\d+'),
    ]

    def __init__(self, compliance_checker: EUComplianceChecker):
        """Initialize with EU Compliance Checker.

        Args:
            compliance_checker: EUComplianceChecker instance from Story 1.2.
                               Injected by Team Builder - NEVER load directly.
        """
        self._compliance_checker = compliance_checker

    async def validate(
        self,
        research_item: TransformedResearch,
    ) -> ValidatedResearch:
        """Validate single research item for EU compliance.

        Detects citations, checks compliance, and determines final status.

        Args:
            research_item: Transformed research from scanner

        Returns:
            ValidatedResearch with compliance_status set

        Raises:
            ValidationError: If validation cannot complete
        """
        logger.debug(
            "Validating research item: source=%s, title=%s",
            research_item.source,
            research_item.title[:50],
        )

        try:
            # Get source as string
            source_str = (
                research_item.source.value
                if hasattr(research_item.source, "value")
                else str(research_item.source)
            )

            # Step 1: Detect scientific citations
            citation_info = self._detect_citation(
                text=research_item.content,
                source_metadata=research_item.source_metadata,
            )

            # Step 2: Build text to check (title + content + key findings)
            texts_to_check = self._extract_texts_to_check(research_item)

            # Step 3: Check compliance for combined text
            combined_text = "\n\n".join(texts_to_check)
            check_result = await self._compliance_checker.check_content(combined_text)

            # Step 4: Determine final status with citation adjustment
            final_status = self._determine_final_status(
                base_status=check_result.overall_status,
                citation_info=citation_info,
                source_type=source_str,
            )

            # Step 5: Build compliance notes
            notes = self._build_compliance_notes(
                status=final_status,
                citation_info=citation_info,
                flagged_count=len(check_result.flagged_phrases),
                source_type=source_str,
            )

            logger.debug(
                "Validation complete: source=%s, status=%s, citations=%s",
                source_str,
                final_status.value,
                citation_info.has_citation,
            )

            return ValidatedResearch(
                source=source_str,
                title=research_item.title,
                content=research_item.content,
                url=research_item.url,
                tags=list(research_item.tags),
                source_metadata=dict(research_item.source_metadata),
                score=research_item.score,
                created_at=research_item.created_at or datetime.now(timezone.utc),
                compliance_status=final_status,
                compliance_notes=notes,
                flagged_phrases=check_result.flagged_phrases,
                has_scientific_citation=citation_info.has_citation,
            )

        except Exception as e:
            logger.error(
                "Failed to validate research item '%s': %s",
                research_item.title[:50],
                e,
            )
            raise ValidationError(
                message=f"Validation failed: {e}",
                source_id=getattr(research_item, "id", None),
            )

    async def validate_batch(
        self,
        items: list[TransformedResearch],
    ) -> list[ValidatedResearch]:
        """Validate batch of research items concurrently.

        Processes items in parallel, handling individual failures gracefully.
        Returns partial results even if some items fail.

        Args:
            items: List of transformed research items

        Returns:
            List of validated items (partial results if some fail)
        """
        logger.info("Validating batch of %d items", len(items))

        async def validate_single(item: TransformedResearch) -> Optional[ValidatedResearch]:
            try:
                return await self.validate(item)
            except Exception as e:
                logger.error(
                    "Batch validation failed for item '%s': %s",
                    item.title[:50] if item.title else "Unknown",
                    e,
                )
                return None

        # Process all items concurrently
        results = await asyncio.gather(
            *[validate_single(item) for item in items],
            return_exceptions=False,
        )

        # Filter out None results from failures
        validated = [r for r in results if r is not None]

        # Log statistics
        stats = self._calculate_stats(items, validated)
        logger.info(
            "Batch validation complete: total=%d, validated=%d, compliant=%d, warned=%d, rejected=%d, failed=%d",
            stats.total,
            stats.validated,
            stats.compliant,
            stats.warned,
            stats.rejected,
            stats.failed,
        )

        return validated

    async def validate_batch_with_stats(
        self,
        items: list[TransformedResearch],
    ) -> Tuple[list[ValidatedResearch], ValidationStats]:
        """Validate batch and return statistics.

        Same as validate_batch but also returns detailed statistics.

        Args:
            items: List of transformed research items

        Returns:
            Tuple of (validated items, validation statistics)
        """
        validated = await self.validate_batch(items)
        stats = self._calculate_stats(items, validated)
        return validated, stats

    def _extract_texts_to_check(
        self,
        research_item: TransformedResearch,
    ) -> list[str]:
        """Extract all text fields to check for compliance.

        Args:
            research_item: Research item to extract from

        Returns:
            List of non-empty text strings to check
        """
        texts = []

        # Always check title
        if research_item.title:
            texts.append(research_item.title)

        # Check content
        if research_item.content:
            texts.append(research_item.content)

        # Check key findings from metadata if present
        if research_item.source_metadata:
            key_findings = research_item.source_metadata.get("key_findings")
            if key_findings and isinstance(key_findings, str):
                texts.append(key_findings)

        return texts

    def _detect_citation(
        self,
        text: str,
        source_metadata: Optional[dict],
    ) -> CitationInfo:
        """Detect scientific citations in research.

        Checks for DOI, PMID, and scientific URLs in both text and metadata.

        Args:
            text: Content text to search
            source_metadata: Source-specific metadata dict

        Returns:
            CitationInfo with detection results
        """
        return self._detect_citation_static(text, source_metadata)

    @staticmethod
    def _detect_citation_static(
        text: str,
        source_metadata: Optional[dict],
    ) -> CitationInfo:
        """Static citation detection for testing.

        Args:
            text: Content text to search
            source_metadata: Source-specific metadata dict

        Returns:
            CitationInfo with detection results
        """
        has_doi = False
        has_pmid = False
        has_url = False
        doi = None
        pmid = None
        url = None

        # Check text for DOI pattern
        doi_match = ResearchComplianceValidator.DOI_PATTERN.search(text)
        if doi_match:
            has_doi = True
            doi = doi_match.group(0)

        # Check text for PMID pattern
        pmid_match = ResearchComplianceValidator.PMID_PATTERN.search(text)
        if pmid_match:
            has_pmid = True
            pmid = pmid_match.group(1)

        # Check metadata for DOI/PMID
        if source_metadata:
            if source_metadata.get("doi"):
                has_doi = True
                doi = doi or source_metadata["doi"]
            if source_metadata.get("pmid"):
                has_pmid = True
                pmid = pmid or str(source_metadata["pmid"])

        # Check for scientific URLs
        for pattern in ResearchComplianceValidator.SCIENTIFIC_URL_PATTERNS:
            url_match = pattern.search(text)
            if url_match:
                has_url = True
                url = url_match.group(0)
                break

        return CitationInfo(
            has_doi=has_doi,
            has_pmid=has_pmid,
            has_url=has_url,
            doi=doi,
            pmid=pmid,
            url=url,
        )

    def _determine_final_status(
        self,
        base_status: OverallStatus,
        citation_info: CitationInfo,
        source_type: str,
    ) -> ComplianceStatus:
        """Determine final compliance status with citation adjustment.

        Rules:
        - PubMed sources: REJECTED becomes WARNING (always citable)
        - Other sources with citation: REJECTED becomes WARNING
        - No citation: Use base status directly

        Args:
            base_status: Status from EU Compliance Checker
            citation_info: Citation detection result
            source_type: Research source (reddit, pubmed, etc.)

        Returns:
            Final ComplianceStatus
        """
        # PubMed sources are inherently citable
        if source_type.lower() == "pubmed":
            if base_status == OverallStatus.REJECTED:
                # Even PubMed can have prohibited language, but we can cite
                return ComplianceStatus.WARNING
            return ComplianceStatus.COMPLIANT

        # Other sources with citations
        if citation_info.has_citation:
            if base_status == OverallStatus.REJECTED:
                # Has citation, downgrade to WARNING
                return ComplianceStatus.WARNING

        # Map OverallStatus to ComplianceStatus
        status_map = {
            OverallStatus.COMPLIANT: ComplianceStatus.COMPLIANT,
            OverallStatus.WARNING: ComplianceStatus.WARNING,
            OverallStatus.REJECTED: ComplianceStatus.REJECTED,
        }

        return status_map.get(base_status, ComplianceStatus.WARNING)

    def _build_compliance_notes(
        self,
        status: ComplianceStatus,
        citation_info: CitationInfo,
        flagged_count: int,
        source_type: str,
    ) -> str:
        """Build human-readable compliance notes.

        Args:
            status: Final compliance status
            citation_info: Citation detection result
            flagged_count: Number of flagged phrases
            source_type: Research source type

        Returns:
            Human-readable notes string
        """
        notes = []

        if status == ComplianceStatus.COMPLIANT:
            notes.append("Content passed EU compliance check.")
        elif status == ComplianceStatus.WARNING:
            notes.append(f"Content has {flagged_count} flagged phrase(s).")
            if citation_info.has_citation:
                notes.append("Scientific citation present - can cite study but cannot make health claims.")
        else:  # REJECTED
            notes.append(f"Content contains {flagged_count} prohibited phrase(s).")
            notes.append("Cannot be used for marketing claims.")

        if source_type.lower() == "pubmed":
            notes.append("Source: Peer-reviewed scientific publication.")

        return " ".join(notes)

    def _calculate_stats(
        self,
        original_items: list[TransformedResearch],
        validated_items: list[ValidatedResearch],
    ) -> ValidationStats:
        """Calculate validation statistics.

        Args:
            original_items: Items submitted for validation
            validated_items: Successfully validated items

        Returns:
            ValidationStats with counts
        """
        compliant = sum(
            1 for v in validated_items
            if v.compliance_status == ComplianceStatus.COMPLIANT
        )
        warned = sum(
            1 for v in validated_items
            if v.compliance_status == ComplianceStatus.WARNING
        )
        rejected = sum(
            1 for v in validated_items
            if v.compliance_status == ComplianceStatus.REJECTED
        )

        return ValidationStats(
            total=len(original_items),
            validated=len(validated_items),
            compliant=compliant,
            warned=warned,
            rejected=rejected,
            failed=len(original_items) - len(validated_items),
        )
