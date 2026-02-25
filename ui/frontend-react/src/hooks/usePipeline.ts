/**
 * usePipeline hook.
 *
 * Story 5-5, Task 7.2: Data fetching hook for the pipeline dashboard.
 * Provides summary, metrics, lead list, and follow-up data via SWR.
 */

import useSWR from "swr";
import { useState, useCallback, useMemo } from "react";
import {
  PipelineSummary,
  PipelineLeadListResponse,
  PipelineMetrics,
  PipelineLead,
  StatusUpdateResponse,
  LeadHistoryEntry,
} from "@/types/pipeline";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const REFRESH_INTERVAL = 30000;

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const error = new Error(`API error: ${response.status}`);
    throw error;
  }
  return response.json();
}

export interface PipelineFilters {
  status: string | null;
  search: string;
  sort: string;
  limit: number;
  offset: number;
}

export interface UsePipelineResult {
  summary: PipelineSummary | null;
  metrics: PipelineMetrics | null;
  leads: PipelineLead[];
  totalCount: number;
  hasMore: boolean;
  followups: PipelineLead[];
  isLoading: boolean;
  error: Error | null;
  filters: PipelineFilters;
  setFilters: (filters: Partial<PipelineFilters>) => void;
  updateLeadStatus: (leadId: string, newStatus: string, reason?: string) => Promise<StatusUpdateResponse>;
  addNote: (leadId: string, note: string) => Promise<LeadHistoryEntry>;
  exportCSV: (status?: string) => void;
  refresh: () => void;
}

/**
 * Hook for fetching and managing pipeline dashboard data.
 */
export function usePipeline(): UsePipelineResult {
  const [filters, setFiltersState] = useState<PipelineFilters>({
    status: null,
    search: "",
    sort: "score",
    limit: 25,
    offset: 0,
  });

  const setFilters = useCallback((update: Partial<PipelineFilters>) => {
    setFiltersState((prev) => ({
      ...prev,
      ...update,
      // Reset offset when filters change (except when explicitly setting offset)
      offset: "offset" in update ? (update.offset ?? 0) : 0,
    }));
  }, []);

  // Build leads URL with filters
  const leadsUrl = useMemo(() => {
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.search) params.set("search", filters.search);
    params.set("sort", filters.sort);
    params.set("limit", filters.limit.toString());
    params.set("offset", filters.offset.toString());
    return `${API_BASE}/pipeline/leads?${params.toString()}`;
  }, [filters]);

  // Fetch summary
  const {
    data: summary,
    error: summaryError,
    isLoading: summaryLoading,
    mutate: mutateSummary,
  } = useSWR<PipelineSummary>(`${API_BASE}/pipeline/summary`, fetcher, {
    refreshInterval: REFRESH_INTERVAL,
    revalidateOnFocus: true,
  });

  // Fetch metrics
  const {
    data: metrics,
    error: metricsError,
    isLoading: metricsLoading,
    mutate: mutateMetrics,
  } = useSWR<PipelineMetrics>(`${API_BASE}/pipeline/metrics`, fetcher, {
    refreshInterval: REFRESH_INTERVAL,
  });

  // Fetch leads (filtered/paginated)
  const {
    data: leadsData,
    error: leadsError,
    isLoading: leadsLoading,
    mutate: mutateLeads,
  } = useSWR<PipelineLeadListResponse>(leadsUrl, fetcher, {
    refreshInterval: REFRESH_INTERVAL,
  });

  // Fetch follow-ups
  const {
    data: followups,
    error: followupsError,
    isLoading: followupsLoading,
    mutate: mutateFollowups,
  } = useSWR<PipelineLead[]>(`${API_BASE}/pipeline/followups`, fetcher, {
    refreshInterval: REFRESH_INTERVAL,
  });

  // Status update mutation
  const updateLeadStatus = useCallback(
    async (leadId: string, newStatus: string, reason?: string): Promise<StatusUpdateResponse> => {
      const response = await fetch(`${API_BASE}/pipeline/leads/${leadId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_status: newStatus, reason }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to update status");
      }

      const result: StatusUpdateResponse = await response.json();

      // Revalidate all data after status change
      mutateSummary();
      mutateMetrics();
      mutateLeads();
      mutateFollowups();

      return result;
    },
    [mutateSummary, mutateMetrics, mutateLeads, mutateFollowups]
  );

  // Add note mutation
  const addNote = useCallback(
    async (leadId: string, note: string): Promise<LeadHistoryEntry> => {
      const response = await fetch(`${API_BASE}/pipeline/leads/${leadId}/note`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to add note");
      }

      return response.json();
    },
    []
  );

  // CSV export
  const exportCSV = useCallback((status?: string) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    const url = `${API_BASE}/pipeline/export?${params.toString()}`;
    window.open(url, "_blank");
  }, []);

  // Refresh all data
  const refresh = useCallback(() => {
    mutateSummary();
    mutateMetrics();
    mutateLeads();
    mutateFollowups();
  }, [mutateSummary, mutateMetrics, mutateLeads, mutateFollowups]);

  const isLoading = summaryLoading || metricsLoading || leadsLoading || followupsLoading;
  const error = summaryError || metricsError || leadsError || followupsError || null;

  return {
    summary: summary ?? null,
    metrics: metrics ?? null,
    leads: leadsData?.leads ?? [],
    totalCount: leadsData?.total_count ?? 0,
    hasMore: leadsData?.has_more ?? false,
    followups: followups ?? [],
    isLoading,
    error,
    filters,
    setFilters,
    updateLeadStatus,
    addNote,
    exportCSV,
    refresh,
  };
}

export default usePipeline;
