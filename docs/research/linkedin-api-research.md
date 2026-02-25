# LinkedIn API Research

**Date:** 2026-02-09
**Purpose:** Epic 5 - B2B Lead Research Scanner

---

## Overview

LinkedIn provides APIs for B2B lead data access, but with significant restrictions and partnership requirements.

## Access Requirements

### Partnership Required
- Must become a **LinkedIn Partner** to access APIs
- APIs only available to businesses and app developers with authorization
- Cannot access arbitrarily - must demonstrate legitimate business use case

### Pricing Tiers
| Plan | Price | Limit |
|------|-------|-------|
| Basic | Free | 3 profiles |
| Standard | $59/month | 500 profiles |
| Premium | $499/month | 10,000 profiles |

## Rate Limits

### Structure
- **Application-level limit**: Total calls the app can make per day
- **Member-level limit**: Calls a single user can make per day
- Limits reset at **midnight UTC**

### Key Points
- Specific limits are **NOT published** - must check Developer Portal
- Rate-limited requests return **HTTP 429**
- Email alerts at 75% quota (1-2 hour delay)
- Application admins receive alerts, not member-level

### Finding Your Limits
1. Go to [Developer Portal](https://www.linkedin.com/developers/apps)
2. Select application
3. Navigate to **Analytics tab**
4. View usage (requires at least 1 request today)

## Authentication

### OAuth 2.0 Scopes
| Scope | Purpose |
|-------|---------|
| `r_liteprofile` | Read basic profile data |
| `r_emailaddress` | Read email address |
| `w_member_social` | Post on behalf of member |
| `r_organization_social` | Read organization data |
| `w_organization_social` | Post as organization |

### Products
- **Advertising API**: Ad campaign management
- **Community Management**: Organization page management
- **Lead Sync**: Lead form data (requires partnership)
- **Conversions API**: Track conversions

## Available Data

### Profile Data (Limited)
- Basic profile information
- Company information
- Job title
- Location

### What's NOT Available
- Email addresses (without explicit permission)
- Connection lists
- Messaging
- Automated connection requests

## Compliance Considerations

### Terms of Service
- No scraping
- No automated actions without user consent
- Must display LinkedIn attribution
- Data retention limits apply

### GDPR (EU/Norway)
- Need legitimate interest or consent
- Right to erasure must be honored
- Data processing agreement required

## Alternative Approaches for Epic 5

Given LinkedIn's restrictive API access:

1. **LinkedIn Lead Gen Forms**: If running LinkedIn ads, leads self-submit
2. **Manual Export**: Users can export their connections
3. **Third-Party Services**: Apollo, Hunter.io, Clearbit (have own LinkedIn integrations)
4. **LinkedIn Sales Navigator API**: More access but expensive ($80+/user/month)

## Recommendation

For DAWO.ECO Epic 5 B2B Lead Research:

1. **Don't rely solely on LinkedIn API** - too restrictive for programmatic lead research
2. **Use lead enrichment services** (Apollo, Clearbit) that aggregate from multiple sources
3. **Consider LinkedIn Lead Gen Forms** if running paid campaigns
4. **Build generic lead scanner interface** that can work with multiple data sources

## Next Steps

- [ ] Evaluate lead enrichment services (Apollo, Hunter.io, Clearbit)
- [ ] Design lead scanner to be source-agnostic
- [ ] Check if LinkedIn Sales Navigator API is viable
- [ ] Review GDPR requirements for B2B outreach

---

## Sources

- [LinkedIn API Rate Limiting - Microsoft Learn](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits)
- [How to Use LinkedIn's API for Sales - Generect](https://generect.com/blog/linkedin-api/)
- [LinkedIn API Complete Guide - Evaboot](https://evaboot.com/blog/what-is-linkedin-api)
- [LinkedIn API for Developers - Unipile](https://www.unipile.com/linkedin-api-a-comprehensive-guide-to-integration/)
