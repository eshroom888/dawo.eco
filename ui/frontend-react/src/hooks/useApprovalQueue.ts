/**
 * useApprovalQueue hook.
 *
 * Data fetching hook for the approval queue with SWR.
 * Provides automatic refresh, loading states, and error handling.
 *
 * Features:
 * - Auto-refresh every 30 seconds
 * - Revalidate on focus
 * - Error handling with retry
 * - Pagination support
 */

import useSWR from "swr";
import { ApprovalQueueResponse, ApprovalQueueItem } from "@/types/approval";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const REFRESH_INTERVAL = 30000; // 30 seconds

/**
 * Fetch function for SWR.
 */
async function fetcher(url: string): Promise<ApprovalQueueResponse> {
  const startTime = performance.now();

  const response = await fetch(url);
  if (!response.ok) {
    const error = new Error("Failed to fetch approval queue");
    throw error;
  }

  const data = await response.json();

  // Log performance for < 3s target
  const loadTime = performance.now() - startTime;
  if (loadTime > 3000) {
    console.warn(`Approval queue load time exceeded target: ${loadTime}ms`);
  }

  return data;
}

export interface UseApprovalQueueResult {
  items: ApprovalQueueItem[];
  totalCount: number;
  isLoading: boolean;
  error: Error | undefined;
  refresh: () => Promise<ApprovalQueueResponse | undefined>;
  hasMore: boolean;
  nextCursor: string | null;
}

/**
 * Hook for fetching and managing approval queue data.
 *
 * @param limit - Maximum number of items to fetch (default: 50)
 * @param cursor - Pagination cursor for fetching next page
 * @returns Queue data, loading state, and utilities
 */
export function useApprovalQueue(
  limit: number = 50,
  cursor?: string
): UseApprovalQueueResult {
  const queryParams = new URLSearchParams();
  queryParams.set("limit", limit.toString());
  if (cursor) {
    queryParams.set("cursor", cursor);
  }

  const url = `${API_BASE}/approval-queue?${queryParams.toString()}`;

  const { data, error, isLoading, mutate } = useSWR<ApprovalQueueResponse>(
    url,
    fetcher,
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
      errorRetryCount: 3,
      errorRetryInterval: 5000,
    }
  );

  return {
    items: data?.items ?? [],
    totalCount: data?.total_count ?? 0,
    isLoading,
    error,
    refresh: mutate,
    hasMore: data?.has_more ?? false,
    nextCursor: data?.next_cursor ?? null,
  };
}

export default useApprovalQueue;
