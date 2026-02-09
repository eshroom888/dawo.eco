# Story 4.2: Approve, Reject, Edit Actions

Status: done

---

## Story

As an **operator**,
I want to approve, reject, or edit individual content items,
So that I control exactly what gets published.

---

## Acceptance Criteria

1. **Given** I'm viewing a content item
   **When** I click Approve
   **Then** status changes to APPROVED
   **And** item moves to scheduled queue
   **And** suggested publish time is confirmed (or I can modify)

2. **Given** I'm viewing a content item
   **When** I click Reject
   **Then** I must provide a rejection reason (dropdown + optional text)
   **And** status changes to REJECTED
   **And** item is archived with rejection reason
   **And** rejection data feeds back to content generation for learning

3. **Given** I'm viewing a content item
   **When** I click Edit
   **Then** caption becomes editable inline
   **And** I can accept AI rewrite suggestions with one click
   **And** compliance re-validates automatically after edit
   **And** quality score recalculates after edit

4. **Given** I edit content
   **When** I save changes
   **Then** edit history is preserved (audit trail)
   **And** original version remains accessible
   **And** I can revert to original if needed

---

## Tasks / Subtasks

- [x] Task 1: Add action buttons to ApprovalDetailModal (AC: #1, #2, #3)
  - [x] 1.1 Create `ApprovalActions` component with Approve/Reject/Edit buttons
  - [x] 1.2 Add button styling: Approve (green), Reject (red), Edit (blue)
  - [x] 1.3 Add loading states during action processing
  - [x] 1.4 Add success/error toast notifications using shadcn/ui Sonner
  - [x] 1.5 Wire up actions to API calls via hooks
  - [x] 1.6 Add keyboard shortcuts: A (approve), R (reject), E (edit)

- [x] Task 2: Create Approve action API and handler (AC: #1)
  - [x] 2.1 Create `POST /api/approval-queue/{id}/approve` endpoint
  - [x] 2.2 Create `ApproveActionSchema` with optional `scheduled_publish_time` override
  - [x] 2.3 Implement `approve_item()` in ApprovalRepository
  - [x] 2.4 Update ApprovalItem status to APPROVED
  - [x] 2.5 Move item to scheduled queue (set scheduled_publish_time)
  - [x] 2.6 Log approval action with timestamp and operator (audit trail)

- [x] Task 3: Create Reject action with reason system (AC: #2)
  - [x] 3.1 Create `RejectReasonEnum` with predefined options:
        - `COMPLIANCE_ISSUE` - Contains prohibited claims
        - `BRAND_VOICE_MISMATCH` - Doesn't match DAWO tone
        - `LOW_QUALITY` - Quality score too low
        - `IRRELEVANT_CONTENT` - Topic not suitable
        - `DUPLICATE_CONTENT` - Similar post already exists
        - `OTHER` - Custom reason required
  - [x] 3.2 Create `RejectActionSchema` with reason enum + optional text
  - [x] 3.3 Create `POST /api/approval-queue/{id}/reject` endpoint
  - [x] 3.4 Implement `reject_item()` in ApprovalRepository
  - [x] 3.5 Create `RejectReasonModal` component with dropdown + textarea
  - [x] 3.6 Store rejection with reason, timestamp, archived status
  - [x] 3.7 Implement rejection feedback endpoint for ML learning pipeline

- [x] Task 4: Create inline caption editor (AC: #3, #4)
  - [x] 4.1 Create `CaptionEditor` component with textarea + character count
  - [x] 4.2 Create edit mode toggle in ApprovalDetailModal (view/edit states)
  - [x] 4.3 Add rich text formatting toolbar (bold, italic, emoji picker)
  - [x] 4.4 Add hashtag highlighting and autocomplete
  - [x] 4.5 Add word/character count display with limits (180-220 words target)
  - [x] 4.6 Add "Save", "Cancel", "Revert to Original" buttons
  - [x] 4.7 Preserve original caption in state for revert functionality

- [x] Task 5: Implement AI rewrite suggestion acceptance (AC: #3)
  - [x] 5.1 Create `RewriteSuggestion` component displaying suggestion cards
  - [x] 5.2 Add "Accept" button per suggestion to apply rewrite inline
  - [x] 5.3 Add "Accept All" button to apply all suggestions at once
  - [x] 5.4 Highlight applied changes with diff view (strikethrough old, green new)
  - [x] 5.5 Create `PUT /api/approval-queue/{id}/apply-rewrite` endpoint
  - [x] 5.6 Track which suggestions were accepted (for ML feedback)

- [x] Task 6: Auto-revalidation after edits (AC: #3)
  - [x] 6.1 Create `POST /api/approval-queue/{id}/revalidate` endpoint
  - [x] 6.2 Call EU Compliance Checker on edited caption
  - [x] 6.3 Call Brand Voice Validator on edited caption
  - [x] 6.4 Recalculate quality score using ContentQualityScorer
  - [x] 6.5 Update item with new compliance_status, quality_score
  - [x] 6.6 Auto-trigger revalidation on caption save
  - [x] 6.7 Display validation progress indicator during revalidation
  - [x] 6.8 Update UI badges in real-time after revalidation completes

- [x] Task 7: Edit history and audit trail (AC: #4)
  - [x] 7.1 Create `ApprovalItemEdit` SQLAlchemy model for edit history
  - [x] 7.2 Create migration for `approval_item_edits` table
  - [x] 7.3 Store each edit: item_id, previous_caption, new_caption, timestamp, editor
  - [x] 7.4 Create `GET /api/approval-queue/{id}/history` endpoint
  - [x] 7.5 Create `EditHistoryAccordion` component showing version timeline
  - [x] 7.6 Add "View History" button in edit mode
  - [x] 7.7 Implement "Revert to Version X" functionality

- [x] Task 8: Publish time modification (AC: #1)
  - [x] 8.1 Create `ScheduleTimeSelector` component with datetime picker
  - [x] 8.2 Use shadcn/ui Calendar + time input for datetime selection
  - [x] 8.3 Show suggested optimal time with "Use Suggested" quick action
  - [x] 8.4 Validate time is in the future
  - [x] 8.5 Display conflict warning if another post scheduled same hour
  - [x] 8.6 Include timezone indicator (CET for DAWO/Norway)

- [x] Task 9: Create useApprovalActions hook (AC: all)
  - [x] 9.1 Create `useApprovalActions` hook with approve/reject/edit mutations
  - [x] 9.2 Handle optimistic updates for smooth UX
  - [x] 9.3 Implement error recovery and rollback
  - [x] 9.4 Auto-refresh queue after successful action
  - [x] 9.5 Add loading state management per action type

- [x] Task 10: Create unit tests for frontend components
  - [x] 10.1 Test ApprovalActions button rendering and click handlers
  - [x] 10.2 Test RejectReasonModal dropdown selection and validation
  - [x] 10.3 Test CaptionEditor edit/save/revert functionality
  - [x] 10.4 Test RewriteSuggestion accept/reject behavior
  - [x] 10.5 Test EditHistoryAccordion version display
  - [x] 10.6 Test keyboard shortcuts (A/R/E)

- [x] Task 11: Create backend integration tests
  - [x] 11.1 Test approve endpoint updates status correctly
  - [x] 11.2 Test reject endpoint requires reason
  - [x] 11.3 Test edit endpoint triggers revalidation
  - [x] 11.4 Test edit history is preserved
  - [x] 11.5 Test revert restores original caption
  - [x] 11.6 Test concurrent edit conflict handling

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Frontend-Architecture], [project-context.md#Technology-Stack]

This story adds action functionality to the approval queue from Story 4-1. It builds directly on existing ApprovalItem model, ApprovalDetailModal, and API infrastructure.

**Key Pattern:** Extends existing approval system with mutation endpoints and edit capabilities.

### Technology Stack (MUST USE)

**Source:** [project-context.md#Technology-Stack], [4-1-content-approval-queue-ui.md]

```
Frontend:
- React 18 with TypeScript
- shadcn/ui components (Button, Dialog, Select, Textarea, Calendar, Sonner)
- SWR mutations for API calls
- React Hook Form for edit validation

Backend:
- FastAPI with async handlers
- SQLAlchemy async ORM
- Pydantic schemas for validation
```

### shadcn/ui Components to Use

**Source:** Story 4-1 patterns + new components needed

```tsx
// Existing from 4-1
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

// New components needed for 4-2
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Sonner } from "@/components/ui/sonner";  // Toast notifications
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
```

### API Schema Design

**Source:** FastAPI patterns in IMAGO.ECO, [4-1-content-approval-queue-ui.md#API-Schema-Design]

```python
# ui/backend/schemas/approval_actions.py

from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class RejectReason(str, Enum):
    """Predefined rejection reasons for analytics and ML feedback."""
    COMPLIANCE_ISSUE = "compliance_issue"
    BRAND_VOICE_MISMATCH = "brand_voice_mismatch"
    LOW_QUALITY = "low_quality"
    IRRELEVANT_CONTENT = "irrelevant_content"
    DUPLICATE_CONTENT = "duplicate_content"
    OTHER = "other"

class ApproveActionSchema(BaseModel):
    """Schema for approve action."""
    scheduled_publish_time: Optional[datetime] = None  # Override suggested time

class RejectActionSchema(BaseModel):
    """Schema for reject action."""
    reason: RejectReason
    reason_text: Optional[str] = Field(None, max_length=500)  # Required if OTHER

class EditActionSchema(BaseModel):
    """Schema for edit action."""
    caption: str = Field(..., min_length=1, max_length=2200)
    hashtags: Optional[list[str]] = None

class RevalidationResultSchema(BaseModel):
    """Result of compliance/quality revalidation."""
    compliance_status: str
    compliance_details: Optional[list[dict]] = None
    quality_score: float
    quality_breakdown: Optional[dict] = None
    rewrite_suggestions: Optional[list[dict]] = None

class ApprovalActionResponse(BaseModel):
    """Standard response for approval actions."""
    success: bool
    message: str
    item_id: str
    new_status: str
    revalidation: Optional[RevalidationResultSchema] = None

class EditHistorySchema(BaseModel):
    """Schema for edit history entry."""
    id: str
    previous_caption: str
    new_caption: str
    edited_at: datetime
    editor: str  # "operator" or system identifier
```

### React Component Structure

**Source:** IMAGO.ECO frontend patterns, extends Story 4-1 structure

```
ui/frontend-react/src/
├── components/
│   └── approval/
│       ├── ApprovalActions.tsx         # Action buttons (Approve/Reject/Edit)
│       ├── RejectReasonModal.tsx       # Rejection reason dialog
│       ├── CaptionEditor.tsx           # Inline caption editor
│       ├── RewriteSuggestion.tsx       # AI suggestion cards
│       ├── RewriteSuggestionsPanel.tsx # Container for suggestions
│       ├── EditHistoryAccordion.tsx    # Version history display
│       ├── ScheduleTimeSelector.tsx    # Datetime picker for publish time
│       └── ApprovalDetailModal.tsx     # (MODIFY) Add edit mode + actions
├── hooks/
│   ├── useApprovalQueue.ts             # (EXISTS) Query hook
│   └── useApprovalActions.ts           # (NEW) Mutation hooks
└── types/
    └── approval.ts                      # (EXTEND) Add action types
```

### Backend Repository Methods

**Source:** [4-1-content-approval-queue-ui.md#File-Structure]

```python
# ui/backend/repositories/approval_repository.py (EXTEND)

class ApprovalRepository:
    # Existing methods from 4-1...

    async def approve_item(
        self,
        item_id: str,
        scheduled_publish_time: Optional[datetime] = None,
        operator_id: str = "operator",
    ) -> ApprovalItem:
        """Approve item and move to scheduled queue."""
        # Update status to APPROVED
        # Set scheduled_publish_time (use suggested if not overridden)
        # Log audit trail
        ...

    async def reject_item(
        self,
        item_id: str,
        reason: RejectReason,
        reason_text: Optional[str],
        operator_id: str = "operator",
    ) -> ApprovalItem:
        """Reject item with reason for ML feedback."""
        # Update status to REJECTED
        # Store rejection_reason, rejection_text
        # Set archived_at timestamp
        # Log audit trail
        ...

    async def update_caption(
        self,
        item_id: str,
        new_caption: str,
        operator_id: str = "operator",
    ) -> ApprovalItem:
        """Update caption and preserve edit history."""
        # Store previous caption in edit history
        # Update caption field
        # Return item for revalidation
        ...

    async def get_edit_history(
        self,
        item_id: str,
    ) -> list[ApprovalItemEdit]:
        """Get all edits for an item."""
        ...

    async def revert_to_version(
        self,
        item_id: str,
        version_id: str,
    ) -> ApprovalItem:
        """Revert caption to a previous version."""
        ...
```

### Revalidation Integration (CRITICAL)

**Source:** [project-context.md#EU-Compliance], [epics.md#Story-3.6]

```python
# After caption edit, revalidation calls these in sequence:

# 1. EU Compliance Check (from teams/dawo/validators/)
compliance_result = await eu_compliance_checker.check(new_caption)
# Returns: status (COMPLIANT/WARNING/REJECTED), flagged_phrases, suggestions

# 2. Brand Voice Check (from teams/dawo/validators/)
brand_result = await brand_voice_validator.validate(new_caption)
# Returns: status (PASS/NEEDS_REVISION/FAIL), issues, suggestions

# 3. Quality Score Recalculation (from core components)
quality_result = await content_quality_scorer.score(
    caption=new_caption,
    compliance_status=compliance_result.status,
    brand_voice_status=brand_result.status,
    # Other factors unchanged
)
# Returns: overall_score, breakdown by factor

# IMPORTANT: Use capability-based lookup via AgentRegistry
compliance_checker = await registry.get_by_capability("eu_compliance")
brand_validator = await registry.get_by_capability("brand_voice")
```

### Edit History Database Model

**Source:** New model for audit trail

```python
# core/approval/models.py (EXTEND)

class ApprovalItemEdit(Base):
    """Audit trail for caption edits."""
    __tablename__ = "approval_item_edits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("approval_items.id", ondelete="CASCADE"),
        index=True,
    )
    previous_caption: Mapped[str] = mapped_column(Text)
    new_caption: Mapped[str] = mapped_column(Text)
    edited_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    editor: Mapped[str] = mapped_column(String(100), default="operator")

    # Relationship
    item: Mapped["ApprovalItem"] = relationship(back_populates="edits")
```

### Keyboard Shortcuts Implementation

**Source:** Accessibility best practices, Story 4-1 keyboard nav pattern

```typescript
// In ApprovalDetailModal or ApprovalActions component

useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Only when modal is open and not in edit mode
    if (!isOpen || isEditing) return;

    switch (e.key.toLowerCase()) {
      case 'a':
        if (!e.ctrlKey && !e.metaKey) handleApprove();
        break;
      case 'r':
        if (!e.ctrlKey && !e.metaKey) handleReject();
        break;
      case 'e':
        if (!e.ctrlKey && !e.metaKey) handleEdit();
        break;
    }
  };

  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, [isOpen, isEditing]);
```

### Toast Notifications Pattern

**Source:** UX best practices with shadcn/ui Sonner

```typescript
import { toast } from "sonner";

// Success toasts
toast.success("Content approved", {
  description: `Scheduled for ${formatDateTime(publishTime)}`,
});

// Error toasts
toast.error("Approval failed", {
  description: error.message,
  action: {
    label: "Retry",
    onClick: () => handleApprove(),
  },
});

// Loading toast for revalidation
const toastId = toast.loading("Revalidating content...");
// ... after completion
toast.success("Validation complete", { id: toastId });
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [4-1-content-approval-queue-ui.md#Previous-Story-Learnings]

| Learning | How to Apply in 4-2 |
|----------|---------------------|
| Complete `__all__` exports | Export all new components in index.ts |
| TypeScript strict mode | No `any` types in action schemas |
| Loading skeletons | Show loading states during actions |
| Error boundaries | Wrap action handlers with try/catch |
| Mobile responsive | Action buttons stack on mobile |
| Accessibility | aria-labels on all buttons, keyboard shortcuts |
| SWR mutations | Use mutate() for optimistic updates |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER hardcode validation logic** - Use EU Compliance Checker and Brand Voice Validator via registry
2. **NEVER skip audit logging** - Every action must be logged
3. **NEVER allow empty rejection** - Require reason for all rejections
4. **NEVER edit without history** - Preserve all versions
5. **NEVER skip revalidation** - Always revalidate after caption changes
6. **NEVER block UI during validation** - Use async with progress indicator

### LLM Tier Assignment

**Source:** [project-context.md#LLM-Tier-Assignment]

```
Revalidation calls validators that use LLM:
- EU Compliance Checker: tier="generate" (Sonnet)
- Brand Voice Validator: tier="generate" (Sonnet)

FORBIDDEN in code/docstrings/comments:
- "haiku", "sonnet", "opus"
- "claude-haiku", "claude-sonnet", "claude-opus"
```

### File Structure (MUST FOLLOW)

**Source:** IMAGO.ECO frontend conventions, extends 4-1 structure

```
ui/frontend-react/src/
├── components/
│   └── approval/
│       ├── index.ts                     # (EXTEND) Add new exports
│       ├── ApprovalActions.tsx          # (NEW)
│       ├── RejectReasonModal.tsx        # (NEW)
│       ├── CaptionEditor.tsx            # (NEW)
│       ├── RewriteSuggestion.tsx        # (NEW)
│       ├── RewriteSuggestionsPanel.tsx  # (NEW)
│       ├── EditHistoryAccordion.tsx     # (NEW)
│       ├── ScheduleTimeSelector.tsx     # (NEW)
│       └── ApprovalDetailModal.tsx      # (MODIFY) Add edit mode
├── hooks/
│   └── useApprovalActions.ts            # (NEW)
├── types/
│   └── approval.ts                      # (EXTEND)
└── __tests__/
    └── approval/
        ├── ApprovalActions.test.tsx     # (NEW)
        ├── RejectReasonModal.test.tsx   # (NEW)
        ├── CaptionEditor.test.tsx       # (NEW)
        └── useApprovalActions.test.tsx  # (NEW)

ui/backend/
├── routers/
│   └── approval_queue.py                # (EXTEND) Add action endpoints
├── schemas/
│   └── approval_actions.py              # (NEW)
└── repositories/
    └── approval_repository.py           # (EXTEND) Add action methods

core/approval/
├── models.py                            # (EXTEND) Add ApprovalItemEdit
└── __init__.py                          # (EXTEND) Export new model

migrations/versions/
└── 2026_02_XX_XXX_add_approval_edits_table.py  # (NEW)

tests/
├── ui/backend/
│   └── test_approval_actions.py         # (NEW)
└── core/approval/
    └── test_edit_history.py             # (NEW)
```

### Edge Cases to Handle

1. **Concurrent edits**: Return 409 Conflict if item was modified since fetch
2. **Reject with OTHER but no text**: Validate reason_text is required
3. **Approve rejected item**: Should not be allowed (enforce state machine)
4. **Edit approved item**: Should revert to PENDING status
5. **Revalidation timeout**: Handle gracefully, allow manual retry
6. **Empty caption after edit**: Validate minimum content
7. **Hashtag limit exceeded**: Warn if >30 hashtags (Instagram limit)
8. **Schedule time in past**: Reject with clear error message
9. **Revert on item with no history**: Show "No previous versions" message
10. **Network failure during action**: Optimistic update rollback

### State Machine for ApprovalStatus

```
PENDING ──┬──> APPROVED ──> SCHEDULED ──> PUBLISHED
          │                              │
          ├──> REJECTED ──> (archived)   ├──> PUBLISH_FAILED
          │                              │
          └──────────────────────────────┘
                  (edit reverts to PENDING)
```

### Project Structure Notes

- **Location**: Extends `ui/frontend-react/src/components/approval/`, `ui/backend/routers/`
- **Dependencies**: Story 4-1 components, EU Compliance Checker, Brand Voice Validator
- **Used by**: IMAGO dashboard operator workflow
- **Performance target**: Actions complete in < 2 seconds, revalidation < 10 seconds
- **Audit requirements**: All actions logged with timestamp and operator

### References

- [Source: epics.md#Story-4.2] - Original story requirements (FR36)
- [Source: 4-1-content-approval-queue-ui.md] - Previous story components and patterns
- [Source: project-context.md#Technology-Stack] - Tech stack
- [Source: project-context.md#EU-Compliance] - Compliance requirements
- [Source: project-context.md#Approval-Workflow] - Approval flow
- [Source: architecture.md#Data-Flow] - System architecture
- [Source: 3-6-content-compliance-rewrite-suggestions.md] - Rewrite suggestion patterns
- [Source: core/approval/] - ApprovalManager integration

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (code review fix pass)

### Debug Log References

- Code review performed 2026-02-08: Found story file out of sync, missing EditHistoryAccordion, revalidation not wired

### Completion Notes List

1. All core action endpoints implemented (approve, reject, edit, revalidate, apply-rewrite, history)
2. Frontend components created: ApprovalActions, RejectReasonModal, CaptionEditor, RewriteSuggestion, RewriteSuggestionsPanel, ScheduleTimeSelector, EditHistoryAccordion
3. useApprovalActions hook with full CRUD operations and error handling
4. Database models and migrations for ApprovalItemEdit audit trail
5. Comprehensive frontend test coverage for all components
6. Backend integration tests for all action endpoints
7. Revalidation wired to EU Compliance Checker and Brand Voice Validator via capability lookup
8. Rich text toolbar added to CaptionEditor (bold, italic, emoji picker)
9. Hashtag autocomplete implemented

### File List

**Frontend Components (NEW):**
- ui/frontend-react/src/components/approval/ApprovalActions.tsx
- ui/frontend-react/src/components/approval/RejectReasonModal.tsx
- ui/frontend-react/src/components/approval/CaptionEditor.tsx
- ui/frontend-react/src/components/approval/RewriteSuggestion.tsx
- ui/frontend-react/src/components/approval/RewriteSuggestionsPanel.tsx
- ui/frontend-react/src/components/approval/ScheduleTimeSelector.tsx
- ui/frontend-react/src/components/approval/EditHistoryAccordion.tsx

**Frontend Hooks (NEW):**
- ui/frontend-react/src/hooks/useApprovalActions.ts

**Frontend Types (MODIFIED):**
- ui/frontend-react/src/types/approval.ts

**Frontend Tests (NEW):**
- ui/frontend-react/src/components/approval/__tests__/ApprovalActions.test.tsx
- ui/frontend-react/src/components/approval/__tests__/RejectReasonModal.test.tsx
- ui/frontend-react/src/components/approval/__tests__/CaptionEditor.test.tsx
- ui/frontend-react/src/components/approval/__tests__/RewriteSuggestionsPanel.test.tsx
- ui/frontend-react/src/components/approval/__tests__/ScheduleTimeSelector.test.tsx
- ui/frontend-react/src/components/approval/__tests__/EditHistoryAccordion.test.tsx

**Frontend Exports (MODIFIED):**
- ui/frontend-react/src/components/approval/index.ts

**Backend Routers (MODIFIED):**
- ui/backend/routers/approval_queue.py

**Backend Schemas (NEW):**
- ui/backend/schemas/approval_actions.py

**Backend Repository (MODIFIED):**
- ui/backend/repositories/approval_repository.py

**Core Models (MODIFIED):**
- core/approval/models.py

**Migrations (NEW):**
- migrations/versions/2026_02_08_002_add_approval_actions.py

**Backend Tests (NEW):**
- tests/ui/backend/test_approval_actions.py
- tests/core/approval/test_edit_history.py

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-08 | Story created by Scrum Master | Bob (SM Agent) |
| 2026-02-08 | Implementation completed - all tasks done | Dev Agent |
| 2026-02-08 | Code review fixes applied - EditHistoryAccordion, revalidation wiring, rich text toolbar, backend tests | Amelia (Code Review) |
