/**
 * useScheduleDrag hook.
 *
 * Story 4-4, Task 4.2: Drag state management for calendar rescheduling.
 *
 * Manages:
 * - Drag state (which item is being dragged)
 * - Drop target highlighting
 * - Conflict preview during drag
 * - Imminent post drag prevention
 * - Optimistic update on drop
 *
 * Usage:
 *   const { isDragging, dragItem, onDragStart, onDragEnd, canDrop } = useScheduleDrag({
 *     items,
 *     onReschedule,
 *   });
 */

import { useState, useCallback, useMemo } from "react";
import { ScheduledItem, ConflictInfo } from "@/types/schedule";

const IMMINENT_THRESHOLD_MS = 60 * 60 * 1000; // 1 hour
const CONFLICT_WARNING_THRESHOLD = 2;
const CONFLICT_CRITICAL_THRESHOLD = 3;

export interface UseScheduleDragOptions {
  /** All scheduled items for conflict detection */
  items: ScheduledItem[];
  /** Callback when item is rescheduled */
  onReschedule: (itemId: string, newTime: Date, force?: boolean) => Promise<void>;
  /** Optional callback for drag start */
  onDragStart?: (item: ScheduledItem) => void;
  /** Optional callback for drag end */
  onDragEnd?: (item: ScheduledItem, success: boolean) => void;
}

export interface DragConflictPreview {
  /** Whether there's a conflict at the target time */
  hasConflict: boolean;
  /** Severity of the conflict */
  severity: "warning" | "critical" | null;
  /** Number of posts at target hour */
  postsAtHour: number;
  /** IDs of conflicting posts */
  conflictingIds: string[];
}

export interface UseScheduleDragResult {
  /** Whether a drag is in progress */
  isDragging: boolean;
  /** The item currently being dragged */
  dragItem: ScheduledItem | null;
  /** Current drag target time (while hovering) */
  dragTargetTime: Date | null;
  /** Conflict preview for current drag target */
  conflictPreview: DragConflictPreview | null;
  /** Start dragging an item */
  onDragStart: (item: ScheduledItem) => void;
  /** Update drag target (while hovering) */
  onDragOver: (targetTime: Date) => void;
  /** End drag and execute reschedule */
  onDragEnd: (targetTime: Date | null) => Promise<void>;
  /** Cancel drag without rescheduling */
  onDragCancel: () => void;
  /** Check if an item can be dragged */
  canDrag: (item: ScheduledItem) => boolean;
  /** Check if drop is allowed at target time */
  canDrop: (targetTime: Date) => boolean;
  /** Whether currently processing a drop */
  isProcessing: boolean;
  /** Error from last drop attempt */
  dropError: Error | null;
}

/**
 * Hook for managing drag-and-drop rescheduling state.
 *
 * Story 4-4, Task 4.2: Drag state management hook.
 *
 * @param options - Configuration options
 * @returns Drag state and handlers
 */
