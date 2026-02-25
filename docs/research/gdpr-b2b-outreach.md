# GDPR Compliance for B2B Outreach

**Date:** 2026-02-09
**Purpose:** Epic 5 - B2B Sales Pipeline
**Jurisdiction:** Norway / EU (GDPR)

---

## Overview

B2B cold outreach is **permitted under GDPR** with proper legal basis and safeguards. This document outlines requirements for compliant B2B email outreach in Norway and the EU.

## Legal Basis for B2B Outreach

### Legitimate Interest (Article 6(1)(f))

B2B outreach typically relies on **Legitimate Interest**, which requires:

1. **Legitimate Purpose**: Business development is recognized as legitimate
2. **Necessity**: Email is necessary to reach decision-makers
3. **Balancing Test**: Our interest doesn't override recipient's rights

### When Legitimate Interest Applies

| Scenario | Valid? | Notes |
|----------|--------|-------|
| Contacting business email (work address) | Yes | Primary use case |
| Relevant to recipient's job function | Yes | Must be business-relevant |
| First-time cold outreach | Yes | With proper safeguards |
| Personal email address | No | Requires consent |
| Repeatedly contacting after opt-out | No | Must honor objections |

---

## Requirements Checklist

### Before Sending

- [ ] Using business email addresses only (not personal)
- [ ] Content is relevant to recipient's professional role
- [ ] Clear identification of sender (company name)
- [ ] Legitimate business purpose documented
- [ ] Easy opt-out mechanism included

### In Every Email

- [ ] Sender identity clearly stated
- [ ] Company name and contact info
- [ ] One-click unsubscribe link
- [ ] Physical address (for CAN-SPAM compliance)
- [ ] Brief explanation of why they received email

### After Sending

- [ ] Honor opt-out requests within 24 hours
- [ ] Maintain suppression list
- [ ] Document consent/objections
- [ ] Respond to data access requests within 30 days

---

## Norway-Specific Requirements

Norway follows GDPR via the **EEA Agreement** plus local implementation through **Personopplysningsloven**.

### Key Points for Norway

1. **Datatilsynet** (Norwegian DPA) is the supervisory authority
2. Same GDPR rules apply as in EU
3. **Marketing Act (Markedsføringsloven)** also applies
4. Electronic marketing requires basis under both GDPR and ePrivacy

### Norwegian Marketing Act

- B2B email is **permitted without consent** if:
  - Sent to business addresses
  - Relevant to recipient's work
  - Contains unsubscribe option
  - Sender is identifiable

---

## Email Template Requirements

### Required Elements

```
From: [Your Name] <your.name@imagoeco.com>
Subject: [Clear, honest subject line]

[Personalized greeting]

[Business-relevant content]

---
Why am I receiving this?
I'm reaching out because [legitimate reason relevant to their role].

Unsubscribe: [One-click unsubscribe link]

ImagoEco AS
[Address]
[Contact info]
```

### Unsubscribe Implementation

```python
# In OutreachEmail model, track unsubscribes
class Lead(Base):
    # ...
    unsubscribed_at: Optional[datetime]  # When they opted out
    unsubscribe_reason: Optional[str]    # Why (optional)

# Suppression list check before sending
async def can_send_email(lead: Lead) -> bool:
    if lead.unsubscribed_at:
        return False
    if lead.status == LeadStatus.LOST:
        return False
    return True
```

---

## Data Subject Rights

### Must Support

| Right | Requirement | Implementation |
|-------|-------------|----------------|
| **Right to Object** | Stop processing on request | Unsubscribe + suppression list |
| **Right of Access** | Provide data within 30 days | Export lead record as JSON/PDF |
| **Right to Erasure** | Delete on request | Soft delete or anonymize |
| **Right to Rectification** | Correct inaccurate data | Allow data updates |

### Response Timeline

- Acknowledge request: **24-48 hours**
- Complete request: **30 days** (max)
- Complex requests: **90 days** with notification

---

## Data Retention

### Retention Periods

