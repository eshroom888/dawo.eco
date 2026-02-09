/**
 * useQueueSelection hook.
 *
 * Story 4-3: Batch Approval Capability
 * Task 1.2: Selection state management for batch operations.
 *
 * Manages selected item IDs with support for:
 * - Individual toggle selection
 * - Select all / Clear all
 * - Filter-based selection (e.g., WOULD_AUTO_PUBLISH items)
 * - Selection persistence across item updates
 */

import { useState, useCallback, useMemo, useEffect } from "react";
import { ApprovalQueueItem } from "@/types/approval";

/**
 * Return type for useQueueSelection hook.
 */
export interface UseQueueSelectionReturn {
  /** Set of selected item IDs */
  selectedIds: Set<string>;
  /** Number of selected items */
  selectedCount: number;
  /** Check if specific item is selected */
  isSelected: (id: string) => boolean;
  /** Toggle selection for a single item */
  toggleSelection: (id: string) => void;
  /** Select all items with given IDs */
  selectAll: (ids: string[]) => void;
  /** Clear all selections */
  clearSelection: () => void;
  /** Select items matching a predicate */
  selectByFilter: (predicate: (item: ApprovalQueueItem) => boolean) => void;
  /** Get array of selected item objects */
  getSelectedItems: () => ApprovalQueueItem[];
  /** True if all items are selected */
  isAllSelected: boolean;
  /** True if some (but not all) items are selected */
  isSomeSelected: boolean;
  /** Toggle between select all and clear all */
  toggleSelectAll: () => void;
}

/**
 * Hook for managing queue item selection state.
 *
 * @param items - Array of queue items available for selection
 * @returns Selection state and control functions
 *
 * @example
 * ```tsx
 * const {
 *   selectedIds,
 *   isSelected,
 *   toggleSelection,
 *   selectByFilter,
 *   clearSelection,
 * } = useQueueSelection(queueItems);
 *
 * // Select only high-quality items
 * selectByFilter((item) => item.would_auto_publish);
 * ```
 */
export function useQueueSelection(
  items: ApprovalQueueItem[]
): UseQueueSelectionReturn {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Task 1.5: Clean up selection when items are removed from list
  useEffect(() => {
    const currentItemIds = new Set(items.map((item) => item.id));

    setSelectedIds((prev) => {
      const validIds = new Set<string>();
      prev.forEach((id) => {
        if (currentItemIds.has(id)) {
          validIds.add(id);
        }
      });

      // Only update if there's a change
      if (validIds.size !== prev.size) {
        return validIds;
      }
      return prev;
    });
  }, [items]);

  /**
   * Check if an item is selected.
   */
  const isSelected = useCallback(
    (id: string): boolean => {
      return selectedIds.has(id);
    },
    [selectedIds]
  );

  /**
   * Toggle selection for a single item.
   */
  const toggleSelection = useCallback((id: string): void => {
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

  /**
   * Select all items with given IDs.
   */
  const selectAll = useCallback((ids: string[]): void => {
    setSelectedIds(new Set(ids));
  }, []);

  /**
   * Clear all selections.
   */
  const clearSelection = useCallback((): void => {
    setSelectedIds(new Set());
  }, []);

  /**
   * Select items matching a predicate function.
   * Replaces current selection with filtered results.
   */
  const selectByFilter = useCallback(
    (predicate: (item: ApprovalQueueItem) => boolean): void => {
      const matchingIds = items.filter(predicate).map((item) => item.id);
      setSelectedIds(new Set(matchingIds));
    },
    [items]
  );

  /**
   * Get array of selected item objects.
   */
  const getSelectedItems = useCallback((): ApprovalQueueItem[] => {
    return items.filter((item) => selectedIds.has(item.id));
  }, [items, selectedIds]);

  /**
   * Selected count for display.
   */
  const selectedCount = selectedIds.size;

  /**
   * Check if all items are selected.
   */
  const isAllSelected = useMemo(() => {
    return items.length > 0 && selectedIds.size === items.length;
  }, [items.length, selectedIds.size]);

  /**
   * Check if some (but not all) items are selected.
   * Used for indeterminate checkbox state.
   */
  const isSomeSelected = useMemo(() => {
    return selectedIds.size > 0 && selectedIds.size < items.length;
  }, [items.length, selectedIds.size]);

  /**
   * Toggle between select all and clear all.
   * If some or none selected, selects all.
   * If all selected, clears all.
   */
  const toggleSelectAll = useCallback((): void => {
    if (isAllSelected) {
      clearSelection();
    } else {
      selectAll(items.map((item) => item.id));
    }
  }, [isAllSelected, clearSelection, selectAll, items]);

  return {
    selectedIds,
    selectedCount,
    isSelected,
    toggleSelection,
    selectAll,
    clearSelection,
    selectByFilter,
    getSelectedItems,
    isAllSelected,
    isSomeSelected,
    toggleSelectAll,
  };
}

export default useQueueSelection;
