# ARQ Job Queue Research

**Date:** 2026-02-19
**Epic:** 7 - Analytics & System Operations
**Stories:** 7-6 (Agent Schedule Configuration), 7-7 (Manual Team/Agent Triggers), 7-8 (Execution Logs)

## Summary

ARQ (Asynchronous Redis Queue) is the correct choice for DAWO.ECO agent scheduling. It's async-native, Redis-backed, and already in `requirements.txt`. Existing code in `core/scheduling/` already uses ARQ for content publishing. Agent scheduling should use a separate worker with different timeout/concurrency profiles.

## Key Findings

### ARQ Core Features
- 100% async-native (asyncio)
- Redis-only broker
- Built-in `arq.cron()` for scheduled jobs
- Job result storage in Redis with TTL
- `max_tries` + `Retry(defer=N)` for error handling
- `unique=True` prevents overlapping cron runs

### Cron Scheduling
ARQ uses Python sets, not cron strings. Need converter:
```python
# Standard cron: "0 5 * * 0" (Sunday 05:00)
# ARQ equivalent:
cron(run_scanner, weekday={6}, hour={5}, minute={0})
```
**Weekday mismatch:** Cron uses 0=Sunday, ARQ/Python uses 0=Monday, 6=Sunday.

### Existing DAWO.ECO ARQ Usage
- `core/scheduling/jobs.py` -- `enqueue_publish_job()` for content publishing
- `ui/backend/routers/schedule.py` -- `retry_publish` using ARQ
- Scanner configs already have `schedule_cron` fields in JSON

### Job Dependencies
No built-in chaining. Recommended: run full pipeline in single job (Harvester Framework is already cohesive). Manual chaining via `enqueue_job()` from within a job if needed.

### Status Tracking
- ARQ provides `Job.status()` and `Job.info()` (stored in Redis, ephemeral)
- For persistent history: wrap jobs with database logging to `JobExecutionLog` table
- `ctx["job_try"]` gives current attempt number (1-indexed)

### Manual Triggers
```python
pool = await create_pool(RedisSettings())
job = await pool.enqueue_job("run_health_claims_scanner")
```

### Limitations
- No built-in dead letter queue
- No cron string parsing (need converter)
- No job chains/dependency graphs
- No built-in dashboard
- No priority queues
- Results are ephemeral (expire after `keep_result` seconds)
- Requires Redis

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Job queue | ARQ | Already in use, async-native, Redis-backed |
| Cron parsing | Custom `cron_expr_to_arq_kwargs()` | Bridge JSON config → ARQ cron |
| Job granularity | Full pipeline per job | Harvester Framework is cohesive; simpler status |
| Persistent logging | Database `JobExecutionLog` table | Redis results are ephemeral |
| Worker separation | Separate worker from publishing | Different timeout/concurrency profiles |
| Manual trigger API | FastAPI endpoints with scanner allowlist | Validate against known scanners |
| Dashboard | Custom FastAPI endpoints + React | No built-in ARQ dashboard |
| Alternative considered | APScheduler 4.x | Good but in-process only, no distributed workers |

### Architecture
```
JSON Configs (schedule_cron) → cron_expr_to_arq_kwargs() → DawoWorkerSettings
FastAPI /api/jobs/trigger → enqueue_job() → Redis → ARQ Worker → Pipeline → DB Log
```

---
*Research for Epic 7 Stories 7-6, 7-7, 7-8*
