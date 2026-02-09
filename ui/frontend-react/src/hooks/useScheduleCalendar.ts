/**
 * useScheduleCalendar hook.
 *
 * Story 4-4, Task 9: Data fetching hook for the scheduling calendar with SWR.
 * Provides automatic refresh, loading states, reschedule mutations, and
 * optimistic updates.
 *
 * Features:
 * - SWR-based data fetching with automatic refresh
 * - Date range state management
 * - Reschedule mutation with optimistic update
 * - Conflict detection integration
 * - Real-time updates via revalidation
 */

import useSWR, { mutate } from "swr";
import { useState, useCallback, useMemo } from "react";
import {
  ScheduledItem,
  ScheduleCalendarResponse,
  ConflictInfo,
  RescheduleResponse,
  CalendarView,
} from "@/types/schedule";
import { startOfWeek, endOfWeek, startOfMonth, endOfMonth, addWeeks, subWeeks, addMonths, subMonths, formatISO } from "date-fns";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const REFRESH_INTERVAL = 30000; // 30 seconds

/**
 * Fetch function for SWR.
 */
async function fetcher(url: string): Promise<ScheduleCalendarResponse> {
  const response = await fetch(url);
  if (!response.ok) {
    const error = new Error("Failed to fetch schedule calendar");
    throw error;
  }
  return response.json();
}

export interface DateRange {
  start: Date;
  end: Date;
}

export interface UseScheduleCalendarResult {
  /** Scheduled items for current date range */
  items: ScheduledItem[];
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: Error | null;
  /** Current date range */
  dateRange: DateRange;
  /** Current calendar view */
  view: CalendarView;
  /** Set date range */
  setDateRange: (range: DateRange) => void;
  /** Set calendar view */
  setView: (view: CalendarView) => void;
  /** Navigate to previous period */
  navigatePrevious: () => void;
  /** Navigate to next period */
  navigateNext: () => void;
  /** Navigate to today */
  navigateToday: () => void;
  /** Reschedule an item */
  reschedule: (itemId: string, newTime: Date, force?: boolean) => Promise<RescheduleResponse>;
  /** Detected conflicts */
  conflicts: ConflictInfo[];
  /** Refresh data */
  refresh: () => Promise<ScheduleCalendarResponse | undefined>;
}

/**
 * Hook for managing scheduling calendar data.
 *
 * Story 4-4, Task 9.1: Create useScheduleCalendar hook with SWR fetching.
 *
 * @param initialView - Initial calendar view (default: "week")
 * @returns Calendar data, navigation, and reschedule utilities
 */
export function useScheduleCalendar(
  initialView: CalendarView = "week"
): UseScheduleCalendarResult {
  // Story 4-4, Task 9.2: Date range state and navigation
  const [view, setView] = useState<CalendarView>(initialView);
  const [currentDate, setCurrentDate] = useState<Date>(new Date());

  // Calculate date range based on view
  const dateRange = useMemo((): DateRange => {
    switch (view) {
      case "day":
        return { start: currentDate, end: currentDate };
      case "week":
        return {
          start: startOfWeek(currentDate, { weekStartsOn: 1 }),
          end: endOfWeek(currentDate, { weekStartsOn: 1 }),
        };
      case "month":
        return {
          start: startOfMonth(currentDate),
          end: endOfMonth(currentDate),
        };
      default:
        return {
          start: startOfWeek(currentDate, { weekStartsOn: 1 }),
          end: endOfWeek(currentDate, { weekStartsOn: 1 }),
        };
    }
  }, [view, currentDate]);

  // Build API URL with date range
  const apiUrl = useMemo(() => {
    const params = new URLSearchParams({
      start_date: formatISO(dateRange.start, { representation: "date" }),
      end_date: formatISO(dateRange.end, { representation: "date" }),
    });
    return `${API_BASE}/schedule/calendar?${params.toString()}`;
  }, [dateRange]);

  // SWR fetch
  const { data, error, isLoading, mutate: swrMutate } = useSWR<ScheduleCalendarResponse>(
    apiUrl,
    fetcher,
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
      errorRetryCount: 3,
      errorRetryInterval: 5000,
    }
  );

  // Navigation handlers
  const navigatePrevious = useCallback(() => {
    setCurrentDate((prev) => {
      switch (view) {
        case "day":
          return new Date(prev.getTime() - 24 * 60 * 60 * 1000);
        case "week":
          return subWeeks(prev, 1);
        case "month":
          return subMonths(prev, 1);
        default:
          return subWeeks(prev, 1);
      }
    });
  }, [view]);

  const navigateNext = useCallback(() => {
    setCurrentDate((prev) => {
      switch (view) {
        case "day":
          return new Date(prev.getTime() + 24 * 60 * 60 * 1000);
        case "week":
          return addWeeks(prev, 1);
        case "month":
          return addMonths(prev, 1);
        default:
          return addWeeks(prev, 1);
      }
    });
  }, [view]);

  const navigateToday = useCallback(() => {
    setCurrentDate(new Date());
  }, []);

  const setDateRange = useCallback((range: DateRange) => {
    setCurrentDate(range.start);
  }, []);

  // Story 4-4, Task 9.3: Reschedule mutation with optimistic updates
  const reschedule = useCallback(
    async (itemId: string, newTime: Date, force: boolean = false): Promise<RescheduleResponse> => {
      // Optimistic update
      const optimisticData: ScheduleCalendarResponse | undefined = data
        ? {
            ...data,
            items: data.items.map((item) =>
              item.id === itemId
                ? { ...item, scheduled_publish_time: newTime.toISOString() }
                : item
            ),
          }
        : undefined;

      // Update cache optimistically
      if (optimisticData) {
        await swrMutate(optimisticData, false);
      }

      try {
        const response = await fetch(
          `${API_BASE}/schedule/${itemId}/reschedule`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              new_publish_time: newTime.toISOString(),
              force,
            }),
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Reschedule failed");
        }

        const result: RescheduleResponse = await response.json();

        // Revalidate to get fresh data
        await swrMutate();

        return result;
      } catch (error) {
        // Rollback on error
        await swrMutate();
        throw error;
      }
    },
    [data, swrMutate]
  );

  return {
    items: data?.items ?? [],
    isLoading,
    error: error ?? null,
    dateRange,
    view,
    setDateRange,
    setView,
    navigatePrevious,
    navigateNext,
    navigateToday,
    reschedule,
    conflicts: data?.conflicts ?? [],
    refresh: swrMutate,
  };
}

export default useScheduleCalendar;
