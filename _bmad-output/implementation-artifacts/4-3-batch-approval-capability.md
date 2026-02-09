# Story 4.3: Batch Approval Capability

Status: done

---

## Story

As an **operator**,
I want to approve multiple content items at once,
So that daily review takes under 5 minutes.

---

## Acceptance Criteria

1. **Given** multiple items are in approval queue
   **When** I select items using checkboxes
   **Then** a batch action bar appears with: Approve All, Reject All

2. **Given** I've selected multiple items
   **When** I click Approve All
   **Then** all selected items are approved
   **And** each uses its suggested publish time
   **And** confirmation shows: "X items approved, scheduled for [dates]"

3. **Given** I want to quickly approve high-quality items
   **When** I use "Approve All WOULD_AUTO_PUBLISH" filter
   **Then** only items tagged WOULD_AUTO_PUBLISH are selected
   **And** I can approve them with one click

4. **Given** batch approval completes
   **When** I return to queue
   **Then** approved items are removed from pending view
   **And** remaining items are re-sorted by priority

---

## Tasks / Subtasks

- [x] Task 1: Add selection checkboxes to queue items (AC: #1)
  - [x] 1.1 Add Checkbox component from shadcn/ui to `ApprovalQueueItem`
  - [x] 1.2 Create `useQueueSelection` hook to manage selected item IDs
  - [x] 1.3 Add "Select All" checkbox in queue header
  - [x] 1.4 Add visual highlight for selected items (border/background change)
  - [x] 1.5 Persist selection across pagination (if applicable)
  - [x] 1.6 Clear selection when leaving page or after batch action

- [x] Task 2: Create batch action bar component (AC: #1)
  - [x] 2.1 Create `BatchActionBar` component that appears when items selected
  - [x] 2.2 Add sticky positioning at bottom of queue viewport
  - [x] 2.3 Display selected count: "X items selected"
  - [x] 2.4 Add "Approve All" button (green)
  - [x] 2.5 Add "Reject All" button (red)
  - [x] 2.6 Add "Clear Selection" button
  - [x] 2.7 Add animation for bar appearance/disappearance
  - [x] 2.8 Add keyboard shortcut: Shift+A (batch approve), Shift+R (batch reject)

- [x] Task 3: Create batch approve API endpoint (AC: #2)
  - [x] 3.1 Create `POST /api/approval-queue/batch/approve` endpoint
  - [x] 3.2 Create `BatchApproveSchema` with `item_ids: list[str]`
  - [x] 3.3 Create `BatchApproveResponse` with summary of approved items
  - [x] 3.4 Implement `batch_approve_items()` in ApprovalRepository
  - [x] 3.5 Update all selected items to APPROVED status atomically
  - [x] 3.6 Use each item's suggested_publish_time for scheduling
  - [x] 3.7 Log all approvals in audit trail with batch_id reference
  - [x] 3.8 Handle partial failures gracefully (report which items failed)

- [x] Task 4: Create batch reject API endpoint (AC: #1)
  - [x] 4.1 Create `POST /api/approval-queue/batch/reject` endpoint
  - [x] 4.2 Create `BatchRejectSchema` with `item_ids: list[str]`, `reason: RejectReason`, `reason_text: Optional[str]`
  - [x] 4.3 Create `BatchRejectResponse` with summary of rejected items
  - [x] 4.4 Implement `batch_reject_items()` in ApprovalRepository
  - [x] 4.5 Apply same rejection reason to all selected items
  - [x] 4.6 Store rejection data for ML feedback pipeline
  - [x] 4.7 Log all rejections in audit trail with batch_id reference

- [x] Task 5: Implement WOULD_AUTO_PUBLISH quick filter (AC: #3)
  - [x] 5.1 Create `QuickFilters` component above queue list
  - [x] 5.2 Add "Select All WOULD_AUTO_PUBLISH" button/filter
  - [x] 5.3 Implement filter to select only would_auto_publish=true items
  - [x] 5.4 Update selected count display when filter applied
  - [x] 5.5 Add "Approve All High-Quality" one-click action combining filter + approve
  - [x] 5.6 Track usage of WOULD_AUTO_PUBLISH approvals for trust metrics

- [x] Task 6: Create batch confirmation dialogs (AC: #2)
  - [x] 6.1 Create `BatchApproveConfirmDialog` showing summary before action
  - [x] 6.2 Display: item count, date range of scheduled posts
  - [x] 6.3 Show preview of first 3 items with thumbnails
  - [x] 6.4 Create `BatchRejectConfirmDialog` requiring reason selection
  - [x] 6.5 Use RejectReason enum from Story 4-2
  - [x] 6.6 Add "Don't show again" checkbox for power users

- [x] Task 7: Implement success/error feedback (AC: #2, #4)
  - [x] 7.1 Create batch success toast: "X items approved, scheduled for [date range]"
  - [x] 7.2 Create batch error toast with retry option for failed items
  - [x] 7.3 Implement optimistic UI update (remove items immediately)
  - [x] 7.4 Add rollback on failure (restore items to queue)
  - [x] 7.5 Auto-refresh queue after successful batch action
  - [x] 7.6 Re-sort remaining items by priority

- [x] Task 8: Create useBatchApproval hook (AC: all)
  - [x] 8.1 Create `useBatchApproval` hook with batchApprove/batchReject mutations
  - [x] 8.2 Integrate with useQueueSelection for selected items
  - [x] 8.3 Handle loading states for batch operations
  - [x] 8.4 Implement error handling with partial success reporting
  - [x] 8.5 Add progress indicator for large batches (10+ items)

- [x] Task 9: Update queue display after batch actions (AC: #4)
  - [x] 9.1 Remove approved/rejected items from queue state
  - [x] 9.2 Re-sort remaining items by source_priority
  - [x] 9.3 Update pagination cursor if needed
  - [x] 9.4 Clear selection state
  - [x] 9.5 Show empty state if all items processed

- [x] Task 10: Create unit tests for frontend components
  - [x] 10.1 Test checkbox selection/deselection
  - [x] 10.2 Test BatchActionBar visibility on selection
  - [x] 10.3 Test "Select All" functionality
  - [x] 10.4 Test WOULD_AUTO_PUBLISH filter selection
  - [x] 10.5 Test confirmation dialogs display correct counts
  - [x] 10.6 Test keyboard shortcuts (Shift+A, Shift+R)
  - [x] 10.7 Test optimistic updates and rollback

- [x] Task 11: Create backend integration tests
  - [x] 11.1 Test batch approve endpoint with 5 items
  - [x] 11.2 Test batch reject endpoint with reason
  - [x] 11.3 Test partial failure handling (some items already approved)
  - [x] 11.4 Test audit trail records batch_id for all items
  - [x] 11.5 Test items removed from queue after batch action
  - [x] 11.6 Test concurrent batch operations conflict handling

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Frontend-Architecture], [project-context.md#Technology-Stack]

This story adds batch approval functionality to the approval queue from Stories 4-1 and 4-2. It builds directly on existing components: ApprovalQueue page, ApprovalQueueItem, useApprovalQueue hook, and action endpoints.

**Key Pattern:** Extends existing approval system with batch mutation endpoints and selection state management.

### Technology Stack (MUST USE)

**Source:** [project-context.md#Technology-Stack], [4-1-content-approval-queue-ui.md], [4-2-approve-reject-edit-actions.md]

```
Frontend:
- React 18 with TypeScript
- shadcn/ui components (Checkbox, Button, Dialog, Sonner)
- SWR mutations for batch API calls
- Custom hooks for selection state management

Backend:
- FastAPI with async handlers
- SQLAlchemy async ORM with bulk operations
- Pydantic schemas for batch validation
```

### shadcn/ui Components to Use

**Source:** Story 4-1 and 4-2 patterns + new components needed

```tsx
// Existing from 4-1 and 4-2
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Sonner } from "@/components/ui/sonner";  // Toast notifications
import { Card } from "@/components/ui/card";

// New components needed for 4-3
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";  // For batch progress
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
```

### API Schema Design

**Source:** FastAPI patterns in IMAGO.ECO, extends 4-2 patterns

```python
# ui/backend/schemas/batch_approval.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .approval_actions import RejectReason

class BatchApproveSchema(BaseModel):
    """Schema for batch approve action."""
    item_ids: list[str] = Field(..., min_length=1, max_length=100)
    # All items use their suggested_publish_time

class BatchRejectSchema(BaseModel):
    """Schema for batch reject action."""
    item_ids: list[str] = Field(..., min_length=1, max_length=100)
    reason: RejectReason
    reason_text: Optional[str] = Field(None, max_length=500)

class BatchActionResultItem(BaseModel):
    """Result for individual item in batch."""
    item_id: str
    success: bool
    error: Optional[str] = None
    scheduled_publish_time: Optional[datetime] = None  # For approved items

class BatchApproveResponse(BaseModel):
    """Response for batch approve action."""
    batch_id: str
    total_requested: int
    successful_count: int
    failed_count: int
    results: list[BatchActionResultItem]
    summary: str  # "5 items approved, scheduled for Feb 8-10"

class BatchRejectResponse(BaseModel):
    """Response for batch reject action."""
    batch_id: str
    total_requested: int
    successful_count: int
    failed_count: int
    results: list[BatchActionResultItem]
    summary: str  # "5 items rejected: Brand voice mismatch"
```

### React Component Structure

**Source:** IMAGO.ECO frontend patterns, extends Stories 4-1 and 4-2

```
ui/frontend-react/src/
├── components/
│   └── approval/
│       ├── BatchActionBar.tsx          # (NEW) Sticky action bar
│       ├── QuickFilters.tsx            # (NEW) WOULD_AUTO_PUBLISH filter
│       ├── BatchApproveConfirmDialog.tsx  # (NEW) Confirm before approve
│       ├── BatchRejectConfirmDialog.tsx   # (NEW) Confirm with reason
│       ├── SelectableQueueItem.tsx     # (NEW) or modify ApprovalQueueItem
│       ├── ApprovalQueue.tsx           # (MODIFY) Add selection state
│       ├── ApprovalQueueItem.tsx       # (MODIFY) Add checkbox
│       └── index.ts                    # (EXTEND) Add new exports
├── hooks/
│   ├── useQueueSelection.ts            # (NEW) Selection state
│   └── useBatchApproval.ts             # (NEW) Batch mutations
└── types/
    └── approval.ts                      # (EXTEND) Add batch types
```

### Selection State Hook Design

**Source:** React patterns for multi-select UIs

```typescript
// hooks/useQueueSelection.ts

import { useState, useCallback } from "react";

interface UseQueueSelectionReturn {
  selectedIds: Set<string>;
  isSelected: (id: string) => boolean;
  toggleSelection: (id: string) => void;
  selectAll: (ids: string[]) => void;
  selectByFilter: (predicate: (item: ApprovalQueueItem) => boolean) => void;
  clearSelection: () => void;
  selectedCount: number;
}

export function useQueueSelection(items: ApprovalQueueItem[]): UseQueueSelectionReturn {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const toggleSelection = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectByFilter = useCallback(
    (predicate: (item: ApprovalQueueItem) => boolean) => {
      const matchingIds = items.filter(predicate).map((item) => item.id);
      setSelectedIds(new Set(matchingIds));
    },
    [items]
  );

  const selectAllWouldAutoPublish = useCallback(() => {
    selectByFilter((item) => item.would_auto_publish);
  }, [selectByFilter]);

  // ... rest of implementation
}
```

### Batch Action Bar Component

**Source:** UI patterns for batch operations

```typescript
// components/approval/BatchActionBar.tsx

interface BatchActionBarProps {
  selectedCount: number;
  onApproveAll: () => void;
  onRejectAll: () => void;
  onClearSelection: () => void;
  isLoading: boolean;
}

export function BatchActionBar({
  selectedCount,
  onApproveAll,
  onRejectAll,
  onClearSelection,
  isLoading,
}: BatchActionBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-background border-t shadow-lg p-4 flex items-center justify-between z-50 animate-in slide-in-from-bottom-4">
      <div className="flex items-center gap-4">
        <span className="font-medium text-foreground">
          {selectedCount} item{selectedCount !== 1 ? "s" : ""} selected
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClearSelection}
        >
          Clear
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          className="border-red-500 text-red-600 hover:bg-red-50"
          onClick={onRejectAll}
          disabled={isLoading}
        >
          Reject All
        </Button>
        <Button
          className="bg-green-600 hover:bg-green-700 text-white"
          onClick={onApproveAll}
          disabled={isLoading}
        >
          {isLoading ? "Processing..." : "Approve All"}
        </Button>
      </div>
    </div>
  );
}
```

### Backend Repository Methods

**Source:** [4-2-approve-reject-edit-actions.md#Backend-Repository-Methods]

```python
# ui/backend/repositories/approval_repository.py (EXTEND)

class ApprovalRepository:
    # Existing methods from 4-1 and 4-2...

    async def batch_approve_items(
        self,
        item_ids: list[str],
        operator_id: str = "operator",
    ) -> BatchApproveResponse:
        """Batch approve items and move to scheduled queue."""
        batch_id = str(uuid4())
        results = []
        successful = 0
        failed = 0
        earliest_time = None
        latest_time = None

        for item_id in item_ids:
            try:
                item = await self._get_item(item_id)
                if item.status != ApprovalStatus.PENDING:
                    results.append(BatchActionResultItem(
                        item_id=item_id,
                        success=False,
                        error=f"Item not in PENDING status: {item.status}",
                    ))
                    failed += 1
                    continue

                item.status = ApprovalStatus.APPROVED
                item.approved_at = datetime.utcnow()
                item.approved_by = operator_id
                item.batch_id = batch_id

                # Track date range for summary
                if earliest_time is None or item.suggested_publish_time < earliest_time:
                    earliest_time = item.suggested_publish_time
                if latest_time is None or item.suggested_publish_time > latest_time:
                    latest_time = item.suggested_publish_time

                await self._log_audit(
                    item_id=item_id,
                    action="BATCH_APPROVE",
                    batch_id=batch_id,
                    operator_id=operator_id,
                )

                results.append(BatchActionResultItem(
                    item_id=item_id,
                    success=True,
                    scheduled_publish_time=item.suggested_publish_time,
                ))
                successful += 1

            except Exception as e:
                results.append(BatchActionResultItem(
                    item_id=item_id,
                    success=False,
                    error=str(e),
                ))
                failed += 1

        await self.session.commit()

        # Generate summary
        if earliest_time and latest_time:
            if earliest_time.date() == latest_time.date():
                summary = f"{successful} items approved, scheduled for {earliest_time.strftime('%b %d')}"
            else:
                summary = f"{successful} items approved, scheduled for {earliest_time.strftime('%b %d')}-{latest_time.strftime('%b %d')}"
        else:
            summary = f"{successful} items approved"

        return BatchApproveResponse(
            batch_id=batch_id,
            total_requested=len(item_ids),
            successful_count=successful,
            failed_count=failed,
            results=results,
            summary=summary,
        )

    async def batch_reject_items(
        self,
        item_ids: list[str],
        reason: RejectReason,
        reason_text: Optional[str],
        operator_id: str = "operator",
    ) -> BatchRejectResponse:
        """Batch reject items with reason."""
        batch_id = str(uuid4())
        results = []
        successful = 0
        failed = 0

        for item_id in item_ids:
            try:
                item = await self._get_item(item_id)
                if item.status != ApprovalStatus.PENDING:
                    results.append(BatchActionResultItem(
                        item_id=item_id,
                        success=False,
                        error=f"Item not in PENDING status: {item.status}",
                    ))
                    failed += 1
                    continue

                item.status = ApprovalStatus.REJECTED
                item.rejected_at = datetime.utcnow()
                item.rejected_by = operator_id
                item.rejection_reason = reason
                item.rejection_text = reason_text
                item.batch_id = batch_id

                await self._log_audit(
                    item_id=item_id,
                    action="BATCH_REJECT",
                    batch_id=batch_id,
                    operator_id=operator_id,
                    details={"reason": reason.value, "reason_text": reason_text},
                )

                results.append(BatchActionResultItem(
                    item_id=item_id,
                    success=True,
                ))
                successful += 1

            except Exception as e:
                results.append(BatchActionResultItem(
                    item_id=item_id,
                    success=False,
                    error=str(e),
                ))
                failed += 1

        await self.session.commit()

        summary = f"{successful} items rejected: {reason.value.replace('_', ' ').title()}"

        return BatchRejectResponse(
            batch_id=batch_id,
            total_requested=len(item_ids),
            successful_count=successful,
            failed_count=failed,
            results=results,
            summary=summary,
        )
```

### Keyboard Shortcuts (CRITICAL)

**Source:** Story 4-2 keyboard patterns, extended for batch

```typescript
// In ApprovalQueue or BatchActionBar component

useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Batch shortcuts require Shift modifier
    if (!e.shiftKey || selectedCount === 0) return;

    switch (e.key.toLowerCase()) {
      case 'a':
        e.preventDefault();
        openBatchApproveDialog();
        break;
      case 'r':
        e.preventDefault();
        openBatchRejectDialog();
        break;
    }
  };

  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, [selectedCount]);
```

### Quick Filter Component

**Source:** Design for WOULD_AUTO_PUBLISH quick selection

```typescript
// components/approval/QuickFilters.tsx

interface QuickFiltersProps {
  items: ApprovalQueueItem[];
  onSelectWouldAutoPublish: () => void;
  wouldAutoPublishCount: number;
}

export function QuickFilters({
  items,
  onSelectWouldAutoPublish,
  wouldAutoPublishCount,
}: QuickFiltersProps) {
  if (wouldAutoPublishCount === 0) return null;

  return (
    <div className="flex items-center gap-2 mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
      <Badge variant="secondary" className="bg-green-100 text-green-800">
        {wouldAutoPublishCount} WOULD_AUTO_PUBLISH
      </Badge>
      <Button
        variant="outline"
        size="sm"
        onClick={onSelectWouldAutoPublish}
        className="text-green-700 border-green-300 hover:bg-green-100"
      >
        Select All High-Quality
      </Button>
      <span className="text-sm text-green-700">
        One-click to approve all items that would auto-publish
      </span>
    </div>
  );
}
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [4-1-content-approval-queue-ui.md], [4-2-approve-reject-edit-actions.md]

| Learning | How to Apply in 4-3 |
|----------|---------------------|
| Complete `__all__` exports | Export all new components in index.ts |
| TypeScript strict mode | No `any` types in batch schemas |
| Loading states | Show loading in BatchActionBar during operations |
| Error boundaries | Handle partial batch failures gracefully |
| Mobile responsive | Stack action buttons vertically on mobile |
| Accessibility | aria-labels on checkboxes, keyboard shortcuts |
| SWR mutations | Use mutate() for optimistic queue updates |
| Toast notifications | Use Sonner for success/error feedback |
| Virtualized lists | Ensure selection works with VirtualizedQueueList |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER process items sequentially when parallel is possible** - Use bulk database operations
2. **NEVER skip confirmation for batch actions** - Always show confirmation dialog
3. **NEVER lose selection state on re-render** - Persist selection in hook state
4. **NEVER block UI during batch processing** - Show progress and allow cancellation
5. **NEVER apply different rejection reasons per item in batch** - Use single reason for batch
6. **NEVER skip audit trail** - Log all batch actions with batch_id reference

### LLM Tier Assignment

**Source:** [project-context.md#LLM-Tier-Assignment]

```
This story is UI/API only - NO LLM usage required.
No tier assignment needed.

FORBIDDEN in code/docstrings/comments:
- "haiku", "sonnet", "opus"
- "claude-haiku", "claude-sonnet", "claude-opus"
```

### File Structure (MUST FOLLOW)

**Source:** IMAGO.ECO frontend conventions, extends 4-1 and 4-2 structure

```
ui/frontend-react/src/
├── components/
│   └── approval/
│       ├── index.ts                     # (EXTEND) Add new exports
│       ├── BatchActionBar.tsx           # (NEW)
│       ├── QuickFilters.tsx             # (NEW)
│       ├── BatchApproveConfirmDialog.tsx # (NEW)
│       ├── BatchRejectConfirmDialog.tsx  # (NEW)
│       ├── ApprovalQueue.tsx            # (MODIFY) Add selection
│       └── ApprovalQueueItem.tsx        # (MODIFY) Add checkbox
├── hooks/
│   ├── useQueueSelection.ts             # (NEW)
│   └── useBatchApproval.ts              # (NEW)
├── types/
│   └── approval.ts                      # (EXTEND) Add batch types
└── __tests__/
    └── approval/
        ├── BatchActionBar.test.tsx      # (NEW)
        ├── QuickFilters.test.tsx        # (NEW)
        ├── useQueueSelection.test.tsx   # (NEW)
        └── useBatchApproval.test.tsx    # (NEW)

ui/backend/
├── routers/
│   └── approval_queue.py                # (EXTEND) Add batch endpoints
├── schemas/
│   └── batch_approval.py                # (NEW)
└── repositories/
    └── approval_repository.py           # (EXTEND) Add batch methods

tests/
├── ui/backend/
│   └── test_batch_approval.py           # (NEW)
└── core/approval/
    └── test_batch_operations.py         # (NEW)
```

### Edge Cases to Handle

1. **Empty selection**: Disable batch action buttons when count = 0
2. **Single item selected**: Show batch UI but behave like individual action
3. **All items fail**: Show error with details, no partial success
4. **Mixed statuses in selection**: Only process PENDING items, report skipped
5. **Large batch (50+ items)**: Show progress indicator, chunk requests
6. **Network timeout during batch**: Implement partial rollback, show completed items
7. **Concurrent batch by another operator**: Handle 409 Conflict gracefully
8. **Selection includes items from different pages**: Persist selection across pagination
9. **Batch reject with OTHER but no text**: Validate reason_text is required
10. **Queue refresh during batch**: Preserve selection state, re-validate against new data

### Performance Requirements (CRITICAL)

**Source:** [epics.md#Story-4.3] - "daily review takes under 5 minutes"

```
- Batch of 10 items: Complete in < 3 seconds
- Batch of 50 items: Complete in < 10 seconds
- Selection toggle: < 50ms response
- Optimistic UI update: Immediate visual feedback
- Queue refresh after batch: < 1 second
```

### Database Considerations

**Source:** [4-1-content-approval-queue-ui.md#Backend-approval-item-model]

```python
# Add batch_id field to ApprovalItem model for audit trail grouping

class ApprovalItem(Base):
    # Existing fields...

    # NEW: Track batch operations
    batch_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
```

### Project Structure Notes

- **Location**: Extends `ui/frontend-react/src/components/approval/`, `ui/backend/routers/`
- **Dependencies**: Stories 4-1 and 4-2 components, useApprovalQueue, useApprovalActions
- **Used by**: IMAGO dashboard operator workflow
- **Performance target**: Batch actions complete in < 3-10 seconds depending on count
- **Audit requirements**: All batch actions logged with batch_id for grouping

### References

- [Source: epics.md#Story-4.3] - Original story requirements (FR37)
- [Source: 4-1-content-approval-queue-ui.md] - Queue UI and item components
- [Source: 4-2-approve-reject-edit-actions.md] - Individual action patterns
- [Source: project-context.md#Technology-Stack] - Tech stack
- [Source: project-context.md#Approval-Workflow] - Approval flow
- [Source: architecture.md#Data-Flow] - System architecture
- [Source: core/approval/] - ApprovalManager integration

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Implemented selection state management via `useQueueSelection` hook with Set-based tracking for O(1) lookups
- BatchActionBar uses fixed positioning with z-50 for overlay behavior and slide-in animation
- Keyboard shortcuts (Shift+A/R) implemented via document-level event listener with proper cleanup
- Confirmation dialogs support "Don't show again" preference with localStorage persistence
- Backend batch operations process items individually to support partial failure reporting
- Each batch operation generates unique batch_id (UUID) for audit trail grouping
- Frontend uses optimistic UI updates with rollback on failure via SWR mutate
- QuickFilters provides one-click "Approve All High-Quality" combining filter + approve
- Trust metrics tracking for WOULD_AUTO_PUBLISH approvals via `/api/approval-queue/metrics/trust` endpoint

**Code Review Fixes Applied:**
- Fixed backend tests referencing non-existent methods (`get_by_ids` → `get_by_id`)
- Fixed batch_id assertions in tests (UUID format, not "batch-" prefix)
- Added localStorage persistence for "Don't show again" dialog preferences
- Added trust metrics tracking for Task 5.6 compliance

### File List

**Frontend - New Components:**
- `ui/frontend-react/src/components/approval/BatchActionBar.tsx` - Sticky batch action bar
- `ui/frontend-react/src/components/approval/QuickFilters.tsx` - WOULD_AUTO_PUBLISH quick filter
- `ui/frontend-react/src/components/approval/BatchApproveConfirmDialog.tsx` - Batch approve confirmation
- `ui/frontend-react/src/components/approval/BatchRejectConfirmDialog.tsx` - Batch reject confirmation

**Frontend - New Hooks:**
- `ui/frontend-react/src/hooks/useQueueSelection.ts` - Selection state management
- `ui/frontend-react/src/hooks/useBatchApproval.ts` - Batch mutation operations

**Frontend - Modified:**
- `ui/frontend-react/src/components/approval/ApprovalQueueItem.tsx` - Added checkbox selection
- `ui/frontend-react/src/components/approval/index.ts` - Added batch component exports
- `ui/frontend-react/src/pages/ApprovalQueue.tsx` - Integrated batch operations
- `ui/frontend-react/src/types/approval.ts` - Added batch types

**Frontend - New Tests:**
- `ui/frontend-react/src/components/approval/__tests__/BatchActionBar.test.tsx`
- `ui/frontend-react/src/components/approval/__tests__/QuickFilters.test.tsx`
- `ui/frontend-react/src/components/approval/__tests__/BatchApproveConfirmDialog.test.tsx`
- `ui/frontend-react/src/components/approval/__tests__/BatchRejectConfirmDialog.test.tsx`
- `ui/frontend-react/src/hooks/__tests__/useQueueSelection.test.tsx`
- `ui/frontend-react/src/hooks/__tests__/useBatchApproval.test.tsx`

**Backend - New:**
- `ui/backend/schemas/batch_approval.py` - Batch request/response schemas

**Backend - Modified:**
- `ui/backend/routers/approval_queue.py` - Added batch endpoints
- `ui/backend/repositories/approval_repository.py` - Added batch methods

**Backend - New Tests:**
- `tests/ui/backend/test_batch_approval.py` - Batch endpoint integration tests

