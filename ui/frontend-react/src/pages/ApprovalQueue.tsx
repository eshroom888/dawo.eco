/**
 * ApprovalQueue page component.
 *
 * Main page for viewing and managing content pending approval.
 * Displays a list/grid of approval items sorted by priority.
 *
 * Features:
 * - Priority-sorted queue display
 * - Automatic refresh (30s interval)
 * - Loading skeletons
 * - Empty state handling
 * - Click to open detail modal
 */

import React, { useState, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useApprovalQueue } from "@/hooks/useApprovalQueue";
import { useQueueSelection } from "@/hooks/useQueueSelection";
import { useToast } from "@/hooks/useToast";
import { useBatchApproval } from "@/hooks/useBatchApproval";
import { ApprovalQueueItem as ApprovalQueueItemType, RejectActionRequest } from "@/types/approval";
import { ApprovalQueueItem } from "@/components/approval/ApprovalQueueItem";
import { ApprovalDetailModal } from "@/components/approval/ApprovalDetailModal";
import { VirtualizedQueueList } from "@/components/approval/VirtualizedQueueList";
import { BatchActionBar } from "@/components/approval/BatchActionBar";
import { QuickFilters } from "@/components/approval/QuickFilters";
import { BatchApproveConfirmDialog } from "@/components/approval/BatchApproveConfirmDialog";
import { BatchRejectConfirmDialog } from "@/components/approval/BatchRejectConfirmDialog";
import { ToastContainer } from "@/components/Toast";

// Threshold for switching to virtualized list (Task 7.3: 100+ items)
const VIRTUALIZATION_THRESHOLD = 100;

// Pull-to-refresh settings (Task 3.6)
const PULL_THRESHOLD = 80;

export interface ApprovalQueueProps {
  className?: string;
}

/**
 * Loading skeleton for queue items.
 */
function QueueItemSkeleton(): React.ReactElement {
  return (
    <Card className="animate-pulse">
      <CardHeader className="pb-2">
        <div className="flex gap-4">
          <Skeleton className="w-20 h-20 rounded-md" />
          <div className="flex flex-col gap-2 flex-1">
            <div className="flex gap-2">
              <Skeleton className="w-12 h-5 rounded" />
              <Skeleton className="w-20 h-5 rounded" />
            </div>
            <Skeleton className="w-24 h-5 rounded" />
            <Skeleton className="w-16 h-4 rounded" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        <Skeleton className="w-full h-4 rounded" />
        <Skeleton className="w-3/4 h-4 rounded mt-2" />
      </CardContent>
    </Card>
  );
}

/**
 * Empty state when no items are pending.
 */
function EmptyState(): React.ReactElement {
  return (
    <Card className="text-center py-12">
      <CardContent>
        <div className="text-4xl mb-4" role="img" aria-label="Celebration">
          {"\uD83C\uDF89"}
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          All caught up!
        </h3>
        <p className="text-gray-500">
          No content pending approval. Check back later or create new content.
        </p>
      </CardContent>
    </Card>
  );
}

/**
 * Error state when queue fails to load.
 */
function ErrorState({
  error,
  onRetry,
}: {
  error: Error;
  onRetry: () => void;
}): React.ReactElement {
  return (
    <Card className="text-center py-12 border-red-200">
      <CardContent>
        <div className="text-4xl mb-4" role="img" aria-label="Error">
          {"\u26A0\uFE0F"}
        </div>
        <h3 className="text-lg font-medium text-red-800 mb-2">
          Failed to load queue
        </h3>
        <p className="text-gray-500 mb-4">{error.message}</p>
        <Button onClick={onRetry} variant="outline">
          Try Again
        </Button>
      </CardContent>
    </Card>
  );
}

/**
 * ApprovalQueue page component.
 */
