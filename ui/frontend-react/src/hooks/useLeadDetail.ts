/**
 * useLeadDetail hook.
 *
 * Story 5-5, Task 7.3: Data fetching for single lead detail + history.
 * Uses SWR for caching and revalidation.
 */

import useSWR from "swr";
import { LeadDetail, LeadHistoryResponse } from "@/types/pipeline";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Lead not found");
    }
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export interface UseLeadDetailResult {
  lead: LeadDetail | null;
  isLoading: boolean;
  error: Error | null;
  refresh: () => void;
}

/**
 * Hook for fetching a single lead's full detail with activities.
 *
 * @param leadId - Lead UUID to fetch (null to skip fetching)
 */
export function useLeadDetail(leadId: string | null): UseLeadDetailResult {
  const {
    data: lead,
    error,
    isLoading,
    mutate,
  } = useSWR<LeadDetail>(
    leadId ? `${API_BASE}/pipeline/leads/${leadId}` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      errorRetryCount: 2,
    }
  );

  return {
    lead: lead ?? null,
    isLoading,
    error: error ?? null,
    refresh: () => mutate(),
  };
}

export default useLeadDetail;
