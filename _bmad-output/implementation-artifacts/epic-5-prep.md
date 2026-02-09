# Epic 5 Preparation Tasks

**Created:** 2026-02-09
**Epic:** 5 - B2B Sales Pipeline
**Status:** Pre-implementation

---

## Carryover from Epic 4 Retrospective

### Process Improvements (Priority: High)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Pre-submission code review checklist | Dev Team | Pending | Reduce 100% fix rate seen in Epic 4 |
| 2 | Add deprecation linting to CI | Charlie | Pending | Catch `datetime.utcnow()` style issues early |
| 3 | Mock verification pattern documentation | Charlie | Pending | Mocks must validate `response.success` |

### Technical Debt (Priority: Medium)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Complete WebSocket event wiring | Dev Team | Pending | Events emitted but connections need review |
| 2 | Integration test coverage | QA | Pending | End-to-end tests for publish flow |
| 3 | Rate limit config externalization | Dev Team | Pending | Move rate limit values to config |

---

## Epic 5 Specific Preparation

### Research Tasks

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | LinkedIn API research | Dev Team | Pending | B2B lead data access, rate limits |
| 2 | Gmail API OAuth setup | eshroom | Pending | Send permissions for outreach |
| 3 | Lead enrichment services evaluation | Dev Team | Pending | Clearbit, Hunter.io, Apollo alternatives |
| 4 | CRM integration patterns | Dev Team | Pending | If connecting to external CRM |

### Infrastructure Setup

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Gmail API credentials | eshroom | Pending | OAuth 2.0 for sending |
| 2 | Lead database schema design | Architect | Pending | B2B lead storage model |
| 3 | Email template system | Dev Team | Pending | Personalized outreach templates |

### Knowledge Development

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | B2B lead scoring algorithms | Dev Team | Pending | How to prioritize leads |
| 2 | Email deliverability best practices | Dev Team | Pending | Avoid spam filters |
| 3 | GDPR compliance for B2B outreach | Legal/Dev | Pending | Norwegian/EU requirements |

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

- [ ] All "High" priority carryover tasks completed
- [ ] Gmail API credentials obtained and tested
- [ ] Lead database schema designed and reviewed
- [ ] B2B lead scoring approach documented
- [ ] GDPR compliance requirements clarified

---

## Notes

- Epic 5 builds on Epic 2's scanner patterns for lead research
- LLM tier system from Epic 1 applies to outreach generation
- Protocol + Implementation pattern continues from Epic 3/4
