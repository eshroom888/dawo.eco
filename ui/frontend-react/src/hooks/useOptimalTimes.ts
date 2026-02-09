/**
 * useOptimalTimes hook.
 *
 * Story 4-4, Task 9.4: Fetch optimal time suggestions for scheduling.
 *
 * Provides suggested publish times based on:
 * - Instagram peak engagement hours
 * - Existing scheduled posts (conflict avoidance)
 * - Historical engagement data (future Epic 7)
 */

import useSWR from "swr";
import { useMemo } from "react";
import { OptimalTimesResponse, OptimalTimeSlot } from "@/types/schedule";
import { formatISO } from "date-fns";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

/**
 * Fetch function for optimal times API.
 */
async function fetcher(url: string): Promise<OptimalTimesResponse> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Failed to fetch optimal times");
  }
  return response.json();
}

export interface UseOptimalTimesResult {
  /** Suggested time slots */
  suggestions: OptimalTimeSlot[];
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: Error | null;
  /** Refresh suggestions */
  refresh: () => Promise<OptimalTimesResponse | undefined>;
}

/**
 * Hook for fetching optimal publish time suggestions.
 *
 * @param targetDate - Date to get suggestions for
 * @param itemId - Optional item being scheduled
 * @returns Optimal time suggestions and utilities
 */
export function useOptimalTimes(
  targetDate: Date,
  itemId?: string
): UseOptimalTimesResult {
  const apiUrl = useMemo(() => {
    const params = new URLSearchParams({
      target_date: formatISO(targetDate, { representation: "date" }),
    });
    if (itemId) {
      params.set("item_id", itemId);
    }
    return `${API_BASE}/schedule/optimal-times?${params.toString()}`;
  }, [targetDate, itemId]);

  const { data, error, isLoading, mutate } = useSWR<OptimalTimesResponse>(
    apiUrl,
    fetcher,
    {
      revalidateOnFocus: false,
      errorRetryCount: 2,
    }
  );

  return {
    suggestions: data?.suggestions ?? [],
    isLoading,
    error: error ?? null,
    refresh: mutate,
  };
}

export default useOptimalTimes;
