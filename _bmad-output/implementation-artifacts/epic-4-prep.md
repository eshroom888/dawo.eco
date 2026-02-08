# Epic 4 Preparation - Approval & Auto-Publishing

**Date:** 2026-02-08
**Epic:** 4 - Approval & Auto-Publishing (7 stories)
**Status:** Preparation Complete

---

## Overview

Epic 4 focuses on the human-in-the-loop approval workflow and automated Instagram publishing. This document tracks the preparation work completed before story implementation begins.

---

## Preparation Checklist

### Infrastructure Ready

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| Instagram Graph API client | ✅ Ready | [integrations/instagram/client.py](../../integrations/instagram/client.py) | 33 tests passing |
| Discord embed notifications | ✅ Ready | [integrations/discord/client.py](../../integrations/discord/client.py) | Rich embeds for Epic 4 stories |
| React + CopilotKit UI | ✅ Platform | IMAGO.ECO | React 18 + CopilotKit v1.50 |
| FastAPI backend | ✅ Platform | IMAGO.ECO | Async endpoints ready |
| Redis job queue | ✅ Platform | IMAGO.ECO | ARQ for scheduled publishing |

### Credentials Required

| Service | Env Variable | Status | Setup Guide |
|---------|--------------|--------|-------------|
| Instagram Graph API | `INSTAGRAM_ACCESS_TOKEN` | ⏳ Pending | [Meta Business Suite](https://business.facebook.com/) |
| Instagram Business ID | `INSTAGRAM_BUSINESS_ACCOUNT_ID` | ⏳ Pending | From Meta Business Suite |
| Discord Webhook | `DISCORD_WEBHOOK_URL` | ✅ Template | Already in .env.example |

---

## New Integrations Created

### 1. Instagram Publishing Client

**Location:** [integrations/instagram/](../../integrations/instagram/)

**Features:**
- Two-step container-based publishing (create → poll → publish)
- Async polling with configurable intervals
- Comprehensive error handling
- Rate limit awareness (25 posts/24h)

**Usage:**
```python
from integrations.instagram import InstagramPublishClient, PublishResult

client = InstagramPublishClient(
    access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN"),
    business_account_id=os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID"),
)

result = await client.publish_image(
    image_url="https://cdn.example.com/image.jpg",
    caption="Post caption with #hashtags",
)

if result.success:
    print(f"Published: {result.media_id}")
else:
    print(f"Failed: {result.error_message}")
```

**Tests:** 33 tests in [tests/integrations/instagram/test_client.py](../../tests/integrations/instagram/test_client.py)

### 2. Enhanced Discord Notifications

**Location:** [integrations/discord/client.py](../../integrations/discord/client.py)

**New Features:**
- Rich embed support (`DiscordEmbed`, `EmbedField`, `EmbedColor`)
- `send_embed()` - Generic embed sending
- `send_approval_notification()` - Story 4.6
- `send_publish_notification()` - Story 4.7
- `send_daily_summary()` - Story 4.7

**Usage:**
```python
from integrations.discord import DiscordWebhookClient, DiscordEmbed, EmbedColor

client = DiscordWebhookClient(webhook_url=os.getenv("DISCORD_WEBHOOK_URL"))

# Approval notification
await client.send_approval_notification(
    pending_count=5,
    compliance_warnings=1,
    dashboard_url="https://app.dawo.eco/approvals",
)

# Publish notification
await client.send_publish_notification(
    post_title="New mushroom post",
    instagram_url="https://instagram.com/p/...",
    success=True,
)

# Daily summary
await client.send_daily_summary(
    published_count=3,
    pending_count=2,
    failed_count=0,
)
```

---

## Story Dependencies

| Story | Title | Dependencies |
|-------|-------|--------------|
| 4-1 | Content Approval Queue UI | Epic 3 content generators, React frontend |
| 4-2 | Approve/Reject/Edit Actions | Story 4-1, compliance validators |
| 4-3 | Batch Approval Capability | Story 4-1, Story 4-2 |
| 4-4 | Content Scheduling Interface | Story 4-2, ARQ job queue |
| 4-5 | Instagram Graph API Auto-Publishing | Story 4-4, **Instagram client (ready)** |
| 4-6 | Discord Approval Notifications | Story 4-1, **Discord embeds (ready)** |
| 4-7 | Discord Publish Notifications | Story 4-5, **Discord embeds (ready)** |

---

## Architecture Notes

### Content Flow for Epic 4

```
[Epic 3: Content Generation]
         ↓
    [Approval Queue] ← Story 4-1
         ↓
[Approve/Reject/Edit] ← Story 4-2, 4-3
         ↓
    [Schedule Post] ← Story 4-4
         ↓
[Instagram Publish] ← Story 4-5 (uses new Instagram client)
         ↓
[Discord Notify] ← Story 4-6, 4-7 (uses enhanced Discord client)
```

### Key Patterns from Epic 3 to Continue

1. **Protocol + Implementation pattern** for any new generators/validators
2. **TYPE_CHECKING** for circular import prevention
3. **Complete __init__.py exports** from story start
4. **LLM tier specification** (tier="generate" or tier="scan")

---

## Remaining Setup Before Stories

### Instagram API Access (Required for Story 4-5)

1. Create Facebook App at [developers.facebook.com](https://developers.facebook.com/)
2. Add Instagram Graph API product
3. Connect Instagram Business Account
4. Generate long-lived access token
5. Add to `.env`:
   ```
   INSTAGRAM_ACCESS_TOKEN=your_token_here
   INSTAGRAM_BUSINESS_ACCOUNT_ID=your_account_id
   ```

### Discord Webhook (Required for Stories 4-6, 4-7)

1. Create webhook in Discord server settings
2. Add to `.env`:
   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```

---

## Test Coverage

| Integration | Tests | Status |
|-------------|-------|--------|
| Instagram Publishing | 33 | ✅ All passing |
| Discord Alerts | 7 | ✅ Existing tests |
| Discord Embeds | - | Uses same client |

---

## Ready for Implementation

Epic 4 preparation is complete. All integration clients are ready for stories 4-5, 4-6, and 4-7.

**Next Step:** Run `/bmad:bmm:workflows:create-story` to start with story 4-1.

---

*Prepared: 2026-02-08*
*DAWO.ECO Epic 4 Preparation*
