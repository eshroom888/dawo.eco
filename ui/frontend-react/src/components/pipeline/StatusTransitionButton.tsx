/**
 * StatusTransitionButton component.
 *
 * Story 5-5, Task 8.7: Dropdown showing valid next statuses for a lead.
 * Includes optional reason input for status changes.
 */

import React, { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { VALID_TRANSITIONS, STATUS_CONFIGS, LeadStatus } from "@/types/pipeline";

export interface StatusTransitionButtonProps {
  currentStatus: string;
  onTransition: (newStatus: string, reason?: string) => Promise<void>;
  isLoading?: boolean;
  className?: string;
}

/**
 * Button with dropdown for manual status transitions.
 */
export function StatusTransitionButton({
  currentStatus,
  onTransition,
  isLoading = false,
  className,
}: StatusTransitionButtonProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false);
  const [showReasonInput, setShowReasonInput] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  const validNextStatuses = VALID_TRANSITIONS[currentStatus] ?? [];

  const handleSelect = useCallback(
    (status: string) => {
      // Lost and Nurture transitions benefit from a reason
      if (status === LeadStatus.LOST || status === LeadStatus.NURTURE) {
        setShowReasonInput(status);
        return;
      }
      onTransition(status);
      setIsOpen(false);
    },
    [onTransition]
  );

  const handleSubmitWithReason = useCallback(async () => {
    if (showReasonInput) {
      await onTransition(showReasonInput, reason || undefined);
      setShowReasonInput(null);
      setReason("");
      setIsOpen(false);
    }
  }, [showReasonInput, reason, onTransition]);

  if (validNextStatuses.length === 0) {
    return (
      <span className="text-xs text-gray-400 italic">No transitions available</span>
    );
  }

  return (
    <div className={cn("relative", className)}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
      >
        {isLoading ? "Updating..." : "Change Status"}
      </Button>

      {isOpen && (
        <div className="absolute top-full mt-1 left-0 bg-white border rounded-md shadow-lg z-10 min-w-[200px]">
          {showReasonInput ? (
            <div className="p-3">
              <p className="text-xs text-gray-500 mb-2">
                Reason for changing to{" "}
                <strong>
                  {STATUS_CONFIGS[showReasonInput as LeadStatus]?.label ?? showReasonInput}
                </strong>
                :
              </p>
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Optional reason..."
                className="w-full px-2 py-1 border rounded text-sm mb-2"
                autoFocus
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={handleSubmitWithReason} disabled={isLoading}>
                  Confirm
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setShowReasonInput(null);
                    setReason("");
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="py-1">
              {validNextStatuses.map((status) => {
                const config = STATUS_CONFIGS[status as LeadStatus];
                return (
                  <button
                    key={status}
                    onClick={() => handleSelect(status)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center gap-2"
                  >
                    <span
                      className={cn(
                        "px-2 py-0.5 rounded-full text-xs",
                        config?.bgColor ?? "bg-gray-100",
                        config?.color ?? "text-gray-700"
                      )}
                    >
                      {config?.label ?? status}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Click-outside handler */}
      {isOpen && (
        <div
          className="fixed inset-0 z-0"
          onClick={() => {
            setIsOpen(false);
            setShowReasonInput(null);
            setReason("");
          }}
        />
      )}
    </div>
  );
}

export default StatusTransitionButton;
