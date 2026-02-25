# Instagram Graph API Insights Research

**Date:** 2026-02-19
**Epic:** 7 - Analytics & System Operations
**Stories:** 7-1 (Instagram Engagement Metrics Collection)

## Summary

The Instagram Graph API provides per-media insights via `/{media-id}/insights` endpoint. Metrics are lifetime cumulative values only -- no date-range filtering per post. To track metrics at intervals (24h, 48h, 7d), we must snapshot cumulative values and compute deltas.

## Key Findings

### Available Metrics (Image Posts)
`impressions`, `reach`, `likes`, `comments`, `saved`, `shares`, `total_interactions`

### Reels-Specific Metrics
`ig_reels_aggregated_all_plays_count`, `ig_reels_avg_watch_time`, `ig_reels_video_view_total_time`

### API Endpoint
```
GET /v19.0/{media-id}/insights?metric=impressions,reach,likes,comments,saved,shares,total_interactions&access_token={token}
```

### Rate Limits
- 200 API calls per user token per hour (shared across ALL Instagram API operations)
- Budget estimation: ~105 calls/hour currently used, ~95 buffer remaining

### Authentication
- Requires `instagram_manage_insights` scope (may already be approved with `instagram_content_publish`)
- Verify via debug_token endpoint

### Collection Strategy
```
T+1h    Baseline snapshot (metrics stabilize after ~30 min)
T+24h   Day 1 snapshot
T+48h   Day 2 snapshot
T+7d    Final snapshot
```

### Proposed Schema
```sql
CREATE TABLE instagram_media_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id VARCHAR(100) NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL,
    snapshot_label VARCHAR(20) NOT NULL,  -- 'baseline', '24h', '48h', '7d'
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    saved INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    total_interactions INTEGER DEFAULT 0,
    plays INTEGER,                        -- Reel-specific
    avg_watch_time_ms INTEGER,            -- Reel-specific
    raw_response JSONB,
    UNIQUE(media_id, snapshot_label)
);
```

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Library | Extend existing httpx client | Zero dependencies, consistent with codebase |
| Metrics endpoint | `/insights` edge (not basic fields) | Full metric set including reach, saves, shares |
| Deprecated metric | Replace `engagement` with `total_interactions` | Deprecated in v18.0+ |
| Interval tracking | Snapshot + delta pattern | API only returns lifetime cumulative values |

## Gaps in Existing Code
- `get_media_insights()` in `integrations/instagram/client.py` uses deprecated `engagement` metric
- Missing `likes`, `comments`, `shares` from metric list
- Not part of `InstagramPublishClientProtocol`
- Insights calls not counted against shared quota tracker

## Limitations
- No reach-by-source breakdown per post
- No individual carousel slide metrics
- Story insights expire 48h after posting
- No real-time streaming/webhooks for metric changes
- Cannot backfill pre-authorization posts

---
*Research for Epic 7 Story 7-1*
