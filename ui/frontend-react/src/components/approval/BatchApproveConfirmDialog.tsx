/**
 * BatchApproveConfirmDialog component.
 *
 * Story 4-3: Batch Approval Capability
 * Task 6: Batch confirmation dialogs
 *
 * Features:
 * - Summary of items to be approved
 * - Date range display for scheduled posts
 * - Preview thumbnails of first 3 items
 * - "Don't show again" checkbox for power users
 */

import React, { useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { ApprovalQueueItem } from "@/types/approval";

export interface BatchApproveConfirmDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Items to be approved */
  items: ApprovalQueueItem[];
  /** Callback when user confirms approval */
  onConfirm: () => Promise<void>;
  /** Callback when user cancels */
  onCancel: () => void;
  /** Whether batch operation is in progress */
  isLoading: boolean;
  /** Current state of "Don't show again" checkbox */
  dontShowAgain: boolean;
  /** Callback when "Don't show again" changes */
  onDontShowAgainChange: (checked: boolean) => void;
}

// Number of preview items to show
const PREVIEW_COUNT = 3;

/**
 * Format date range for display.
 */
function formatDateRange(dates: Date[]): string {
  if (dates.length === 0) return "No scheduled times";

  const sorted = [...dates].sort((a, b) => a.getTime() - b.getTime());
  const first = sorted[0];
  const last = sorted[sorted.length - 1];

  const formatOptions: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
  };

  if (sorted.length === 1) {
    return first.toLocaleDateString("en-US", formatOptions);
  }

  const firstStr = first.toLocaleDateString("en-US", formatOptions);
  const lastStr = last.toLocaleDateString("en-US", formatOptions);

  return `${firstStr} - ${lastStr}`;
}

/**
 * Batch approval confirmation dialog.
 *
 * Shows summary before executing batch approval action.
 */
export function BatchApproveConfirmDialog({
  isOpen,
  items,
  onConfirm,
  onCancel,
  isLoading,
  dontShowAgain,
  onDontShowAgainChange,
}: BatchApproveConfirmDialogProps): React.ReactElement | null {
  // Task 6.2: Calculate date range of scheduled posts
  const dateRange = useMemo(() => {
    const dates = items
      .map((item) => item.suggested_publish_time)
      .filter((time): time is string => time !== null)
      .map((time) => new Date(time));

    return formatDateRange(dates);
  }, [items]);

  // Task 6.3: Get preview items (first 3)
  const previewItems = useMemo(() => {
    return items.slice(0, PREVIEW_COUNT);
  }, [items]);

  const remainingCount = items.length - PREVIEW_COUNT;
  const itemCountLabel = items.length === 1 ? "1 item" : `${items.length} items`;

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Confirm Batch Approval</DialogTitle>
          <DialogDescription>
            You are about to approve {itemCountLabel} for publishing.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Task 6.2: Summary info */}
          <div className="rounded-lg bg-green-50 p-4 border border-green-200">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-green-800">
                {itemCountLabel} will be approved
              </span>
            </div>
            <p className="text-sm text-green-700">
              Scheduled for: <span className="font-medium">{dateRange}</span>
            </p>
          </div>

          {/* Task 6.3: Preview thumbnails */}
          <div className="space-y-3">
            <p className="text-sm font-medium text-gray-700">Preview:</p>
            <div className="space-y-2">
              {previewItems.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center gap-3 p-2 rounded-md bg-gray-50"
                >
                  <img
                    src={item.thumbnail_url}
                    alt={`Thumbnail for ${item.id}`}
                    className="w-12 h-12 rounded object-cover"
                  />
                  <span className="text-sm text-gray-600 truncate flex-1">
                    {item.caption_excerpt}
                  </span>
                </div>
              ))}

              {/* +N more indicator */}
              {remainingCount > 0 && (
                <p className="text-sm text-gray-500 text-center">
                  +{remainingCount} more item{remainingCount !== 1 ? "s" : ""}
                </p>
              )}
            </div>
          </div>

          {/* Task 6.6: Don't show again checkbox */}
          <div className="flex items-center gap-2 pt-2 border-t">
            <Checkbox
              id="dont-show-again"
              checked={dontShowAgain}
              onCheckedChange={(checked) =>
                onDontShowAgainChange(checked === true)
              }
              aria-label="Don't show this confirmation again"
            />
            <Label htmlFor="dont-show-again" className="text-sm text-gray-600">
              Don't show again for batch approvals
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            className="bg-green-600 hover:bg-green-700 text-white"
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Approving...
              </>
            ) : (
              `Approve ${itemCountLabel}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default BatchApproveConfirmDialog;