| Data Type | Retention | Rationale |
|-----------|-----------|-----------|
| Active leads | Indefinite while engaged | Business need |
| Lost leads | 2 years | Re-engagement possibility |
| Unsubscribed | Email only, 7 years | Suppression list |
| Converted customers | Per customer agreement | Contract basis |

### After Retention

- Delete personal data
- Retain anonymized statistics
- Maintain suppression list (email hash only)

---

## Documentation Requirements

### Legitimate Interest Assessment (LIA)

Create and maintain LIA document covering:

1. **Purpose**: Why we're contacting leads
2. **Necessity**: Why email is needed
3. **Impact on Individuals**: How this affects them
4. **Safeguards**: How we protect their rights
5. **Conclusion**: Balance tips in our favor

### Record of Processing Activities

Maintain under Article 30:

```json
{
    "processing_activity": "B2B Email Outreach",
    "purpose": "Business development and sales",
    "legal_basis": "Legitimate interest (Art. 6(1)(f))",
    "data_categories": ["name", "email", "company", "job_title"],
    "recipients": ["Internal sales team"],
    "retention": "2 years after last contact",
    "security_measures": ["Encryption", "Access controls"]
}
```

---

## Implementation in DAWO

### Database Fields

```python
# Add to Lead model
class Lead(Base):
    # GDPR compliance fields
    legal_basis: str  # "legitimate_interest" or "consent"
    data_source: str  # Where data came from
    unsubscribed_at: Optional[datetime]
    erasure_requested_at: Optional[datetime]
    data_exported_at: Optional[datetime]
```

### Suppression List

```python
class SuppressionList(Base):
    """Emails that must never be contacted."""

    __tablename__ = "suppression_list"

    email_hash: str  # SHA-256 hash of email
    reason: str  # "unsubscribed", "bounced", "complaint"
    added_at: datetime
```

### Pre-Send Check

```python
async def validate_outreach(lead: Lead) -> tuple[bool, str]:
    """Check if outreach is GDPR compliant."""

    # Check suppression list
    if await is_suppressed(lead.email):
        return False, "Email is on suppression list"

    # Check unsubscribe status
    if lead.unsubscribed_at:
        return False, "Lead has unsubscribed"

    # Check if business email
    if not is_business_email(lead.email):
        return False, "Not a business email address"

    # Check erasure request
    if lead.erasure_requested_at:
        return False, "Erasure requested"

    return True, "OK"
```

---

## Email Frequency Limits

To avoid being seen as spam:

| Sequence | Max Emails | Spacing |
|----------|------------|---------|
| Initial outreach | 1 | - |
| Follow-up 1 | 1 | 3-5 days |
| Follow-up 2 | 1 | 5-7 days |
| Final follow-up | 1 | 7-14 days |
| **Total per lead** | **4** | Over 3-4 weeks |

If no response after 4 emails, move to "nurture" (quarterly touch) or "lost".

---

## Summary

### B2B Cold Email is Legal When:

1. Targeting business email addresses
2. Content relevant to their work
3. Clear sender identification
4. Easy unsubscribe option
5. Honoring opt-outs promptly
6. Documenting legitimate interest

### B2B Cold Email is NOT Legal When:

1. Using personal email addresses
2. Ignoring unsubscribe requests
3. Hiding sender identity
4. Continuing after objection
5. Excessive frequency (spam)

---

## Sources

- [GDPR Article 6 - Lawfulness of Processing](https://gdpr-info.eu/art-6-gdpr/)
- [ICO Guide to Legitimate Interest](https://ico.org.uk/for-organisations/guide-to-data-protection/guide-to-the-general-data-protection-regulation-gdpr/legitimate-interests/)
- [Datatilsynet (Norwegian DPA)](https://www.datatilsynet.no/)
- [Norwegian Marketing Act](https://lovdata.no/dokument/NL/lov/2009-01-09-2)
- [ePrivacy Directive and B2B](https://ec.europa.eu/digital-single-market/en/news/proposal-regulation-privacy-and-electronic-communications)
