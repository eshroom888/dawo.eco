/**
 * useBatchApproval hook.
 *
 * Story 4-3: Batch Approval Capability
 * Task 8: Create useBatchApproval hook (AC: all)
 *
 * Features:
 * - Batch approve/reject mutations
 * - Optimistic UI updates
 * - Error handling with partial success reporting
 * - Progress indicator for large batches (10+ items)
 * - Integration with toast notifications
 */

import { useState, useCallback, useMemo } from "react";
import { mutate } from "swr";
import {
  ApprovalQueueItem,
  RejectActionRequest,
  ApprovalStatus,
} from "@/types/approval";
import { UseToastReturn } from "./useToast";

// API base URL
const API_BASE = "/api/approval-queue";

// Threshold for showing progress indicator
const PROGRESS_THRESHOLD = 10;

/**
 * Batch action result from API.
 */
export interface BatchActionResult {
  batch_id: string;
  total_requested: number;
  successful_count: number;
  failed_count: number;
  results: BatchActionResultItem[];
  summary: string;
}

export interface BatchActionResultItem {
  item_id: string;
  success: boolean;
  error_message?: string;
  scheduled_publish_time?: string;
}

/**
 * Return type for useBatchApproval hook.
 */
export interface UseBatchApprovalReturn {
  /** Execute batch approval */
  batchApprove: (items: ApprovalQueueItem[]) => Promise<BatchActionResult>;
  /** Execute batch rejection */
  batchReject: (
    items: ApprovalQueueItem[],
    request: RejectActionRequest
  ) => Promise<BatchActionResult>;
  /** Whether a batch operation is in progress */
  isLoading: boolean;
  /** Progress percentage for large batches */
  progress: number | null;
  /** Current operation type */
  currentOperation: "approve" | "reject" | null;
  /** Number of items being processed */
  processingCount: number;
}

/**
 * Format date range for toast message.
 */
function formatDateRange(dates: string[]): string {
  if (dates.length === 0) return "";

  const parsed = dates
    .map((d) => new Date(d))
    .sort((a, b) => a.getTime() - b.getTime());

  const options: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  const first = parsed[0].toLocaleDateString("en-US", options);

  if (parsed.length === 1) return first;

  const last = parsed[parsed.length - 1].toLocaleDateString("en-US", options);
  return `${first} - ${last}`;
}

/**
 * Task 5.6: Track WOULD_AUTO_PUBLISH approval usage for trust metrics.
 *
 * Sends analytics data when high-quality items are batch approved.
 * This data is used to refine the auto-publish threshold over time.
 */
async function trackHighQualityApprovals(
  items: ApprovalQueueItem[],
  batchId: string
): Promise<void> {
  const highQualityItems = items.filter((item) => item.would_auto_publish);

  if (highQualityItems.length === 0) return;

  try {
    await fetch(`${API_BASE}/metrics/trust`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        batch_id: batchId,
        event_type: "high_quality_batch_approved",
        total_approved: items.length,
        high_quality_count: highQualityItems.length,
        high_quality_percentage: (highQualityItems.length / items.length) * 100,
        item_ids: highQualityItems.map((item) => item.id),
        timestamp: new Date().toISOString(),
      }),
    });
  } catch (error) {
    // Non-blocking - don't fail batch approval if metrics tracking fails
    console.warn("Failed to track high-quality approval metrics:", error);
  }
}

/**
 * Hook for batch approval/rejection operations.
 *
 * @param toast - Toast hook for notifications (Task 7)
 * @param onSuccess - Callback after successful batch operation
 * @param onItemsRemoved - Callback to optimistically remove items
 */
