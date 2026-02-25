# B2B Lead Scoring Approach

**Date:** 2026-02-09
**Purpose:** Epic 5 - Story 5-2 Lead Information Enrichment
**Model:** Point-based scoring system (0-100)

---

## Overview

Lead scoring prioritizes outreach by assigning points based on:
1. **Fit Score** - How well lead matches ideal customer profile (ICP)
2. **Intent Score** - Signals of buying interest
3. **Engagement Score** - Interaction with our content/outreach

## Scoring Model

### Total Score = Fit (40%) + Intent (30%) + Engagement (30%)

| Component | Max Points | Weight |
|-----------|------------|--------|
| Fit Score | 40 | 40% |
| Intent Score | 30 | 30% |
| Engagement Score | 30 | 30% |
| **Total** | **100** | 100% |

---

## 1. Fit Score (0-40 points)

How well the lead matches our Ideal Customer Profile.

### Company Size (0-10 points)

| Size | Points | Rationale |
|------|--------|-----------|
| 1-10 employees | 3 | Too small, limited budget |
| 11-50 employees | 7 | Growing, good fit |
| 51-200 employees | 10 | Sweet spot |
| 201-1000 employees | 8 | Good, may have existing solutions |
| 1000+ employees | 5 | Enterprise, long sales cycle |

### Industry (0-10 points)

| Industry | Points |
|----------|--------|
| E-commerce / DTC brands | 10 |
| Health & wellness | 10 |
| Sustainable products | 10 |
| Food & beverage | 8 |
| Beauty & cosmetics | 8 |
| Fashion | 7 |
| B2B SaaS | 5 |
| Other | 3 |

### Job Title (0-10 points)

| Role | Points |
|------|--------|
| Founder / CEO / Owner | 10 |
| CMO / VP Marketing | 10 |
| Marketing Director / Manager | 8 |
| Head of Content / Social | 8 |
| Marketing Specialist | 5 |
| Other | 2 |

### Geography (0-10 points)

| Region | Points |
|--------|--------|
| Norway | 10 |
| Nordics (SE, DK, FI) | 9 |
| EU (GDPR region) | 7 |
| UK | 7 |
| US / Canada | 5 |
| Other | 3 |

---

## 2. Intent Score (0-30 points)

Signals that indicate buying interest.

### Website Activity (0-10 points)

| Activity | Points |
|----------|--------|
| Visited pricing page | +5 |
| Downloaded resource | +3 |
| Viewed case studies | +3 |
| Multiple page views | +2 |
| No website activity | 0 |

### Social Engagement (0-10 points)

| Signal | Points |
|--------|--------|
| Engaged with our content | +5 |
| Following our accounts | +3 |
| Mentioned relevant topics | +3 |
| Active on LinkedIn | +2 |

### Timing Signals (0-10 points)

| Signal | Points |
|--------|--------|
| Recently hired marketing role | +5 |
| Company raised funding | +5 |
| Launched new product | +4 |
| Expanding to new market | +4 |
| Posted about pain points | +3 |

---

## 3. Engagement Score (0-30 points)

Interaction with our outreach.

### Email Engagement (0-15 points)

| Action | Points |
|--------|--------|
| Replied to email | +15 |
| Clicked link in email | +8 |
| Opened email | +3 |
| Multiple opens | +2 |
| No engagement | 0 |

### Meeting/Call (0-15 points)

| Action | Points |
|--------|--------|
| Attended meeting | +15 |
| Scheduled meeting | +10 |
| Requested information | +5 |
| Asked questions | +3 |

---

## Score Thresholds

| Score Range | Classification | Action |
|-------------|----------------|--------|
| 80-100 | **Hot** | Immediate outreach, priority follow-up |
| 60-79 | **Warm** | Active outreach sequence |
| 40-59 | **Qualified** | Standard nurture sequence |
| 20-39 | **Cool** | Low-priority, quarterly touch |
| 0-19 | **Cold** | Archive or research more |

---

## Score Decay

Scores should decay over time to prioritize fresh leads:

| Time Since Last Activity | Decay |
|--------------------------|-------|
| 0-7 days | No decay |
| 8-14 days | -5 points |
| 15-30 days | -10 points |
| 31-60 days | -20 points |
| 60+ days | -30 points |

---

## Implementation

### Database Fields

```python
# In Lead model
score: float  # 0-100
score_breakdown: dict  # JSONB with component scores

# Example score_breakdown:
{
    "fit": {
        "company_size": 10,
        "industry": 8,
        "job_title": 10,
        "geography": 7,
        "total": 35
    },
    "intent": {
        "website_activity": 5,
        "social_engagement": 3,
        "timing_signals": 4,
        "total": 12
    },
    "engagement": {
        "email_engagement": 8,
        "meeting": 0,
        "total": 8
    },
    "decay_applied": -5,
    "calculated_at": "2026-02-09T12:00:00Z"
}
```

### Scoring Service

```python
class LeadScoringService:
    """Calculate lead scores based on ICP fit and engagement."""

    async def calculate_score(self, lead: Lead) -> tuple[float, dict]:
        """Calculate total score and breakdown."""
        fit = self._calculate_fit_score(lead)
        intent = self._calculate_intent_score(lead)
        engagement = self._calculate_engagement_score(lead)
        decay = self._calculate_decay(lead.updated_at)

        total = fit["total"] + intent["total"] + engagement["total"] + decay

        breakdown = {
            "fit": fit,
            "intent": intent,
            "engagement": engagement,
            "decay_applied": decay,
            "calculated_at": datetime.now(UTC).isoformat(),
        }

        return max(0, min(100, total)), breakdown
```

---

## Enrichment Sources

To populate scoring data, use these sources:

| Data Point | Source |
|------------|--------|
| Company size | Hunter.io, LinkedIn |
| Industry | Hunter.io, website |
| Job title | Hunter.io, LinkedIn |
| Website activity | Our analytics (future) |
| Social engagement | LinkedIn API (limited) |
| Timing signals | News APIs, LinkedIn |

---

## Iteration Plan

1. **MVP (Epic 5)**: Fit score only based on enrichment data
2. **v1.1**: Add intent signals from manual research
3. **v1.2**: Add engagement tracking from email opens/clicks
4. **v2.0**: Automated intent signals, ML-based scoring

---

## Configuration

Store weights in config for easy tuning:

```json
// config/dawo_lead_scoring.json
{
    "version": "2026-02",
    "weights": {
        "fit": 0.40,
        "intent": 0.30,
        "engagement": 0.30
    },
    "thresholds": {
        "hot": 80,
        "warm": 60,
        "qualified": 40,
        "cool": 20
    },
    "decay": {
        "enabled": true,
        "schedule_days": [7, 14, 30, 60],
        "decay_points": [0, -5, -10, -20, -30]
    }
}
```

---

## Sources

- HubSpot Lead Scoring Best Practices
- Salesforce Einstein Lead Scoring
- B2B Lead Scoring Benchmarks 2025
