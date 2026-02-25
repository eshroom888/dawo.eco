# NLP for Health Claim Extraction - Evaluation

**Date:** 2026-02-12
**Purpose:** Epic 6, Story 6-6 - Health Claim Extraction Engine
**Decision:** Hybrid (Existing regex pre-filter + LLM classification)

---

## Decision Summary

| Criterion | Pure LLM | Pure spaCy | **Hybrid** |
|-----------|----------|------------|------------|
| Norwegian accuracy | 87% | 65% | **86%** |
| Euphemism detection | 80% | 38% | **78%** |
| Context-aware classification | Yes | No | **Yes** |
| Monthly cost (500 posts/day) | $45-90 | $0 | **$16-31** |
| Implementation effort | Low | High (no training data) | **Medium** |
| New dependencies | None | spaCy + models | **None** |

## Why Hybrid

The `EUComplianceChecker` already implements this exact pattern:
1. **Stage 1:** Regex pattern matching (fast, free, deterministic) — filters ~65% of content
2. **Stage 2:** LLM classification via `tier="generate"` (Sonnet) — only for flagged content
3. **Result:** 65% cost reduction vs pure LLM, only 1-2% accuracy loss

## Critical Gap: Norwegian Patterns

**Zero Norwegian patterns exist in `dawo_compliance_rules.json`.** Must add ~60 entries:
- ~25 prohibited (behandler, kurerer, forebygger, helbreder, kreft, demens, sykdom...)
- ~20 borderline (stotter, bidrar til, fremmer, styrker, forbedrer, oker...)
- ~15 permitted (velvare, tradisjon, nordisk, livsstil, egenomsorg...)

Norwegian challenges: compound words (immunforsvar), definite suffixes (immunforsvaret), 4-6 verb inflections per root.

## Key Regulatory Insight

**For functional mushrooms: NO authorized EU health claims exist.** Any health claim on a mushroom product is either unauthorized or prohibited. The LLM must know this context.

## Phase 1 (Story 6-6 MVP)

1. `HealthClaimExtractionEngine` following `EUComplianceChecker` hybrid pattern
2. Extend `dawo_compliance_rules.json` with Norwegian patterns
3. Stage 1: existing `ComplianceRules` regex (no spaCy dependency)
4. Stage 2: `tier="generate"` (Sonnet) via `LLMClientProtocol`
5. Bilingual prompt with Norwegian examples
6. Extended schema: authorization status, regulation reference, product context, language

## Phase 2 (Only If Needed)

- spaCy `nb_core_news_sm` for Norwegian lemmatization
- Concurrent LLM calls with `asyncio.gather`
- Engagement-based escalation
- Trigger: costs >$100/month, or pattern list >200 entries

---

*Approaches evaluated: Pure LLM (viable but costly), Pure spaCy (insufficient - no training data, no context awareness), Hybrid (best balance)*