export function useBatchApproval(
  toast: UseToastReturn,
  onSuccess?: () => void,
  onItemsRemoved?: (itemIds: string[]) => void
): UseBatchApprovalReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [currentOperation, setCurrentOperation] = useState<"approve" | "reject" | null>(null);
  const [processingCount, setProcessingCount] = useState(0);

  /**
   * Task 8.1: Batch approve mutation.
   */
  const batchApprove = useCallback(
    async (items: ApprovalQueueItem[]): Promise<BatchActionResult> => {
      const itemIds = items.map((item) => item.id);
      setIsLoading(true);
      setCurrentOperation("approve");
      setProcessingCount(items.length);

      // Task 8.5: Show progress for large batches
      if (items.length >= PROGRESS_THRESHOLD) {
        setProgress(0);
      }

      // Task 7.3: Optimistic UI update - remove items immediately
      if (onItemsRemoved) {
        onItemsRemoved(itemIds);
      }

      try {
        const response = await fetch(`${API_BASE}/batch/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ item_ids: itemIds }),
        });

        if (!response.ok) {
          throw new Error(`Batch approval failed: ${response.statusText}`);
        }

        const result: BatchActionResult = await response.json();

        // Update progress
        if (items.length >= PROGRESS_THRESHOLD) {
          setProgress(100);
        }

        // Task 7.1: Success toast with date range
        if (result.successful_count > 0) {
          const scheduledDates = result.results
            .filter((r) => r.success && r.scheduled_publish_time)
            .map((r) => r.scheduled_publish_time!);

          const dateRange = formatDateRange(scheduledDates);
          const message = dateRange
            ? `Scheduled for ${dateRange}`
            : "Items queued for publishing";

          toast.success(
            `${result.successful_count} item${result.successful_count !== 1 ? "s" : ""} approved`,
            message
          );
        }

        // Task 7.2: Error toast for partial failures
        if (result.failed_count > 0) {
          const failedIds = result.results
            .filter((r) => !r.success)
            .map((r) => r.item_id);

          toast.error(
            `${result.failed_count} item${result.failed_count !== 1 ? "s" : ""} failed`,
            "Some items could not be approved",
            () => {
              // Retry failed items
              const failedItems = items.filter((item) =>
                failedIds.includes(item.id)
              );
              if (failedItems.length > 0) {
                batchApprove(failedItems);
              }
            }
          );

          // Task 7.4: Rollback failed items (restore to queue)
          // This would trigger a re-fetch or add items back to state
        }

        // Task 5.6: Track WOULD_AUTO_PUBLISH approval usage for trust metrics
        if (result.successful_count > 0) {
          trackHighQualityApprovals(items, result.batch_id);
        }

        // Task 7.5: Auto-refresh queue
        await mutate(`${API_BASE}/items`);
        onSuccess?.();

        return result;
      } catch (error) {
        // Task 7.4: Full rollback on complete failure
        toast.error(
          "Batch approval failed",
          error instanceof Error ? error.message : "Unknown error",
          () => batchApprove(items)
        );

        // Re-fetch to restore state
        await mutate(`${API_BASE}/items`);

        throw error;
      } finally {
        setIsLoading(false);
        setProgress(null);
        setCurrentOperation(null);
        setProcessingCount(0);
      }
    },
    [toast, onSuccess, onItemsRemoved]
  );

  /**
   * Task 8.1: Batch reject mutation.
   */
  const batchReject = useCallback(
    async (
      items: ApprovalQueueItem[],
      request: RejectActionRequest
    ): Promise<BatchActionResult> => {
      const itemIds = items.map((item) => item.id);
      setIsLoading(true);
      setCurrentOperation("reject");
      setProcessingCount(items.length);

      // Task 8.5: Show progress for large batches
      if (items.length >= PROGRESS_THRESHOLD) {
        setProgress(0);
      }

      // Task 7.3: Optimistic UI update - remove items immediately
      if (onItemsRemoved) {
        onItemsRemoved(itemIds);
      }

      try {
        const response = await fetch(`${API_BASE}/batch/reject`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            item_ids: itemIds,
            reason: request.reason,
            reason_text: request.reason_text,
          }),
        });

        if (!response.ok) {
          throw new Error(`Batch rejection failed: ${response.statusText}`);
        }

        const result: BatchActionResult = await response.json();

        // Update progress
        if (items.length >= PROGRESS_THRESHOLD) {
          setProgress(100);
        }

        // Task 7.1: Success toast
        if (result.successful_count > 0) {
          toast.success(
            `${result.successful_count} item${result.successful_count !== 1 ? "s" : ""} rejected`,
            "Items have been removed from the queue"
          );
        }

        // Task 7.2: Error toast for partial failures
        if (result.failed_count > 0) {
          const failedIds = result.results
            .filter((r) => !r.success)
            .map((r) => r.item_id);

          toast.error(
            `${result.failed_count} item${result.failed_count !== 1 ? "s" : ""} failed`,
            "Some items could not be rejected",
            () => {
              const failedItems = items.filter((item) =>
                failedIds.includes(item.id)
              );
              if (failedItems.length > 0) {
                batchReject(failedItems, request);
              }
            }
          );
        }

        // Task 7.5: Auto-refresh queue
        await mutate(`${API_BASE}/items`);
        onSuccess?.();

        return result;
      } catch (error) {
        // Task 7.4: Full rollback on complete failure
        toast.error(
          "Batch rejection failed",
          error instanceof Error ? error.message : "Unknown error",
          () => batchReject(items, request)
        );

        // Re-fetch to restore state
        await mutate(`${API_BASE}/items`);

        throw error;
      } finally {
        setIsLoading(false);
        setProgress(null);
        setCurrentOperation(null);
        setProcessingCount(0);
      }
    },
    [toast, onSuccess, onItemsRemoved]
  );

  return {
    batchApprove,
    batchReject,
    isLoading,
    progress,
    currentOperation,
    processingCount,
  };
}

export default useBatchApproval;
