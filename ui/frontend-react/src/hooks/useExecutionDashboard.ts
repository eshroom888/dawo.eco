/**
 * useExecutionDashboard hook.
 *
 * Story 7-8, Task 8.2: Data fetching hook for execution dashboard.
 * Provides dashboard summary, filtered execution list, detail fetch, and retry action.
 * Uses SWR with 30s auto-refresh for dashboard (AC2).
 */

import useSWR from "swr";
import { useCallback, useState } from "react";
import {
  DashboardSummary,
  ExecutionFilters,
  ExecutionListResponse,
  ExecutionLogDetail,
} from "@/types/executions";
import { TriggerResult } from "@/types/triggers";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const DASHBOARD_REFRESH_INTERVAL = 30000; // 30s auto-refresh

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const error = new Error(`API error: ${response.status}`);
    throw error;
  }
  return response.json();
}

function buildFilterQuery(filters: ExecutionFilters, limit: number, offset: number): string {
  const params = new URLSearchParams();
  if (filters.agent_name) params.set("agent_name", filters.agent_name);
  if (filters.status) params.set("status", filters.status);
  if (filters.trigger_type) params.set("trigger_type", filters.trigger_type);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return params.toString();
}

export interface UseExecutionDashboardResult {
  dashboard: DashboardSummary | null;
  executions: ExecutionListResponse | null;
  isLoading: boolean;
  error: Error | null;
  filters: ExecutionFilters;
  setFilters: (filters: ExecutionFilters) => void;
  page: number;
  setPage: (page: number) => void;
  getExecutionDetail: (id: string) => Promise<ExecutionLogDetail>;
  retryExecution: (id: string) => Promise<TriggerResult>;
  refresh: () => void;
}

const PAGE_SIZE = 25;

/**
 * Hook for execution dashboard with auto-refreshing summary and filtered list.
 */
export function useExecutionDashboard(): UseExecutionDashboardResult {
  const [filters, setFilters] = useState<ExecutionFilters>({});
  const [page, setPage] = useState(0);

  // Dashboard summary with 30s auto-refresh
  const {
    data: dashboard,
    error: dashboardError,
    isLoading: dashboardLoading,
    mutate: mutateDashboard,
  } = useSWR<DashboardSummary>(
    `${API_BASE}/executions/dashboard`,
    fetcher,
    { refreshInterval: DASHBOARD_REFRESH_INTERVAL, revalidateOnFocus: true }
  );

  // Filtered execution list
  const filterQuery = buildFilterQuery(filters, PAGE_SIZE, page * PAGE_SIZE);
  const {
    data: executions,
    error: executionsError,
    isLoading: executionsLoading,
    mutate: mutateExecutions,
  } = useSWR<ExecutionListResponse>(
    `${API_BASE}/executions/?${filterQuery}`,
    fetcher,
    { revalidateOnFocus: true }
  );

  // On-demand detail fetch
  const getExecutionDetail = useCallback(
    async (id: string): Promise<ExecutionLogDetail> => {
      const response = await fetch(`${API_BASE}/executions/${id}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("Execution not found");
        }
        throw new Error(`API error: ${response.status}`);
      }
      return response.json();
    },
    []
  );

  // Retry failed execution
  const retryExecution = useCallback(
    async (id: string): Promise<TriggerResult> => {
      const response = await fetch(`${API_BASE}/executions/${id}/retry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || `Failed to retry: ${response.status}`);
      }

      const result: TriggerResult = await response.json();
      // Invalidate caches after retry
      mutateDashboard();
      mutateExecutions();
      return result;
    },
    [mutateDashboard, mutateExecutions]
  );

  // Refresh all data
  const refresh = useCallback(() => {
    mutateDashboard();
    mutateExecutions();
  }, [mutateDashboard, mutateExecutions]);

  return {
    dashboard: dashboard ?? null,
    executions: executions ?? null,
    isLoading: dashboardLoading || executionsLoading,
    error: dashboardError || executionsError || null,
    filters,
    setFilters,
    page,
    setPage,
    getExecutionDetail,
    retryExecution,
    refresh,
  };
}

export default useExecutionDashboard;