export function useScheduleDrag({
  items,
  onReschedule,
  onDragStart: onDragStartCallback,
  onDragEnd: onDragEndCallback,
}: UseScheduleDragOptions): UseScheduleDragResult {
  // Drag state
  const [isDragging, setIsDragging] = useState(false);
  const [dragItem, setDragItem] = useState<ScheduledItem | null>(null);
  const [dragTargetTime, setDragTargetTime] = useState<Date | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [dropError, setDropError] = useState<Error | null>(null);

  // Build hour -> items map for conflict detection
  const itemsByHour = useMemo(() => {
    const map = new Map<string, ScheduledItem[]>();

    for (const item of items) {
      const time = new Date(item.scheduled_publish_time);
      const hourKey = `${time.toISOString().slice(0, 13)}:00:00.000Z`;

      if (!map.has(hourKey)) {
        map.set(hourKey, []);
      }
      map.get(hourKey)!.push(item);
    }

    return map;
  }, [items]);

  // Check if an item can be dragged (not imminent)
  const canDrag = useCallback((item: ScheduledItem): boolean => {
    if (item.is_imminent) {
      return false;
    }

    const publishTime = new Date(item.scheduled_publish_time);
    const now = new Date();
    const timeToPublish = publishTime.getTime() - now.getTime();

    // Cannot drag if within 1 hour of publish
    return timeToPublish > IMMINENT_THRESHOLD_MS;
  }, []);

  // Get conflict preview for a target time
  const getConflictPreview = useCallback(
    (targetTime: Date, excludeId?: string): DragConflictPreview => {
      const hourKey = `${targetTime.toISOString().slice(0, 13)}:00:00.000Z`;
      const itemsAtHour = itemsByHour.get(hourKey) ?? [];

      // Exclude the item being dragged
      const otherItems = excludeId
        ? itemsAtHour.filter((i) => i.id !== excludeId)
        : itemsAtHour;

      // Count would be other items + the dragged item
      const postsAtHour = otherItems.length + 1;

      let hasConflict = false;
      let severity: "warning" | "critical" | null = null;

      if (postsAtHour >= CONFLICT_CRITICAL_THRESHOLD) {
        hasConflict = true;
        severity = "critical";
      } else if (postsAtHour >= CONFLICT_WARNING_THRESHOLD) {
        hasConflict = true;
        severity = "warning";
      }

      return {
        hasConflict,
        severity,
        postsAtHour,
        conflictingIds: otherItems.map((i) => i.id),
      };
    },
    [itemsByHour]
  );

  // Conflict preview for current drag target
  const conflictPreview = useMemo((): DragConflictPreview | null => {
    if (!isDragging || !dragTargetTime || !dragItem) {
      return null;
    }
    return getConflictPreview(dragTargetTime, dragItem.id);
  }, [isDragging, dragTargetTime, dragItem, getConflictPreview]);

  // Check if drop is allowed at target time
  const canDrop = useCallback(
    (targetTime: Date): boolean => {
      // Cannot drop in the past
      if (targetTime < new Date()) {
        return false;
      }

      // Cannot drop within 1 hour of now (imminent threshold)
      const timeFromNow = targetTime.getTime() - Date.now();
      if (timeFromNow < IMMINENT_THRESHOLD_MS) {
        return false;
      }

      return true;
    },
    []
  );

  // Start dragging
  const onDragStart = useCallback(
    (item: ScheduledItem) => {
      if (!canDrag(item)) {
        return;
      }

      setIsDragging(true);
      setDragItem(item);
      setDragTargetTime(null);
      setDropError(null);

      onDragStartCallback?.(item);
    },
    [canDrag, onDragStartCallback]
  );

  // Update drag target while hovering
  const onDragOver = useCallback((targetTime: Date) => {
    setDragTargetTime(targetTime);
  }, []);

  // Cancel drag
  const onDragCancel = useCallback(() => {
    if (dragItem) {
      onDragEndCallback?.(dragItem, false);
    }

    setIsDragging(false);
    setDragItem(null);
    setDragTargetTime(null);
  }, [dragItem, onDragEndCallback]);

  // End drag and execute reschedule
  const onDragEnd = useCallback(
    async (targetTime: Date | null) => {
      if (!dragItem || !targetTime) {
        onDragCancel();
        return;
      }

      if (!canDrop(targetTime)) {
        setDropError(new Error("Cannot drop at this time"));
        onDragCancel();
        return;
      }

      setIsProcessing(true);
      setDropError(null);

      try {
        await onReschedule(dragItem.id, targetTime);
        onDragEndCallback?.(dragItem, true);
      } catch (error) {
        setDropError(error instanceof Error ? error : new Error("Reschedule failed"));
        onDragEndCallback?.(dragItem, false);
      } finally {
        setIsProcessing(false);
        setIsDragging(false);
        setDragItem(null);
        setDragTargetTime(null);
      }
    },
    [dragItem, canDrop, onReschedule, onDragCancel, onDragEndCallback]
  );

  return {
    isDragging,
    dragItem,
    dragTargetTime,
    conflictPreview,
    onDragStart,
    onDragOver,
    onDragEnd,
    onDragCancel,
    canDrag,
    canDrop,
    isProcessing,
    dropError,
  };
}

export default useScheduleDrag;
