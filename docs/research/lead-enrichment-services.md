# Lead Enrichment Services Evaluation

**Date:** 2026-02-09
**Purpose:** Epic 5 - Story 5-2 Lead Information Enrichment

---

## Overview

Evaluated three major lead enrichment services for B2B outreach automation:
1. Apollo.io
2. Hunter.io
3. Clearbit

## Comparison Matrix

| Feature | Apollo.io | Hunter.io | Clearbit |
|---------|-----------|-----------|----------|
| **Primary Focus** | Sales intelligence | Email discovery | Data enrichment |
| **Email Discovery** | Yes | Yes (specialized) | Limited |
| **Data Points** | 60+ | Email-focused | 100+ |
| **API Access** | Enterprise only | All plans | Custom |
| **Free Tier** | 10K credits/mo* | 25 searches/mo | No |
| **Pricing Model** | Per-user + credits | Credits | Custom |
| **GDPR Compliant** | Yes | Yes | Yes |

*10K credits with verified corporate email domain; 100 credits otherwise

---

## Apollo.io

### Pricing (2026)

| Plan | Monthly | Annual | Credits/Month |
|------|---------|--------|---------------|
| Free | $0 | $0 | 10,000* |
| Basic | $49/user | $39/user | 5,000 |
| Professional | $79/user | $59/user | 10,000 |
| Organization | $119/user | $99/user | 15,000 |

### Credit Costs
- Email reveal: 1 credit
- Phone number: 5 credits
- Enrichment: 1-9 credits/record
- Overage: $0.20/credit (min 250)

### API Access
- **Requires Organization plan ($119+/user/mo)**
- Custom API pricing based on volume
- Rate limits apply

### Pros
- Comprehensive database (265M+ contacts)
- Built-in email sequences
- Chrome extension
- CRM integrations

### Cons
- API requires expensive plan
- Credit system can be confusing
- Data accuracy varies by region

---

## Hunter.io

### Pricing (2026)

| Plan | Monthly | Searches | Verifications |
|------|---------|----------|---------------|
| Free | $0 | 25 | 50 |
| Starter | $49/mo | 500 | 1,000 |
| Growth | $149/mo | 5,000 | 10,000 |
| Business | $499/mo | 50,000 | 100,000 |

### API Access
- Available on all plans
- RESTful API
- Generous rate limits

### Features
- Email Finder
- Email Verifier
- Domain Search
- Author Finder (from articles)
- Campaigns (outreach)

### Pros
- Affordable API access
- Simple, focused tool
- Good email verification
- Clearbit replacement available

### Cons
- Email-focused only
- Limited company data
- No phone numbers

---

## Clearbit

### Pricing
- **No public pricing** - sales call required
- Enterprise-focused
- Based on data volume and features

### Features
- 100+ data points per company
- Real-time enrichment
- Website visitor identification
- Firmographics & technographics
- Form shortening

### API Capabilities
- Enrichment API
- Reveal API (website visitors)
- Prospector API
- Risk API

### Pros
- Most comprehensive data
- Real-time enrichment
- HubSpot native integration
- High accuracy

### Cons
- Expensive (enterprise pricing)
- No public API pricing
- Overkill for small operations

---

## Recommendation for DAWO.ECO

### Best Option: **Hunter.io**

**Reasons:**
1. **API access on all plans** - can start with $49/mo
2. **Email-focused** - matches Epic 5 outreach needs
3. **Simple integration** - clear REST API
4. **Budget-friendly** - predictable costs
5. **Clearbit replacement** - offers enrichment API as Clearbit alternative

### Alternative: **Apollo.io Free Tier**

**If 10K credits/month is sufficient:**
- Use Apollo for lead discovery
- Export data manually
- Good for testing/MVP

### Integration Strategy

```
Lead Source → Hunter.io (email discovery) → DAWO DB
                  ↓
           Email Verification
                  ↓
           LLM Outreach Generation
                  ↓
           Gmail API Send
```

---

## API Integration Notes

### Hunter.io API Example

```python
import httpx

HUNTER_API_KEY = os.environ["HUNTER_API_KEY"]

async def find_email(domain: str, first_name: str, last_name: str):
    """Find email using Hunter.io API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.hunter.io/v2/email-finder",
            params={
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": HUNTER_API_KEY,
            }
        )
        data = response.json()
        return data.get("data", {}).get("email")

async def verify_email(email: str):
    """Verify email deliverability."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.hunter.io/v2/email-verifier",
            params={
                "email": email,
                "api_key": HUNTER_API_KEY,
            }
        )
        data = response.json()
        return data.get("data", {}).get("status") == "valid"
```

### Rate Limits (Hunter.io)

| Plan | Requests/Second |
|------|-----------------|
| Free | 1 |
| Starter | 10 |
| Growth | 20 |
| Business | 40 |

---

## Next Steps

1. [ ] Sign up for Hunter.io Starter plan ($49/mo)
2. [ ] Get API key and test integration
3. [ ] Implement email finder protocol
4. [ ] Add email verification step
5. [ ] Integrate with DAWO lead database

---

## Sources

- [Apollo.io Pricing Plans](https://www.apollo.io/pricing)
- [Apollo.io API Pricing](https://docs.apollo.io/docs/api-pricing)
- [Hunter.io Clearbit Alternative](https://hunter.io/clearbit-enrichment-api-alternative)
- [Apollo.io Pricing Analysis - Persana AI](https://persana.ai/blogs/apollo-io-pricing)
- [Lead Enrichment Tools Comparison - Knock AI](https://www.knock-ai.com/blog/data-enrichment-tools)
- [Apollo.io Competitors - Cognism](https://www.cognism.com/blog/apollo-competitors)
