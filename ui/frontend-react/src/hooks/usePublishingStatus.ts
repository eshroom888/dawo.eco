/**
 * usePublishingStatus hook.
 *
 * Story 4-4, Task 6.1: Track imminent posts and publishing status.
 *
 * Monitors scheduled items that are approaching their publish time
 * and provides countdown timers and lock status.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { ScheduledItem } from "@/types/schedule";

const IMMINENT_THRESHOLD_MS = 60 * 60 * 1000; // 1 hour
const LOCKED_THRESHOLD_MS = 30 * 60 * 1000; // 30 minutes
const UPDATE_INTERVAL_MS = 60 * 1000; // Update every minute

export interface ImminentItem {
  /** Item data */
  item: ScheduledItem;
  /** Milliseconds until publish */
  msUntilPublish: number;
  /** Minutes until publish (rounded) */
  minutesUntilPublish: number;
  /** Whether editing is locked */
  isLocked: boolean;
  /** Whether item is publishing soon (< 1 hour) */
  isImminent: boolean;
}

export interface UsePublishingStatusResult {
  /** Items that are imminent (< 1 hour) */
  imminentItems: ImminentItem[];
  /** Check if a specific item is imminent */
  isItemImminent: (itemId: string) => boolean;
  /** Check if a specific item is locked for editing */
  isItemLocked: (itemId: string) => boolean;
  /** Get minutes until publish for an item */
  getMinutesUntilPublish: (itemId: string) => number | null;
}

/**
 * Hook for tracking publishing status of scheduled items.
 *
 * Story 4-4, Task 6.1: usePublishingStatus hook to track imminent posts.
 *
 * @param items - Scheduled items to monitor
 * @returns Publishing status information and utilities
 */
export function usePublishingStatus(
  items: ScheduledItem[]
): UsePublishingStatusResult {
  const [now, setNow] = useState(() => Date.now());

  // Update "now" periodically to refresh countdowns
  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now());
    }, UPDATE_INTERVAL_MS);

    return () => clearInterval(interval);
  }, []);

  // Calculate imminent items
  const imminentItems = useMemo((): ImminentItem[] => {
    const result: ImminentItem[] = [];

    for (const item of items) {
      if (!item.scheduled_publish_time) continue;

      const publishTime = new Date(item.scheduled_publish_time).getTime();
      const msUntilPublish = publishTime - now;

      // Only include items within 1 hour
      if (msUntilPublish > 0 && msUntilPublish <= IMMINENT_THRESHOLD_MS) {
        result.push({
          item,
          msUntilPublish,
          minutesUntilPublish: Math.ceil(msUntilPublish / 60000),
          isLocked: msUntilPublish <= LOCKED_THRESHOLD_MS,
          isImminent: true,
        });
      }
    }

    // Sort by closest to publish
    result.sort((a, b) => a.msUntilPublish - b.msUntilPublish);

    return result;
  }, [items, now]);

  // Build lookup map for fast access
  const imminentMap = useMemo(() => {
    const map = new Map<string, ImminentItem>();
    for (const item of imminentItems) {
      map.set(item.item.id, item);
    }
    return map;
  }, [imminentItems]);

  const isItemImminent = useCallback(
    (itemId: string): boolean => {
      return imminentMap.has(itemId);
    },
    [imminentMap]
  );

  const isItemLocked = useCallback(
    (itemId: string): boolean => {
      const item = imminentMap.get(itemId);
      return item?.isLocked ?? false;
    },
    [imminentMap]
  );

  const getMinutesUntilPublish = useCallback(
    (itemId: string): number | null => {
      const item = imminentMap.get(itemId);
      return item?.minutesUntilPublish ?? null;
    },
    [imminentMap]
  );

  return {
    imminentItems,
    isItemImminent,
    isItemLocked,
    getMinutesUntilPublish,
  };
}

export default usePublishingStatus;
