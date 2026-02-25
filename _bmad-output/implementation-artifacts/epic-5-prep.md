# Epic 5 Preparation Tasks

**Created:** 2026-02-09
**Epic:** 5 - B2B Sales Pipeline
**Status:** Pre-implementation

---

## Carryover from Epic 4 Retrospective

### Process Improvements (Priority: High)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Pre-submission code review checklist | Dev Team | **Done** | [docs/pre-submission-checklist.md](../../docs/pre-submission-checklist.md) |
| 2 | Add deprecation linting to CI | Charlie | **Done** | [.github/workflows/ci.yml](../../.github/workflows/ci.yml) + ruff DTZ rules |
| 3 | Mock verification pattern documentation | Charlie | **Done** | [docs/mock-verification-patterns.md](../../docs/mock-verification-patterns.md) |

### Technical Debt (Priority: Medium)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Complete WebSocket event wiring | Dev Team | **Done** | [ui/backend/routers/websocket.py](../../ui/backend/routers/websocket.py) + fixed datetime.utcnow |
| 2 | Integration test coverage | QA | **Done** | [tests/integration/test_publish_flow.py](../../tests/integration/test_publish_flow.py) |
| 3 | Rate limit config externalization | Dev Team | **Done** | [core/config.py](../../core/config.py) + [config/dawo_rate_limits.json](../../config/dawo_rate_limits.json) |

---

## Epic 5 Specific Preparation

### Research Tasks

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | LinkedIn API research | Dev Team | **Done** | [docs/research/linkedin-api-research.md](../../docs/research/linkedin-api-research.md) |
| 2 | Gmail API OAuth setup | eshroom | **Done** | [docs/research/gmail-api-setup.md](../../docs/research/gmail-api-setup.md) - Token saved |
| 3 | Lead enrichment services evaluation | Dev Team | **Done** | [docs/research/lead-enrichment-services.md](../../docs/research/lead-enrichment-services.md) - Recommend Hunter.io |
| 4 | CRM integration patterns | Dev Team | **Done** | [docs/research/crm-integration-patterns.md](../../docs/research/crm-integration-patterns.md) - Recommend internal DB for MVP |

### Infrastructure Setup

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Gmail API credentials | eshroom | **Done** | `credentials/gmail-token.json` - gmail.send scope |
| 2 | Lead database schema design | Architect | **Done** | [core/leads/models.py](../../core/leads/models.py) + migration |
| 3 | Email template system | Dev Team | Pending | Personalized outreach templates |

### Knowledge Development

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | B2B lead scoring algorithms | Dev Team | **Done** | [docs/research/lead-scoring-approach.md](../../docs/research/lead-scoring-approach.md) |
| 2 | Email deliverability best practices | Dev Team | Pending | Avoid spam filters |
| 3 | GDPR compliance for B2B outreach | Legal/Dev | **Done** | [docs/research/gdpr-b2b-outreach.md](../../docs/research/gdpr-b2b-outreach.md) |

---

## Epic 5 Stories Overview

| Story | Title | Dependencies |
|-------|-------|--------------|
| 5-1 | B2B Lead Research Scanner | Research pool patterns from Epic 2 |
| 5-2 | Lead Information Enrichment | 5-1 |
| 5-3 | Personalized Outreach Draft Generator | 5-2, LLM tier system |
| 5-4 | Gmail API Integration | Gmail credentials |
| 5-5 | Lead Pipeline Status Tracking | 5-1 through 5-4 |

---

## Definition of Ready for Epic 5

- [x] All "High" priority carryover tasks completed
- [x] Gmail API credentials obtained and tested
- [x] Lead database schema designed and reviewed
- [x] B2B lead scoring approach documented
- [x] GDPR compliance requirements clarified

---

## Notes

- Epic 5 builds on Epic 2's scanner patterns for lead research
- LLM tier system from Epic 1 applies to outreach generation
- Protocol + Implementation pattern continues from Epic 3/4