export function ApprovalQueue({
  className = "",
}: ApprovalQueueProps): React.ReactElement {
  const { items, totalCount, isLoading, error, refresh } = useApprovalQueue();
  const [selectedItem, setSelectedItem] = useState<ApprovalQueueItemType | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Story 4-3: Selection state for batch operations
  const {
    isSelected,
    toggleSelection,
    selectedCount,
    isAllSelected,
    isSomeSelected,
    toggleSelectAll,
    clearSelection,
    getSelectedItems,
    selectByFilter,
  } = useQueueSelection(items);

  // Story 4-3, Task 7-8: Toast and batch approval hooks
  const toast = useToast();
  const {
    batchApprove,
    batchReject,
    isLoading: isBatchLoading,
  } = useBatchApproval(toast, refresh, clearSelection);

  // Story 4-3, Task 6: Dialog states
  const [isApproveDialogOpen, setIsApproveDialogOpen] = useState(false);
  const [isRejectDialogOpen, setIsRejectDialogOpen] = useState(false);
  const [pendingHighQualityApprove, setPendingHighQualityApprove] = useState(false);

  // Task 6.6: Persist "Don't show again" to localStorage for power users
  const [dontShowApproveDialog, setDontShowApproveDialogState] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("approval_queue_skip_approve_dialog") === "true";
    }
    return false;
  });
  const [dontShowRejectDialog, setDontShowRejectDialogState] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("approval_queue_skip_reject_dialog") === "true";
    }
    return false;
  });

  // Wrapper functions that persist to localStorage
  const setDontShowApproveDialog = useCallback((value: boolean) => {
    setDontShowApproveDialogState(value);
    if (typeof window !== "undefined") {
      localStorage.setItem("approval_queue_skip_approve_dialog", String(value));
    }
  }, []);

  const setDontShowRejectDialog = useCallback((value: boolean) => {
    setDontShowRejectDialogState(value);
    if (typeof window !== "undefined") {
      localStorage.setItem("approval_queue_skip_reject_dialog", String(value));
    }
  }, []);

  // Story 4-3, Task 6: Batch action handlers that open confirmation dialogs
  const handleBatchApprove = useCallback(() => {
    if (dontShowApproveDialog) {
      // Skip dialog for power users - approve directly
      batchApprove(getSelectedItems());
      clearSelection();
    } else {
      setIsApproveDialogOpen(true);
    }
  }, [getSelectedItems, dontShowApproveDialog, batchApprove, clearSelection]);

  const handleBatchReject = useCallback(() => {
    // Always show dialog for reject to get reason
    setIsRejectDialogOpen(true);
  }, []);

  // Confirm handlers for dialogs
  const handleConfirmApprove = useCallback(async () => {
    const selectedItems = pendingHighQualityApprove
      ? items.filter((item) => item.would_auto_publish)
      : getSelectedItems();

    try {
      await batchApprove(selectedItems);
      setIsApproveDialogOpen(false);
      setPendingHighQualityApprove(false);
      clearSelection();
    } catch (error) {
      // Error is handled by the hook with toast
    }
  }, [getSelectedItems, items, pendingHighQualityApprove, clearSelection, batchApprove]);

  const handleConfirmReject = useCallback(
    async (request: RejectActionRequest) => {
      try {
        await batchReject(getSelectedItems(), request);
        setIsRejectDialogOpen(false);
        clearSelection();
      } catch (error) {
        // Error is handled by the hook with toast
      }
    },
    [getSelectedItems, clearSelection, batchReject]
  );

  // Story 4-3, Task 5: Quick filter handlers
  const handleSelectWouldAutoPublish = useCallback(() => {
    // Task 5.3: Select only would_auto_publish=true items
    selectByFilter((item) => item.would_auto_publish);
  }, [selectByFilter]);

  const handleApproveAllHighQuality = useCallback(() => {
    // Task 5.5: One-click action to approve high-quality items
    const highQualityItems = items.filter((item) => item.would_auto_publish);
    if (highQualityItems.length === 0) return;

    // Select them first (for visual feedback)
    selectByFilter((item) => item.would_auto_publish);

    if (dontShowApproveDialog) {
      // Skip dialog for power users - approve directly
      batchApprove(highQualityItems);
      clearSelection();
    } else {
      // Mark that we're doing a high-quality approve (uses different item set)
      setPendingHighQualityApprove(true);
      setIsApproveDialogOpen(true);
    }
  }, [selectByFilter, items, dontShowApproveDialog]);

  // Pull-to-refresh state (Task 3.6 - mobile support)
  const [pullDistance, setPullDistance] = useState(0);
  const [isPulling, setIsPulling] = useState(false);
  const touchStartY = useRef(0);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const handleItemClick = useCallback((item: ApprovalQueueItemType) => {
    setSelectedItem(item);
    setIsModalOpen(true);
  }, []);

  const handleModalClose = useCallback(() => {
    setIsModalOpen(false);
    setSelectedItem(null);
  }, []);

  const handleNavigate = useCallback(
    (direction: "prev" | "next") => {
      if (!selectedItem) return;
      const currentIndex = items.findIndex((i) => i.id === selectedItem.id);
      const newIndex = direction === "next" ? currentIndex + 1 : currentIndex - 1;
      if (newIndex >= 0 && newIndex < items.length) {
        setSelectedItem(items[newIndex]);
      }
    },
    [items, selectedItem]
  );

  // Pull-to-refresh handlers (Task 3.6)
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const scrollTop = scrollAreaRef.current?.scrollTop ?? 0;
    if (scrollTop === 0) {
      touchStartY.current = e.touches[0].clientY;
      setIsPulling(true);
    }
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isPulling) return;
    const currentY = e.touches[0].clientY;
    const distance = Math.max(0, currentY - touchStartY.current);
    setPullDistance(Math.min(distance, PULL_THRESHOLD * 1.5));
  }, [isPulling]);

  const handleTouchEnd = useCallback(() => {
    if (pullDistance >= PULL_THRESHOLD && !isLoading) {
      refresh();
    }
    setPullDistance(0);
    setIsPulling(false);
  }, [pullDistance, isLoading, refresh]);

  // Use virtualized list for large queues (Task 7.3)
  const useVirtualization = items.length >= VIRTUALIZATION_THRESHOLD;

  return (
    <div className={`p-6 ${className}`}>
      {/* Header */}
      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Story 4-3, Task 1.3: Select All checkbox */}
            {items.length > 0 && (
              <Checkbox
                checked={isAllSelected}
                onCheckedChange={toggleSelectAll}
                aria-label={isAllSelected ? "Deselect all items" : "Select all items"}
                className="data-[state=indeterminate]:bg-blue-500"
                {...(isSomeSelected && !isAllSelected
                  ? { "data-state": "indeterminate" }
                  : {})}
              />
            )}
            <div>
              <CardTitle>Approval Queue</CardTitle>
              <p className="text-sm text-gray-500 mt-1">
                {isLoading ? (
                  <Skeleton className="w-24 h-4 inline-block" />
                ) : selectedCount > 0 ? (
                  `${selectedCount} of ${totalCount} selected`
                ) : (
                  `${totalCount} item${totalCount !== 1 ? "s" : ""} pending`
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Story 4-3, Task 1.6: Clear selection button */}
            {selectedCount > 0 && (
              <Button
                onClick={clearSelection}
                variant="ghost"
                size="sm"
                aria-label="Clear selection"
              >
                Clear
              </Button>
            )}
            <Button
              onClick={() => refresh()}
              variant="outline"
              size="sm"
              disabled={isLoading}
              aria-label="Refresh queue"
            >
              {"\u21BB"} Refresh
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Story 4-3, Task 5: Quick filters for batch operations */}
      {items.length > 0 && (
        <QuickFilters
          items={items}
          onSelectWouldAutoPublish={handleSelectWouldAutoPublish}
          onApproveAllHighQuality={handleApproveAllHighQuality}
          selectedCount={selectedCount}
          isLoading={isBatchLoading}
        />
      )}

      {/* Queue content with pull-to-refresh (Task 3.6) */}
      <div
        ref={scrollAreaRef}
        className="h-[calc(100vh-200px)] overflow-auto"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Pull-to-refresh indicator */}
        {pullDistance > 0 && (
          <div
            className="flex items-center justify-center text-gray-500 transition-all"
            style={{ height: pullDistance }}
          >
            {pullDistance >= PULL_THRESHOLD ? (
              <span>{"\u21BB"} Release to refresh</span>
            ) : (
              <span>{"\u2193"} Pull to refresh</span>
            )}
          </div>
        )}

        <ScrollArea className="h-full">
          {/* Error state */}
          {error && !isLoading && (
            <ErrorState error={error} onRetry={refresh} />
          )}

          {/* Loading state */}
          {isLoading && items.length === 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <QueueItemSkeleton key={i} />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && items.length === 0 && <EmptyState />}

          {/* Queue items - use virtualization for 100+ items (Task 7.3) */}
          {items.length > 0 && !useVirtualization && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {items.map((item) => (
                <ApprovalQueueItem
                  key={item.id}
                  item={item}
                  onClick={handleItemClick}
                  selectable={true}
                  isSelected={isSelected(item.id)}
                  onSelectionChange={toggleSelection}
                />
              ))}
            </div>
          )}

          {/* Virtualized list for large queues (Task 7.3) */}
          {items.length > 0 && useVirtualization && (
            <VirtualizedQueueList
              items={items}
              onItemClick={handleItemClick}
              className="h-full"
              selectable={true}
              isSelected={isSelected}
              onSelectionChange={toggleSelection}
            />
          )}
        </ScrollArea>
      </div>

      {/* Detail modal */}
      <ApprovalDetailModal
        item={selectedItem}
        isOpen={isModalOpen}
        onClose={handleModalClose}
        onNavigate={handleNavigate}
        hasPrev={
          selectedItem
            ? items.findIndex((i) => i.id === selectedItem.id) > 0
            : false
        }
        hasNext={
          selectedItem
            ? items.findIndex((i) => i.id === selectedItem.id) < items.length - 1
            : false
        }
      />

      {/* Story 4-3, Task 2: Batch action bar */}
      <BatchActionBar
        selectedCount={selectedCount}
        onApproveAll={handleBatchApprove}
        onRejectAll={handleBatchReject}
        onClearSelection={clearSelection}
        isLoading={isBatchLoading}
      />

      {/* Story 4-3, Task 6: Batch confirmation dialogs */}
      <BatchApproveConfirmDialog
        isOpen={isApproveDialogOpen}
        items={
          pendingHighQualityApprove
            ? items.filter((item) => item.would_auto_publish)
            : getSelectedItems()
        }
        onConfirm={handleConfirmApprove}
        onCancel={() => {
          setIsApproveDialogOpen(false);
          setPendingHighQualityApprove(false);
        }}
        isLoading={isBatchLoading}
        dontShowAgain={dontShowApproveDialog}
        onDontShowAgainChange={setDontShowApproveDialog}
      />

      <BatchRejectConfirmDialog
        isOpen={isRejectDialogOpen}
        items={getSelectedItems()}
        onConfirm={handleConfirmReject}
        onCancel={() => setIsRejectDialogOpen(false)}
        isLoading={isBatchLoading}
        dontShowAgain={dontShowRejectDialog}
        onDontShowAgainChange={setDontShowRejectDialog}
      />

      {/* Story 4-3, Task 7: Toast notifications for feedback */}
      <ToastContainer toasts={toast.toasts} onDismiss={toast.dismiss} />
    </div>
  );
}

export default ApprovalQueue;
