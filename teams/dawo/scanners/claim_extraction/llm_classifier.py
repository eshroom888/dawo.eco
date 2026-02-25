"""LLM-based health claim classifier.

Epic 6, Story 6-6, Task 6: ClaimLLMClassifier.

Sends content and regex pre-filter matches to LLM for classification,
confirmation, and additional claim discovery. Follows the hybrid
regex+LLM pattern from EUComplianceChecker (reference, not import).

Classes:
    ClaimLLMClassifier: LLM classification with merge logic.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol, runtime_checkable

from teams.dawo.scanners.claim_extraction.config import HealthClaimExtractionConfig
from teams.dawo.scanners.claim_extraction.schemas import (
    ClaimExtractionResult,
    PatternMatch,
)

logger = logging.getLogger(__name__)

# Confidence scores by extraction method
CONFIDENCE_REGEX_ONLY = 60
CONFIDENCE_HYBRID = 90
CONFIDENCE_LLM_ONLY = 75
# Text overlap threshold for deduplication (fraction)
OVERLAP_THRESHOLD = 0.8


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol for LLM client dependency injection."""

    async def generate(self, prompt: str, *, tier: str = "generate") -> str: ...


@runtime_checkable
class RetryMiddlewareProtocol(Protocol):
    """Protocol for retry middleware dependency injection."""

    async def execute_with_retry(self, func, *args, **kwargs): ...


class ClaimLLMClassifier:
    """LLM-based health claim classifier.

    Uses LLM to confirm regex matches, classify claims by category,
    and discover additional claims missed by regex.

    Args:
        llm_client: LLM client for generating responses.
        retry: Retry middleware for wrapping LLM calls.
        config: Extraction configuration.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        retry: RetryMiddlewareProtocol,
        config: HealthClaimExtractionConfig,
    ) -> None:
        self._llm = llm_client
        self._retry = retry
        self._config = config

    async def classify_claims(
        self,
        content_text: str,
        pre_filter_matches: list[PatternMatch],
        language_hint: str,
    ) -> list[ClaimExtractionResult]:
        """Classify health claims using LLM.

        Args:
            content_text: Full text to analyze.
            pre_filter_matches: Regex matches as hints.
            language_hint: Detected language ("en", "no").

        Returns:
            Merged list of ClaimExtractionResult from regex + LLM.
        """
        llm_claims = await self._call_llm(content_text, pre_filter_matches, language_hint)
        merged = self._merge_claims(pre_filter_matches, llm_claims)

        # Cap at max_claims_per_content
        if len(merged) > self._config.max_claims_per_content:
            # Keep highest confidence
            merged.sort(key=lambda c: c.confidence_score, reverse=True)
            merged = merged[: self._config.max_claims_per_content]

        return merged

    async def _call_llm(
        self,
        content_text: str,
        pre_filter_matches: list[PatternMatch],
        language_hint: str,
    ) -> list[dict]:
        """Call LLM and parse response."""
        prompt = self._build_extraction_prompt(content_text, pre_filter_matches, language_hint)
        try:
            response = await self._retry.execute_with_retry(
                self._llm.generate, prompt, tier="generate"
            )
            return self._parse_llm_response(response)
        except Exception:
            logger.debug("LLM call failed, returning empty claims", exc_info=True)
            return []

    def _build_extraction_prompt(
        self,
        content_text: str,
        pre_filter_matches: list[PatternMatch],
        language_hint: str,
    ) -> str:
        """Build the extraction prompt for LLM.

        Includes regulation context, mushroom-specific context,
        pre-filter results, and bilingual examples.
        """
        matches_text = ""
        if pre_filter_matches:
            match_lines = []
            for m in pre_filter_matches:
                match_lines.append(
                    f'  - "{m.matched_text}" (category: {m.category}, language: {m.language})'
                )
            matches_text = "Regex pre-filter found these potential matches:\n" + "\n".join(match_lines) + "\n\n"

        return f"""You are an EU food regulation expert analyzing competitor content for unauthorized health claims under EC 1924/2006.

