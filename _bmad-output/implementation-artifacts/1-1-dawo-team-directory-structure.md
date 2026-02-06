# Story 1.1: DAWO Team Directory Structure

Status: done

---

## Story

As a **developer**,
I want the DAWO agent team directory structure created with proper organization,
So that all future agents have a consistent location and registration pattern.

---

## Acceptance Criteria

1. **Given** the IMAGO.ECO platform codebase exists
   **When** I create the DAWO team structure
   **Then** the following directories exist:
   - `teams/dawo/scanners/`
   - `teams/dawo/generators/`
   - `teams/dawo/validators/`
   - `teams/dawo/orchestrators/`

2. **And** `teams/dawo/__init__.py` exports the team module

3. **And** `teams/dawo/team_spec.py` exists with empty agent registration list

4. **And** the structure follows Platform Test Team pattern from `teams/platform_test/`

---

## Tasks / Subtasks

- [x] Task 1: Create base directory structure (AC: #1)
  - [x] 1.1 Create `teams/dawo/` directory
  - [x] 1.2 Create `teams/dawo/scanners/` with `__init__.py`
  - [x] 1.3 Create `teams/dawo/generators/` with `__init__.py`
  - [x] 1.4 Create `teams/dawo/validators/` with `__init__.py`
  - [x] 1.5 Create `teams/dawo/orchestrators/` with `__init__.py`

- [x] Task 2: Create team module exports (AC: #2)
  - [x] 2.1 Create `teams/dawo/__init__.py` with proper exports
  - [x] 2.2 Import and expose `AGENTS` from team_spec
  - [x] 2.3 Export capability subdirectories

- [x] Task 3: Create team_spec.py registration file (AC: #3)
  - [x] 3.1 Create `teams/dawo/team_spec.py`
  - [x] 3.2 Define empty `AGENTS` list with RegisteredAgent type hint
  - [x] 3.3 Add docstring explaining registration pattern
  - [x] 3.4 Import RegisteredAgent from core

- [x] Task 4: Validate Platform Test Team pattern compliance (AC: #4)
  - [x] 4.1 Review `teams/platform_test/team_spec.py` structure
  - [x] 4.2 Ensure DAWO structure mirrors registration pattern
  - [x] 4.3 Verify type hints and imports match platform conventions

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Agent-Package-Structure]

The DAWO team structure MUST follow capability-based organization:

```
teams/dawo/
├── __init__.py              # Team module exports
├── team_spec.py             # ALL agent registrations (CRITICAL)
├── scanners/                # Research & discovery agents (scan tier)
│   └── __init__.py
├── generators/              # Content creation agents (generate tier)
│   └── __init__.py
├── validators/              # Compliance & quality agents (generate tier)
│   └── __init__.py
└── orchestrators/           # Team coordinators (strategize tier)
    └── __init__.py
```

### Registration Pattern (MUST FOLLOW)

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py - CORRECT PATTERN
from typing import List
from core.registry import RegisteredAgent

# Empty list - agents will be added in subsequent stories
AGENTS: List[RegisteredAgent] = []
```

**Anti-patterns to avoid:**
- ❌ NEVER use `@register_agent` decorators
- ❌ NEVER self-register agents
- ✅ ALL registrations go through team_spec.py

### __init__.py Pattern

**Source:** [architecture.md#Implementation-Patterns]

```python
# teams/dawo/__init__.py
"""DAWO Agent Team - AI agents for DAWO.ECO content platform."""

from .team_spec import AGENTS

__all__ = ["AGENTS"]
```

```python
# teams/dawo/scanners/__init__.py
"""DAWO Scanner agents - Research and discovery."""
# Agents will be imported here as they are created
```

### Project Structure Notes

**Platform:** IMAGO.ECO (brownfield extension)
**Location:** `teams/dawo/` within existing codebase
**Pattern Reference:** `teams/platform_test/` (if exists)

**Naming Conventions:**
| Element | Convention | Example |
|---------|------------|---------|
| Directories | snake_case | `scanners`, `validators` |
| Python files | snake_case | `team_spec.py` |
| Module exports | UPPER_CASE list | `AGENTS` |

### Technology Stack Context

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Use type hints throughout |
| Agent Framework | Google ADK | Base classes from `core/` |
| Registry | AgentRegistry | From `core/registry/` |

---

## References

- [Source: architecture.md#Agent-Package-Structure] - Complete directory structure
- [Source: architecture.md#Implementation-Patterns] - Registration patterns
- [Source: project-context.md#Agent-Registration] - Registration rules and examples
- [Source: project-context.md#Code-Organization] - Directory conventions
- [Source: epics.md#Story-1.1] - Original story requirements

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Python syntax validation passed for all files
- Directory structure verified with find command

### Completion Notes List

- Created capability-based directory structure: scanners, generators, validators, orchestrators
- Implemented team_spec.py with empty AGENTS list and proper type hints
- Created __init__.py with AGENTS export and subdirectory imports
- All subdirectory __init__.py files include descriptive docstrings explaining LLM tier usage
- RegisteredAgent import includes try/except for graceful fallback during development
- All Python files pass syntax validation

### Change Log

- 2026-02-05: Initial implementation of DAWO team directory structure
- 2026-02-05: Code review completed - 7 issues fixed:
  - H1: Added `__all__` exports to all subdirectory `__init__.py` files
  - H2/H3: Fixed tier terminology (scan/generate/strategize instead of haiku/sonnet/opus)
  - H4: AC #4 verified - Platform Test Team not in standalone repo, pattern from architecture.md followed
  - M1: Initialized git repository
  - M2: Created `.gitignore` excluding `__pycache__/` and common patterns
  - M3: Replaced `Any` fallback with type-safe `RegisteredAgent` dataclass placeholder
- 2026-02-06: Adversarial LOW review - 1 issue fixed:
  - L1: Fixed tier terminology in `teams/dawo/__init__.py` docstring (still used haiku/sonnet/opus)

### File List

- [x] `teams/dawo/__init__.py` - Team module with exports
- [x] `teams/dawo/team_spec.py` - Agent registration with empty AGENTS list
- [x] `teams/dawo/scanners/__init__.py` - Scanner agents module
- [x] `teams/dawo/generators/__init__.py` - Generator agents module
- [x] `teams/dawo/validators/__init__.py` - Validator agents module
- [x] `teams/dawo/orchestrators/__init__.py` - Orchestrator agents module
- [x] `.gitignore` - Git ignore patterns (added during review)
