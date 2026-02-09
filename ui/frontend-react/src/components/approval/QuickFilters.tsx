/**
 * QuickFilters component.
 *
 * Story 4-3: Batch Approval Capability
 * Task 5: WOULD_AUTO_PUBLISH quick filter
 *
 * Features:
 * - "Select All High-Quality" button to select only would_auto_publish items
 * - "Approve All High-Quality" one-click action
 * - Count display for high-quality items
 * - Loading state handling
 */

import React, { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { ApprovalQueueItem } from "@/types/approval";

export interface QuickFiltersProps {
  /** All items in the queue */
  items: ApprovalQueueItem[];
  /** Callback when "Select All High-Quality" is clicked */
  onSelectWouldAutoPublish: () => void;
  /** Callback when "Approve All High-Quality" is clicked */
  onApproveAllHighQuality: () => void;
  /** Number of currently selected items */
  selectedCount: number;
  /** Whether a batch operation is in progress */
  isLoading: boolean;
}

/**
 * Quick filters for batch approval operations.
 *
 * Provides shortcuts to select and approve items that have been
 * automatically tagged as high-quality (would_auto_publish=true).
 */
export function QuickFilters({
  items,
  onSelectWouldAutoPublish,
  onApproveAllHighQuality,
  selectedCount,
  isLoading,
}: QuickFiltersProps): React.ReactElement {
  // Task 5.3: Count items with would_auto_publish=true
  const highQualityCount = useMemo(() => {
    return items.filter((item) => item.would_auto_publish).length;
  }, [items]);

  const hasHighQualityItems = highQualityCount > 0;

  // Task 5.2: Handle select all high-quality click
  const handleSelectHighQuality = () => {
    if (!isLoading && hasHighQualityItems) {
      onSelectWouldAutoPublish();
    }
  };

  // Task 5.5: Handle approve all high-quality click
  const handleApproveHighQuality = () => {
    if (!isLoading && hasHighQualityItems) {
      onApproveAllHighQuality();
    }
  };

  return (
    <div
      className="flex items-center justify-between p-3 bg-muted/50 rounded-lg mb-4"
      role="toolbar"
      aria-label="Quick filters"
    >
      {/* Left side: Filter info */}
      <div className="flex items-center gap-4">
        <span className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{highQualityCount}</span>{" "}
          high-quality items ready
        </span>

        {/* Task 5.4: Show selected count when items are selected */}
        {selectedCount > 0 && (
          <span className="text-sm font-medium text-blue-600">
            {selectedCount} selected
          </span>
        )}
      </div>

      {/* Right side: Action buttons */}
      <div className="flex items-center gap-2">
        {/* Task 5.2: Select All High-Quality button */}
        <Button
          variant="outline"
          size="sm"
          onClick={handleSelectHighQuality}
          disabled={!hasHighQualityItems || isLoading}
          aria-label={`Select all high-quality items (${highQualityCount})`}
        >
          Select All High-Quality ({highQualityCount})
        </Button>

        {/* Task 5.5: Approve All High-Quality one-click action */}
        <Button
          size="sm"
          className="bg-green-600 hover:bg-green-700 text-white"
          onClick={handleApproveHighQuality}
          disabled={!hasHighQualityItems || isLoading}
          aria-label={
            isLoading
              ? "Processing..."
              : `Approve all high-quality items (${highQualityCount})`
          }
        >
          {isLoading ? "Processing..." : `Approve All High-Quality (${highQualityCount})`}
        </Button>
      </div>
    </div>
  );
}

export default QuickFilters;
