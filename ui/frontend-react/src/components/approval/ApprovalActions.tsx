/**
 * ApprovalActions component.
 *
 * Provides Approve, Reject, and Edit action buttons for approval items.
 * Supports loading states, keyboard shortcuts, and accessibility.
 *
 * Features:
 * - Color-coded buttons (green/red/blue)
 * - Loading spinners per action
 * - Keyboard shortcuts (A/R/E)
 * - aria-labels for accessibility
 */

import React, { useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Loader2, Check, X, Pencil } from "lucide-react";
import { ApprovalActionType } from "@/types/approval";

export interface ApprovalActionsProps {
  onApprove: () => void;
  onReject: () => void;
  onEdit: () => void;
  isLoading?: boolean;
  loadingAction?: ApprovalActionType | null;
  isEditing?: boolean;
  enableKeyboardShortcuts?: boolean;
  className?: string;
}

/**
 * Action buttons for approval workflow.
 */
export function ApprovalActions({
  onApprove,
  onReject,
  onEdit,
  isLoading = false,
  loadingAction = null,
  isEditing = false,
  enableKeyboardShortcuts = false,
  className = "",
}: ApprovalActionsProps): React.ReactElement | null {
  // Keyboard shortcuts handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Skip if editing, loading, or modifier keys pressed
      if (isEditing || isLoading) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      switch (e.key.toLowerCase()) {
        case "a":
          e.preventDefault();
          onApprove();
          break;
        case "r":
          e.preventDefault();
          onReject();
          break;
        case "e":
          e.preventDefault();
          onEdit();
          break;
      }
    },
    [isEditing, isLoading, onApprove, onReject, onEdit]
  );

  useEffect(() => {
    if (!enableKeyboardShortcuts) return;

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [enableKeyboardShortcuts, handleKeyDown]);

  // Hide buttons when in edit mode
  if (isEditing) {
    return null;
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Approve Button */}
      <Button
        onClick={onApprove}
        disabled={isLoading}
        className="bg-green-600 hover:bg-green-700 text-white"
        aria-label="Approve content"
      >
        {loadingAction === "approve" ? (
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        ) : (
          <Check className="h-4 w-4 mr-2" />
        )}
        Approve
        <span className="ml-1 text-xs opacity-70">(A)</span>
      </Button>

      {/* Reject Button */}
      <Button
        onClick={onReject}
        disabled={isLoading}
        className="bg-red-600 hover:bg-red-700 text-white"
        aria-label="Reject content"
      >
        {loadingAction === "reject" ? (
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        ) : (
          <X className="h-4 w-4 mr-2" />
        )}
        Reject
        <span className="ml-1 text-xs opacity-70">(R)</span>
      </Button>

      {/* Edit Button */}
      <Button
        onClick={onEdit}
        disabled={isLoading}
        className="bg-blue-600 hover:bg-blue-700 text-white"
        aria-label="Edit content"
      >
        {loadingAction === "edit" ? (
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        ) : (
          <Pencil className="h-4 w-4 mr-2" />
        )}
        Edit
        <span className="ml-1 text-xs opacity-70">(E)</span>
      </Button>
    </div>
  );
}

export default ApprovalActions;
