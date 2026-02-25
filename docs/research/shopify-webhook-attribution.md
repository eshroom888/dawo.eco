# Shopify Webhook & Order Attribution Research

**Date:** 2026-02-19
**Epic:** 7 - Analytics & System Operations
**Stories:** 7-3 (Shopify Sales Attribution)

## Summary

Shopify order webhooks include `landing_site` field with full UTM query parameters. Parse `utm_content` to link orders to Instagram posts. Use `orders/paid` (not `orders/create`) as primary trigger -- only attribute confirmed revenue.

## Key Findings

### Webhook Topics to Subscribe
1. `orders/paid` -- primary attribution trigger (confirmed revenue)
2. `orders/cancelled` -- void attribution
3. `refunds/create` -- adjust attributed revenue

### Attribution Field: `landing_site`
Contains URL path + query string of customer's first pageview:
```
/products/lions-mane-extract?utm_source=instagram&utm_medium=post&utm_campaign=feed_post&utm_content=abc123
```
Parse UTM params from this field. `utm_content` is the attribution key (post_id).

### HMAC Verification
- Shopify signs webhooks with HMAC-SHA256
- Must use raw request body bytes (NOT re-serialized JSON)
- Use `hmac.compare_digest()` for timing-safe comparison
- Signing secret is separate from Admin API access token

### Delivery Behavior
- At-least-once delivery (must be idempotent)
- 5-second response timeout (process in background)
- 19 retries over 48 hours
- Auto-removes subscription after 48h of failures

### Attribution Model
Last-touch (per Story 7.3 spec). Store both first-touch and last-touch for future analysis.

### `customerJourneySummary` (Shopify Plus only)
Provides structured UTM objects with `firstVisit` and `lastVisit`. Standard plan must parse `landing_site` manually.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary webhook | `orders/paid` | Only confirmed revenue |
| Attribution model | Last-touch | Story 7.3 spec; simplest correct model |
| UTM source | Parse `landing_site` field | Works on all Shopify plans |
| Idempotency | `order_id` UNIQUE constraint | At-least-once delivery |
| Response strategy | Return 200, process in `BackgroundTasks` | 5-second timeout |
| Phase 2 processing | ARQ job queue | More reliable for production |
| Backfill | Hourly GraphQL polling | Safety net for missed webhooks |
| Refund handling | Subtract from attributed revenue | Accurate net revenue |

### Files to Create
- `integrations/shopify/webhook.py` -- HMAC verification, UTM extraction
- `integrations/shopify/attribution.py` -- `LastTouchAttributor`, dataclasses
- `core/analytics/models.py` -- SQLAlchemy models
- `ui/backend/routers/shopify_webhook.py` -- 3 webhook endpoints

### Environment Variable
```
SHOPIFY_WEBHOOK_SECRET=whsec_xxxxx  # Different from SHOPIFY_ACCESS_TOKEN
```

---
*Research for Epic 7 Story 7-3*
