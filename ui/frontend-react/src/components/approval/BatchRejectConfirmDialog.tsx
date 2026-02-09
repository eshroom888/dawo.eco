/**
 * BatchRejectConfirmDialog component.
 *
 * Story 4-3: Batch Approval Capability
 * Task 6: Batch confirmation dialogs
 *
 * Features:
 * - Requires rejection reason selection
 * - Uses RejectReason enum from Story 4-2
 * - Optional text for additional details
 * - "Don't show again" checkbox for power users
 */

import React, { useState, useCallback } from "react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Loader2 } from "lucide-react";
import {
  ApprovalQueueItem,
  RejectReason,
  RejectActionRequest,
  REJECT_REASON_LABELS,
} from "@/types/approval";

export interface BatchRejectConfirmDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Items to be rejected */
  items: ApprovalQueueItem[];
  /** Callback when user confirms rejection with reason */
  onConfirm: (request: RejectActionRequest) => Promise<void>;
  /** Callback when user cancels */
  onCancel: () => void;
  /** Whether batch operation is in progress */
  isLoading: boolean;
  /** Current state of "Don't show again" checkbox */
  dontShowAgain: boolean;
  /** Callback when "Don't show again" changes */
  onDontShowAgainChange: (checked: boolean) => void;
}

const MAX_REASON_TEXT_LENGTH = 500;

/**
 * Batch rejection confirmation dialog.
 *
 * Requires reason selection before batch rejection.
 */
export function BatchRejectConfirmDialog({
  isOpen,
  items,
  onConfirm,
  onCancel,
  isLoading,
  dontShowAgain,
  onDontShowAgainChange,
}: BatchRejectConfirmDialogProps): React.ReactElement | null {
  const [reason, setReason] = useState<RejectReason | "">("");
  const [reasonText, setReasonText] = useState("");

  const itemCountLabel = items.length === 1 ? "1 item" : `${items.length} items`;
  const isOtherSelected = reason === RejectReason.OTHER;
  const canSubmit = reason && (!isOtherSelected || reasonText.trim());

  // Reset form and close
  const handleClose = useCallback(() => {
    setReason("");
    setReasonText("");
    onCancel();
  }, [onCancel]);

  // Submit rejection
  const handleConfirm = useCallback(async () => {
    if (!reason) return;

    await onConfirm({
      reason: reason as RejectReason,
      reason_text: reasonText.trim() || null,
    });

    // Reset form on success
    setReason("");
    setReasonText("");
  }, [reason, reasonText, onConfirm]);

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Confirm Batch Rejection</DialogTitle>
          <DialogDescription>
            You are about to reject {itemCountLabel}. This action cannot be undone.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Warning banner */}
          <div className="rounded-lg bg-red-50 p-4 border border-red-200">
            <p className="text-sm font-medium text-red-800">
              {itemCountLabel} will be rejected
            </p>
            <p className="text-sm text-red-700 mt-1">
              The same rejection reason will be applied to all selected items.
            </p>
          </div>

          {/* Task 6.5: Rejection reason dropdown */}
          <div className="space-y-2">
            <Label htmlFor="batch-reject-reason">Rejection Reason *</Label>
            <Select
              value={reason}
              onValueChange={(value) => setReason(value as RejectReason)}
              disabled={isLoading}
            >
              <SelectTrigger
                id="batch-reject-reason"
                aria-label="Select rejection reason"
              >
                <SelectValue placeholder="Select a reason..." />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(REJECT_REASON_LABELS).map(([key, label]) => (
                  <SelectItem key={key} value={key}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Reason text (required for OTHER) */}
          {isOtherSelected && (
            <div className="space-y-2">
              <Label htmlFor="batch-reject-reason-text">
                Please describe the reason *
              </Label>
              <Textarea
                id="batch-reject-reason-text"
                value={reasonText}
                onChange={(e) => setReasonText(e.target.value)}
                placeholder="Describe the reason for rejection..."
                maxLength={MAX_REASON_TEXT_LENGTH}
                disabled={isLoading}
                className="min-h-[80px]"
              />
              <p className="text-xs text-gray-500 text-right">
                {reasonText.length}/{MAX_REASON_TEXT_LENGTH}
              </p>
            </div>
          )}

          {/* Task 6.6: Don't show again checkbox */}
          <div className="flex items-center gap-2 pt-2 border-t">
            <Checkbox
              id="batch-reject-dont-show"
              checked={dontShowAgain}
              onCheckedChange={(checked) =>
                onDontShowAgainChange(checked === true)
              }
              aria-label="Don't show this confirmation again"
            />
            <Label
              htmlFor="batch-reject-dont-show"
              className="text-sm text-gray-600"
            >
              Don't show again for batch rejections
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={!canSubmit || isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Rejecting...
              </>
            ) : (
              `Reject ${itemCountLabel}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default BatchRejectConfirmDialog;
