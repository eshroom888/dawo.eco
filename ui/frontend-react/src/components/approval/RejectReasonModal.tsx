/**
 * RejectReasonModal component.
 *
 * Dialog for selecting a rejection reason when rejecting content.
 * Requires reason selection from dropdown + optional text for details.
 *
 * Features:
 * - Predefined reason dropdown
 * - Required text field when "Other" is selected
 * - Character count for reason text
 * - Validation before submission
 */

import React, { useState, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import {
  RejectReason,
  RejectActionRequest,
  REJECT_REASON_LABELS,
} from "@/types/approval";

export interface RejectReasonModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (request: RejectActionRequest) => Promise<void>;
  isLoading?: boolean;
}

const MAX_REASON_TEXT_LENGTH = 500;

/**
 * Modal for collecting rejection reason.
 */
export function RejectReasonModal({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
}: RejectReasonModalProps): React.ReactElement {
  const [reason, setReason] = useState<RejectReason | "">("");
  const [reasonText, setReasonText] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal closes
  const handleClose = useCallback(() => {
    setReason("");
    setReasonText("");
    setError(null);
    onClose();
  }, [onClose]);

  // Validate and submit
  const handleSubmit = useCallback(async () => {
    setError(null);

    // Validate reason is selected
    if (!reason) {
      setError("Please select a rejection reason");
      return;
    }

    // Validate reason_text when OTHER is selected
    if (reason === RejectReason.OTHER && !reasonText.trim()) {
      setError("Please provide details when selecting 'Other'");
      return;
    }

    try {
      await onSubmit({
        reason: reason as RejectReason,
        reason_text: reasonText.trim() || null,
      });
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject content");
    }
  }, [reason, reasonText, onSubmit, handleClose]);

  const isOtherSelected = reason === RejectReason.OTHER;
  const canSubmit = reason && (!isOtherSelected || reasonText.trim());

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Reject Content</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Reason Dropdown */}
          <div className="space-y-2">
            <Label htmlFor="reject-reason">Rejection Reason *</Label>
            <Select
              value={reason}
              onValueChange={(value) => setReason(value as RejectReason)}
              disabled={isLoading}
            >
              <SelectTrigger id="reject-reason" aria-label="Select rejection reason">
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

          {/* Reason Text */}
          <div className="space-y-2">
            <Label htmlFor="reject-reason-text">
              Additional Details {isOtherSelected && "*"}
            </Label>
            <Textarea
              id="reject-reason-text"
              value={reasonText}
              onChange={(e) => setReasonText(e.target.value)}
              placeholder={
                isOtherSelected
                  ? "Please describe the reason for rejection..."
                  : "Optional additional details..."
              }
              maxLength={MAX_REASON_TEXT_LENGTH}
              disabled={isLoading}
              className="min-h-[100px]"
              aria-describedby="reason-text-count"
            />
            <p
              id="reason-text-count"
              className="text-xs text-gray-500 text-right"
            >
              {reasonText.length}/{MAX_REASON_TEXT_LENGTH}
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleSubmit}
            disabled={!canSubmit || isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Rejecting...
              </>
            ) : (
              "Reject Content"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default RejectReasonModal;
