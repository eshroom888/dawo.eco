# Pre-Submission Code Review Checklist

**Purpose:** Reduce code review fix cycles by catching common issues before submission.
**Target:** 50% reduction in post-review fixes (baseline: 100% fix rate in Epics 4 & 5).

> **Team Agreement (Epic 5 Retro):** Every PR must pass this checklist before requesting review. This is non-negotiable.

---

## Before Submitting for Review

### 1. Exports (CRITICAL - missed in every Epic 5 story)

- [ ] Every `__init__.py` has a complete `__all__` list
- [ ] `__all__` includes ALL public classes, functions, constants, and types
- [ ] Verify by comparing `__all__` against actual module contents
- [ ] No circular imports
- [ ] `TYPE_CHECKING` pattern used for type-only imports:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from some_module import SomeType
  ```

**Quick verification:**
```python
# For each __init__.py, ensure every public symbol is exported:
# 1. List all .py files in the package
# 2. Check each file's public classes/functions
# 3. Verify they appear in __all__
```

### 2. Tests

- [ ] All existing tests pass (`pytest tests/`)
- [ ] New code has corresponding unit tests
- [ ] Tests cover both **success AND failure paths** for external services
- [ ] Mock objects validate `response.success` attribute, not just exceptions
- [ ] Test assertions match current expected counts (e.g., enum sizes, status counts)
- [ ] Integration tests verify end-to-end flows (not just unit behavior)
- [ ] No duplicate activity logging or side effects in test setup

### 3. Type Annotations

- [ ] All function parameters have type hints
- [ ] All return types annotated
- [ ] Protocol classes used for dependency injection interfaces
- [ ] No `Any` types without explicit justification

### 4. Python Best Practices

- [ ] Use `datetime.now(UTC)` NOT `datetime.utcnow()` (deprecated Python 3.12+)
- [ ] Use `from datetime import UTC` for timezone-aware datetimes
- [ ] No hardcoded secrets or credentials
- [ ] Configuration values externalized to config files
- [ ] No N+1 query patterns (use eager loading or batch queries) — **see Section 8**
- [ ] Database filtering done in SQL, not in-memory Python

### 5. Pipeline & Service Patterns

- [ ] `RetryMiddleware` returns `RetryResult` - never raises (see [patterns doc](./retry-middleware-patterns.md))
- [ ] Services catch their own exceptions and return result objects with `.error`
- [ ] Pipelines inspect `result.error` for auth/fatal errors to stop batch processing
- [ ] No direct field mutation on SQLAlchemy models — use update methods
- [ ] Activity logging happens in exactly one place per operation (no double logging)

### 6. Code Quality

- [ ] No `# TODO` items left unaddressed in new code
- [ ] WebSocket/async events actually wired up (not just emitted)
- [ ] Error handling covers expected failure modes
- [ ] Logging added for debugging production issues

### 7. Documentation

- [ ] Docstrings for public APIs
- [ ] Complex logic has inline comments
- [ ] New patterns discovered are documented in story completion notes

### 8. N+1 Query Prevention (added Epic 6 retro — recurring in 6-7, 6-10)

- [ ] List queries do NOT call individual lookups in a loop
- [ ] Related data loaded via `selectinload()` or `joinedload()` in the same query
- [ ] Batch queries used when loading related entities (e.g., `WHERE id IN (...)`)
- [ ] No `for item in items: await repo.get(item.id)` patterns
- [ ] Pagination queries include all needed joins, not lazy-loaded after

**Common N+1 patterns to catch:**
```python
# BAD: N+1 — queries in a loop
for violation in violations:
    evidence = await evidence_repo.get_by_violation(violation.id)  # N queries!

# GOOD: Batch load
violation_ids = [v.id for v in violations]
evidence_map = await evidence_repo.get_by_violation_ids(violation_ids)  # 1 query
```

### 9. Security Review (added Epic 6 retro — CRITICAL SQL injection caught in 6-9)

- [ ] **No `getattr()` on user-supplied field names** for database sorting/filtering
- [ ] Sort fields validated against an explicit allowlist:
  ```python
  # GOOD: Allowlist
  ALLOWED_SORT_FIELDS = {"created_at", "severity", "status"}
  if sort_field not in ALLOWED_SORT_FIELDS:
      raise ValueError(f"Invalid sort field: {sort_field}")
  ```
- [ ] User input in SQL queries uses parameterized queries (SQLAlchemy bindparams)
- [ ] No string formatting/f-strings in SQL query construction
- [ ] File paths from user input are sanitized (no path traversal)
- [ ] API endpoints validate input schemas (Pydantic models)

### 10. Registration Pattern (added Epic 6 retro — confusion in 6-6)

- [ ] Components that use LLM tiers → `RegisteredAgent` (with `tier=` parameter)
- [ ] Components that are pure Python (no LLM) → `RegisteredService`
- [ ] See [RegisteredAgent vs RegisteredService guide](./registered-agent-vs-service.md)

---

## Quick Commands

```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=core --cov-report=term-missing

# Type checking
mypy core/

# Lint with deprecation rules
ruff check --select=B,C,E,F,W,DTZ

# Verify __init__.py exports (manual)
python -c "from your_module import *; print(dir())"
```

---

## Common Issues by Epic (Reference)

### Epic 4 Issues
| Issue | Fix |
|-------|-----|
| Missing `__init__.py` exports | Add to `__all__` list |
| `datetime.utcnow()` | Use `datetime.now(UTC)` |
| Mock didn't check `response.success` | Add attribute validation |
| Status enum count wrong in test | Update expected count |

### Epic 5 Issues
| Issue | Fix |
|-------|-----|
| Missing `__init__.py` exports (again, every story) | Verify `__all__` completeness before PR |
| `datetime.utcnow()` in Story 5-5 | Enforce via ruff DTZ rules |
| Double activity logging (5-5) | Log in exactly one layer |
| Fragile field mutation on models (5-5) | Use update methods, not direct assignment |
| N+1 query pattern (5-5) | Eager load or batch query |
| In-memory date filtering (5-5) | Filter in SQL WHERE clause |
| Pipeline didn't detect auth errors (5-4) | Inspect `result.error` for auth failures |

### Epic 6 Issues
| Issue | Fix |
|-------|-----|
| N+1 queries in report generation (6-7, 6-10) | Batch load related entities, use `selectinload()` |
| SQL injection via `getattr` on sort fields (6-9) | Validate against explicit allowlist |
| `RegisteredService` used for LLM component (6-6) | Use `RegisteredAgent` for any component with LLM tier |
| Missing `__init__.py` exports (6-6) | Verify `__all__` completeness before PR |
| CRITICAL: dedup broken in competitor scanner (6-5) | Test deduplication with real data patterns |
| Missing error handling in PDF generation (6-10) | Handle template rendering + file I/O errors |

---

## Acceptance Criteria Verification

Before marking a story task complete:

1. Read the AC literally - does the code satisfy each point?
2. Run the specific test file for that feature
3. Manually verify behavior if UI component
4. Check that no unrelated tests broke

---

*Created: 2026-02-09*
*Updated: 2026-02-12 with Epic 5 Retrospective findings*
*Updated: 2026-02-19 with Epic 6 Retrospective findings (N+1, security, registration)*
*Baseline: 100% (Epics 4-5) → 80% (Epic 6) — target: <50%*
