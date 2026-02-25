# RetryMiddleware Patterns & Auth Error Detection

**Purpose:** Document the "never raises" pattern used by RetryMiddleware and how pipelines must detect auth errors from service results.
**Background:** Story 5-4 (Gmail API Integration) uncovered a subtle pattern where the pipeline must inspect `result.error` for auth failures because services catch exceptions internally.

---

## Core Principle: RetryMiddleware Never Raises

The `RetryMiddleware` in `teams/dawo/middleware/retry.py` **never raises exceptions**. It always returns a `RetryResult` object:

```python
@dataclass
class RetryResult:
    success: bool
    response: Optional[Any] = None
    attempts: int = 0
    last_error: Optional[str] = None
    is_incomplete: bool = False        # True = exhausted retries (graceful degradation)
    operation_id: Optional[str] = None
```

### Return Cases

| Scenario | `success` | `is_incomplete` | `last_error` |
|----------|-----------|-----------------|--------------|
| Operation succeeded | `True` | `False` | `None` |
| Non-retryable error (4xx except 429) | `False` | `False` | Error message |
| All retries exhausted | `False` | **`True`** | Last error message |

### Key Implication

**Callers must check the result, not catch exceptions:**

```python
# CORRECT - check result fields
result = await retry_middleware.execute_with_retry(operation, "context")
if not result.success:
    if result.is_incomplete:
        # Graceful degradation - retries exhausted
        log.warning(f"Operation incomplete after {result.attempts} attempts")
    else:
        # Definite failure - non-retryable
        log.error(f"Operation failed: {result.last_error}")

# WRONG - RetryMiddleware never raises
try:
    result = await retry_middleware.execute_with_retry(operation, "context")
except SomeError:  # This will never fire
    ...
```

---

## Service Pattern: Catch Exceptions, Return Results

Services that use external APIs follow this pattern:

1. **Service catches its own exceptions** (e.g., `GmailAuthError`, `GmailSendError`)
2. **Service returns a result object** with `success=False` and `error=<message>`
3. **Service never re-raises** to the pipeline

### Example: GmailSendService

From `teams/dawo/leads/gmail/service.py`:

```python
async def send_outreach(self, lead: Lead, outreach: OutreachDraft) -> GmailSendResult:
    # ... prepare message ...

    try:
        result = await self._client.send_message(message)
    except GmailAuthError as e:
        logger.error(f"Gmail auth error sending to {lead.email}: {e}")
        await self._handle_auth_failure(e)
        return GmailSendResult(success=False, error=f"Auth error: {e}")
    except GmailSendError as e:
        logger.error(f"Gmail send error to {lead.email}: {e}")
        await self._handle_send_failure(lead, e)
        return GmailSendResult(success=False, error=str(e))
```

**Note:** The `GmailAuthError` is caught and wrapped into a result with `error="Auth error: ..."`. The pipeline never sees the exception.

---

## Pipeline Pattern: Inspect result.error for Auth Errors

Pipelines that process batches must detect fatal errors (like auth failures) to stop processing the entire batch. Since services return results rather than raising, **the pipeline must inspect the error string**.

### Example: GmailSendPipeline

From `teams/dawo/leads/gmail/pipeline.py`:

```python
for lead in leads_to_send:
    send_result = await self._send_service.send_outreach(lead, outreach)

    if send_result.success:
        result.sent += 1
    elif send_result.error and "Auth error" in send_result.error:
        # Auth failure stops the ENTIRE pipeline
        logger.error(f"Auth failure stops pipeline: {send_result.error}")
        result.is_complete = False
        result.error = f"Auth failure: {send_result.error}"
        result.failed += 1
        break  # <-- Stop processing remaining leads
    else:
        # Non-auth failure - continue with next lead
        result.failed += 1
```

### Why This Matters

Without auth error detection, the pipeline would:
1. Try to send email #1 → auth fails → logged as single failure
2. Try to send email #2 → auth fails → logged as single failure
3. Try to send email #3 → auth fails → logged as single failure
4. ... continue failing for ALL leads in the batch

With auth error detection, the pipeline:
1. Try to send email #1 → auth fails → **stops entire batch immediately**
2. Reports `is_complete=False` with auth failure reason

---

## The Three-Layer Pattern

```
┌─────────────────────────────────┐
│  Pipeline (batch orchestrator)  │
│  - Inspects result.error        │
│  - Detects auth → stops batch   │
│  - Non-auth → continues         │
├─────────────────────────────────┤
│  Service (single operation)     │
│  - Catches exceptions           │
│  - Returns Result(error=...)    │
│  - Never re-raises              │
├─────────────────────────────────┤
│  RetryMiddleware                │
│  - Handles transient failures   │
│  - Returns RetryResult          │
│  - Never raises                 │
├─────────────────────────────────┤
│  External API Client            │
│  - May raise auth errors        │
│  - May raise transient errors   │
│  - May return error responses   │
└─────────────────────────────────┘
```

---

## Checklist for New Pipelines

When building a new pipeline that processes batches:

- [ ] Service catches all expected exceptions and returns result objects
- [ ] Result objects have `success: bool` and `error: Optional[str]` fields
- [ ] Auth errors include identifiable prefix (e.g., `"Auth error: "`)
- [ ] Pipeline inspects `result.error` for auth/fatal errors
- [ ] Auth errors trigger `break` to stop batch processing
- [ ] Pipeline sets `is_complete=False` when stopping early
- [ ] Non-auth errors allow the loop to continue
- [ ] Tests cover: success, non-auth failure (continues), and auth failure (stops batch)

---

## Reference Files

| Component | File |
|-----------|------|
| RetryMiddleware | `teams/dawo/middleware/retry.py` |
| RetryResult dataclass | `teams/dawo/middleware/retry.py:95-116` |
| GmailAuthError | `teams/dawo/leads/gmail/credentials_manager.py:25-28` |
| GmailSendService | `teams/dawo/leads/gmail/service.py:83-147` |
| GmailSendPipeline | `teams/dawo/leads/gmail/pipeline.py:84-162` |
| Mock verification patterns | `docs/mock-verification-patterns.md` |

---

*Created: 2026-02-12*
*Based on: Epic 5 Story 5-4 (Gmail API Integration) discoveries*
*Action Item #3 from Epic 5 Retrospective*
