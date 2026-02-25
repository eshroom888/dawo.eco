# UTM Tracking & Link Shortening Research

**Date:** 2026-02-19
**Epic:** 7 - Analytics & System Operations
**Stories:** 7-2 (UTM Click-Through Tracking)

## Summary

DAWO.ECO already has UTM generation in two places: `integrations/shopify/utm.py` (Instagram posts) and `teams/dawo/leads/gmail/utm.py` (B2B outreach). For click tracking, the recommended approach is a custom FastAPI short-link redirect endpoint combined with Shopify native UTM attribution and GA4.

## Key Findings

### Existing UTM Scheme (Already Implemented)
- Instagram: `utm_source=instagram, utm_medium=post, utm_campaign={content_type}, utm_content={post_id}`
- Email: `utm_source=email, utm_medium=outreach, utm_campaign=b2b_outreach, utm_content={lead_id}`

### Link Shortening Decision
Build custom `/l/{code}` redirect in FastAPI -- zero dependencies, full data ownership, GDPR-compliant.

### Three-Layer Click Tracking
1. Custom redirect endpoint (click-level data we own)
2. Shopify native UTM attribution (revenue, free)
3. GA4 on Shopify store (funnel analysis)

### Attribution Windows
| Channel | Window | Rationale |
|---------|--------|-----------|
| Instagram DTC | 30 days | Matches Shopify native |
| B2B email outreach | 90 days | Longer B2B sales cycle |
| Story link sticker | 7 days | Stories expire in 24h |

### Database Schema (3 tables)
- `short_links` -- code, destination URL, denormalized UTM fields, post_id
- `link_clicks` -- append-only, IP hash (GDPR), user-agent, device
- `utm_attributions` -- order-level, first-touch + last-touch, revenue

### Instagram Link Constraints
| Placement | Clickable? | Strategy |
|-----------|-----------|----------|
| Bio link | Yes | Rotate per campaign or self-hosted landing page |
| Story link sticker | Yes | Per-story UTM short link |
| Feed caption | No | "Lenke i bio" CTA + bio link |
| Shopping tags | Yes | Bypasses UTM, Shopify tracks directly |

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Link shortener | Custom FastAPI `/l/{code}` | Zero deps, GDPR, data ownership |
| Short code generation | `secrets.token_urlsafe(6)` | stdlib, crypto-random |
| IP storage | SHA-256 hash only | GDPR compliance |
| New dependencies | None needed | `urllib.parse` + `secrets` + existing stack |
| Optional dependency | `user-agents` for device parsing | Only if device breakdown needed |

---
*Research for Epic 7 Story 7-2*
