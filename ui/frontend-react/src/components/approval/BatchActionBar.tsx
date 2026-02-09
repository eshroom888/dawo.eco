/**
 * BatchActionBar component.
 *
 * Story 4-3: Batch Approval Capability
 * Task 2: Sticky action bar that appears when items are selected.
 *
 * Features:
 * - Fixed positioning at bottom of viewport
 * - Displays selected count
 * - Approve All / Reject All / Clear buttons
 * - Keyboard shortcuts (Shift+A, Shift+R)
 * - Loading state during batch operations
 */

import React, { useEffect } from "react";
import { Button } from "@/components/ui/button";

export interface BatchActionBarProps {
  /** Number of items currently selected */
  selectedCount: number;
  /** Callback when Approve All is clicked */
  onApproveAll: () => void;
  /** Callback when Reject All is clicked */
  onRejectAll: () => void;
  /** Callback when Clear Selection is clicked */
  onClearSelection: () => void;
  /** Whether a batch operation is in progress */
  isLoading: boolean;
}

/**
 * Batch action bar for approval queue.
 *
 * Appears at the bottom of the screen when items are selected,
 * providing quick access to batch approve/reject actions.
 */
export function BatchActionBar({
  selectedCount,
  onApproveAll,
  onRejectAll,
  onClearSelection,
  isLoading,
}: BatchActionBarProps): React.ReactElement | null {
  // Task 2.8: Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle shortcuts when bar is visible and not loading
      if (selectedCount === 0 || isLoading) return;

      // Require Shift modifier
      if (!e.shiftKey) return;

      switch (e.key.toLowerCase()) {
        case "a":
          e.preventDefault();
          onApproveAll();
          break;
        case "r":
          e.preventDefault();
          onRejectAll();
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [selectedCount, isLoading, onApproveAll, onRejectAll]);

  // Task 2.1: Don't render if nothing selected
  if (selectedCount === 0) {
    return null;
  }

  return (
    <div
      className="fixed bottom-0 left-0 right-0 bg-background border-t shadow-lg p-4 flex items-center justify-between z-50 animate-in slide-in-from-bottom-4 duration-200"
      role="toolbar"
      aria-label="Batch actions"
    >
      {/* Left side: Selected count and clear */}
      <div className="flex items-center gap-4">
        {/* Task 2.3: Selected count display */}
        <span className="font-medium text-foreground">
          {selectedCount} item{selectedCount !== 1 ? "s" : ""} selected
        </span>

        {/* Task 2.6: Clear Selection button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onClearSelection}
          aria-label="Clear selection"
        >
          Clear
        </Button>
      </div>

      {/* Right side: Action buttons */}
      <div className="flex items-center gap-2">
        {/* Keyboard shortcut hints */}
        <span className="hidden sm:inline text-xs text-muted-foreground mr-2">
          Shift+A: Approve | Shift+R: Reject
        </span>

        {/* Task 2.5: Reject All button */}
        <Button
          variant="outline"
          className="border-red-500 text-red-600 hover:bg-red-50"
          onClick={onRejectAll}
          disabled={isLoading}
          aria-label="Reject All"
        >
          Reject All
        </Button>

        {/* Task 2.4: Approve All button */}
        <Button
          className="bg-green-600 hover:bg-green-700 text-white"
          onClick={onApproveAll}
          disabled={isLoading}
          aria-label={isLoading ? "Processing..." : "Approve All"}
        >
          {isLoading ? "Processing..." : "Approve All"}
        </Button>
      </div>
    </div>
  );
}

export default BatchActionBar;
