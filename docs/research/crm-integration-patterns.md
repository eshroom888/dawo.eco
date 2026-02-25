# CRM Integration Patterns Research

**Date:** 2026-02-09
**Purpose:** Epic 5 - B2B Sales Pipeline - External CRM Connectivity

---

## Overview

Research on CRM integration patterns for B2B sales pipeline automation. Evaluates whether DAWO.ECO needs external CRM integration or can use built-in lead tracking.

## Key CRM Platforms

| CRM | Target Market | Python SDK | API Style | Free Tier |
|-----|---------------|------------|-----------|-----------|
| **HubSpot** | SMB-Enterprise | Official | REST | Yes (limited) |
| **Pipedrive** | SMB-Mid | Official | REST | No (trial only) |
| **Salesforce** | Enterprise | Official | REST/SOAP | No |
| **Airtable** | Flexible/Small | Official | REST | Yes |
| **Monday.com** | Project-focused | Official | GraphQL | Yes |

---

## Integration Patterns

### Pattern 1: Internal Lead Database (Recommended for MVP)

```
DAWO Lead Scanner → PostgreSQL (DAWO DB) → Lead Pipeline UI
                              ↓
                        Email Outreach
```

**Pros:**
- Full control over data model
- No external dependencies
- No additional costs
- Matches existing Protocol pattern

**Cons:**
- Must build pipeline UI
- No cross-system sync

### Pattern 2: CRM as Source of Truth

```
DAWO Lead Scanner → External CRM API → CRM Pipeline
                           ↑
                   DAWO reads from CRM
```

**Pros:**
- Sales team familiar with CRM
- Built-in reporting
- Mobile apps

**Cons:**
- API rate limits
- Data sync complexity
- Additional subscription cost

### Pattern 3: Bi-directional Sync

```
DAWO DB ←→ Sync Service ←→ External CRM
```

**Pros:**
- Best of both worlds
- Offline capability

**Cons:**
- Conflict resolution complexity
- Highest development effort

---

## CRM API Comparison

### HubSpot

```python
# HubSpot API Example
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput

client = HubSpot(access_token=os.environ["HUBSPOT_TOKEN"])

# Create contact
properties = {
    "email": "lead@company.com",
    "firstname": "John",
    "lastname": "Doe",
    "company": "Acme Inc",
}
contact = SimplePublicObjectInput(properties=properties)
response = client.crm.contacts.basic_api.create(simple_public_object_input=contact)
```

**Rate Limits:**
- 100 requests per 10 seconds per API key
- 150,000 requests per day

**Pricing:**
- Free: Basic CRM features
- Starter: $20/user/mo
- Professional: $100/user/mo

### Pipedrive

```python
# Pipedrive API Example
from pipedrive.client import Client

client = Client(domain="your-company")
client.set_api_token(os.environ["PIPEDRIVE_TOKEN"])

# Create person (lead)
person = client.persons.create_person({
    "name": "John Doe",
    "email": ["lead@company.com"],
    "org_id": org_id,
})

# Create deal
deal = client.deals.create_deal({
    "title": "B2B Outreach - Acme Inc",
    "person_id": person["id"],
    "stage_id": pipeline_stage_id,
})
```

**Rate Limits:**
- 100 requests per 10 seconds
- Soft limit, not hard cutoff

**Pricing:**
- Essential: $14/user/mo
- Advanced: $34/user/mo
- Professional: $49/user/mo

### Airtable (Lightweight Option)

```python
# Airtable API Example
from pyairtable import Api

api = Api(os.environ["AIRTABLE_TOKEN"])
table = api.table("appXXX", "Leads")

# Create lead record
record = table.create({
    "Name": "John Doe",
    "Email": "lead@company.com",
    "Company": "Acme Inc",
    "Status": "New",
    "Source": "LinkedIn",
})
```

**Rate Limits:**
- 5 requests per second per base

**Pricing:**
- Free: 1,200 records/base
- Team: $20/user/mo (50K records)

---

## Recommendation for DAWO.ECO

### Phase 1: Internal Lead Database (Epic 5)

**Build Story 5-5 with internal PostgreSQL-based lead tracking:**

1. Lead model in DAWO DB
2. Pipeline status tracking
3. Basic reporting

**Rationale:**
- Matches existing architecture (SQLAlchemy, PostgreSQL)
- No additional costs
- Full control over data model
- Can always add CRM sync later

### Phase 2: Optional CRM Sync (Future Epic)

**If sales team needs external CRM:**

1. Implement CRM Protocol interface
2. Build adapters for HubSpot/Pipedrive
3. Add bi-directional sync service

```python
# Protocol pattern for CRM integration
from typing import Protocol

class CRMClientProtocol(Protocol):
    """Protocol for CRM integration."""

    async def create_contact(self, data: LeadData) -> str:
        """Create contact in CRM, return ID."""
        ...

    async def update_pipeline_stage(self, contact_id: str, stage: str) -> bool:
        """Update deal/pipeline stage."""
        ...

    async def sync_activity(self, contact_id: str, activity: Activity) -> None:
        """Log activity (email sent, etc.)."""
        ...
```

---

## Lead Database Schema (Internal)

For Epic 5 Story 5-5, build lead tracking in DAWO DB:

```python
class Lead(Base):
    """B2B Lead for outreach pipeline."""

    __tablename__ = "leads"

    id: Mapped[UUID] = mapped_column(primary_key=True)

    # Contact info
    email: Mapped[str]
    first_name: Mapped[str]
    last_name: Mapped[str]
    company: Mapped[str]
    job_title: Mapped[Optional[str]]

    # Pipeline
    status: Mapped[str]  # new, contacted, replied, qualified, converted, lost
    score: Mapped[float]  # 0-100 lead score

    # Source tracking
    source: Mapped[str]  # linkedin, website, referral
    enriched_at: Mapped[Optional[datetime]]
    enrichment_data: Mapped[Optional[dict]]  # JSONB

    # Activity
    last_contacted_at: Mapped[Optional[datetime]]
    contact_count: Mapped[int]
    reply_received: Mapped[bool]

    # Timestamps
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

---

## Next Steps

1. [ ] Build internal lead model for Epic 5
2. [ ] Implement pipeline status tracking
3. [ ] Create basic lead pipeline UI
4. [ ] Defer CRM integration to future epic if needed

---

## Sources

- [CRM API Integration Patterns - APIDeck](https://www.apideck.com/blog/25-crm-apis-to-integrate-with)
- [Pipedrive API Features](https://www.pipedrive.com/en/features/crm-api)
- [AI Agents for CRM - DEV Community](https://dev.to/alifar/ai-agents-for-crm-integrations-pipedrive-hubspot-and-airtable-compared-kle)
- [AI SDR Tools with CRM - Monday.com](https://monday.com/blog/crm-and-sales/ai-sdr-tools-integrate-crm-systems/)
- [Pipedrive vs HubSpot Comparison](https://coldiq.com/blog/pipedrive-vs-hubspot)