REGULATORY CONTEXT:
- EU Health Claims Regulation EC 1924/2006 governs all health claims on food products.
- For functional mushrooms (lion's mane, chaga, reishi, cordyceps, turkey tail, etc.), ZERO authorized EU health claims exist.
- Any health claim on a mushroom product is either unauthorized or prohibited.

CLAIM CATEGORIES:
- treatment: Medicinal/treatment claims (PROHIBITED — e.g., "cures cancer", "treats depression")
- prevention: Disease risk reduction (Article 14.1a — e.g., "reduces risk of heart disease")
- enhancement: Body function enhancement (Article 13.1 — e.g., "boosts immunity", "improves cognition")
- general_wellness: General wellbeing (Article 13.1 borderline — e.g., "supports wellbeing")

LANGUAGE: Content appears to be in {"Norwegian" if language_hint == "no" else "English"}.
Note: Content may be bilingual. Check for claims in BOTH English and Norwegian.

Norwegian examples:
- "styrker immunforsvaret" → enhancement
- "behandler kreft" → treatment (prohibited)
- "forebygger sykdom" → prevention
- "bidrar til helse" → general_wellness

English examples:
- "boosts cognitive function" → enhancement
- "cures cancer" → treatment (prohibited)
- "prevents disease" → prevention
- "supports wellbeing" → general_wellness

{matches_text}CONTENT TO ANALYZE:
{content_text}

INSTRUCTIONS:
1. Analyze the content for ALL health claims (explicit and implicit).
2. For each claim found, provide: claim_text (exact phrase), category, confidence (0-100), reasoning, language.
3. Confirm or reject the regex pre-filter matches above.
4. Find ADDITIONAL claims that regex may have missed.
5. Return ONLY a JSON array. No other text.

OUTPUT FORMAT (JSON array):
[
  {{
    "claim_text": "exact phrase from content",
    "category": "treatment|prevention|enhancement|general_wellness",
    "confidence": 85,
    "reasoning": "Brief explanation",
    "language": "en|no"
  }}
]

If no health claims found, return: []
"""

    def _parse_llm_response(self, response: str) -> list[dict]:
        """Parse LLM JSON response.

        Handles markdown code blocks and validates fields.
        Returns empty list on parse failure (graceful degradation).
        """
        text = response.strip()

        # Strip markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
            return []

        if not isinstance(data, list):
            logger.warning("LLM response is not a JSON array")
            return []

        validated = []
        for item in data:
            if not isinstance(item, dict):
                continue
            if "claim_text" not in item or "category" not in item:
                continue
            validated.append(item)

        return validated

    def _merge_claims(
        self,
        regex_matches: list[PatternMatch],
        llm_claims: list[dict],
    ) -> list[ClaimExtractionResult]:
        """Merge regex matches with LLM claims.

        - Regex confirmed by LLM → confidence 90, method "hybrid"
        - Regex only (LLM missed) → confidence 60, method "regex"
        - LLM only (regex missed) → confidence 75, method "llm"
        """
        results: list[ClaimExtractionResult] = []
        llm_matched: set[int] = set()  # indices of LLM claims matched to regex

        # Process regex matches
        for rm in regex_matches:
            llm_idx = self._find_llm_match(rm, llm_claims)
            if llm_idx is not None:
                llm_matched.add(llm_idx)
                llm_claim = llm_claims[llm_idx]
                eu_ref = self._config.eu_article_mapping.get(
                    llm_claim.get("category", rm.category)
                )
                results.append(ClaimExtractionResult(
                    claim_text=rm.matched_text,
                    surrounding_context=rm.surrounding_context,
                    claim_category=llm_claim.get("category", rm.category),
                    confidence_score=CONFIDENCE_HYBRID,
                    language_detected=llm_claim.get("language", rm.language),
                    extraction_method="hybrid",
                    eu_article_reference=eu_ref,
                    matched_pattern=rm.pattern,
                    llm_reasoning=llm_claim.get("reasoning"),
                ))
            else:
                eu_ref = self._config.eu_article_mapping.get(rm.category)
                results.append(ClaimExtractionResult(
                    claim_text=rm.matched_text,
                    surrounding_context=rm.surrounding_context,
                    claim_category=rm.category,
                    confidence_score=CONFIDENCE_REGEX_ONLY,
                    language_detected=rm.language,
                    extraction_method="regex",
                    eu_article_reference=eu_ref,
                    matched_pattern=rm.pattern,
                ))

        # Process LLM-only claims (regex missed)
        for i, llm_claim in enumerate(llm_claims):
            if i in llm_matched:
                continue
            category = llm_claim.get("category", "enhancement")
            eu_ref = self._config.eu_article_mapping.get(category)
            results.append(ClaimExtractionResult(
                claim_text=llm_claim.get("claim_text", ""),
                surrounding_context="",
                claim_category=category,
                confidence_score=CONFIDENCE_LLM_ONLY,
                language_detected=llm_claim.get("language", "unknown"),
                extraction_method="llm",
                eu_article_reference=eu_ref,
                llm_reasoning=llm_claim.get("reasoning"),
            ))

        # Deduplicate overlapping claims
        return self._deduplicate(results)

    def _find_llm_match(
        self, regex_match: PatternMatch, llm_claims: list[dict]
    ) -> int | None:
        """Find LLM claim matching a regex match by text overlap."""
        rm_text = regex_match.matched_text.lower()
        for i, lc in enumerate(llm_claims):
            lc_text = lc.get("claim_text", "").lower()
            if not lc_text:
                continue
            # Check overlap
            if rm_text in lc_text or lc_text in rm_text:
                return i
            # Fuzzy: check word overlap
            rm_words = set(rm_text.split())
            lc_words = set(lc_text.split())
            if rm_words and lc_words:
                overlap = len(rm_words & lc_words) / max(len(rm_words), len(lc_words))
                if overlap >= OVERLAP_THRESHOLD:
                    return i
        return None

    @staticmethod
    def _deduplicate(claims: list[ClaimExtractionResult]) -> list[ClaimExtractionResult]:
        """Remove duplicate claims, keeping highest confidence."""
        if not claims:
            return claims

        unique: list[ClaimExtractionResult] = []
        for claim in claims:
            is_dup = False
            for i, existing in enumerate(unique):
                if _text_overlap(claim.claim_text, existing.claim_text) >= OVERLAP_THRESHOLD:
                    is_dup = True
                    if claim.confidence_score > existing.confidence_score:
                        unique[i] = claim
                    break
            if not is_dup:
                unique.append(claim)

        return unique


def _text_overlap(a: str, b: str) -> float:
    """Calculate word-level overlap between two texts."""
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return 0.0
    return len(a_words & b_words) / max(len(a_words), len(b_words))


__all__ = [
    "ClaimLLMClassifier",
    "LLMClientProtocol",
    "RetryMiddlewareProtocol",
]
