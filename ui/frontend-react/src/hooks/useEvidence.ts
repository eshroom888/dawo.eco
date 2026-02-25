/**
 * useEvidence hook.
 *
 * Story 6-9, Task 7: Data fetching hook for the evidence search page.
 * Provides evidence list, summary, competitor data, and download via SWR.
 */

import useSWR from "swr";
import { useState, useCallback, useMemo } from "react";
import {
  EvidenceListResponse,
  EvidenceSummary,
  EvidenceDetail,
  EvidenceFilters,
  CompetitorTimelineEntry,
} from "@/types/evidence";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const REFRESH_INTERVAL = 30000;

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export interface UseEvidenceResult {
  evidence: EvidenceListResponse | null;
  summary: EvidenceSummary | null;
  competitors: string[];
  filters: EvidenceFilters;
  setFilters: (filters: Partial<EvidenceFilters>) => void;
  page: number;
  setPage: (page: number) => void;
  pageSize: number;
  isLoading: boolean;
  error: Error | null;
  refresh: () => void;
  downloadEvidence: (id: string) => Promise<void>;
}

/**
 * Hook for fetching and managing evidence search data.
 */
export function useEvidence(): UseEvidenceResult {
  const [filters, setFiltersState] = useState<EvidenceFilters>({});
  const [page, setPage] = useState(0);
  const pageSize = 25;

  const setFilters = useCallback((update: Partial<EvidenceFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...update }));
    setPage(0);
  }, []);

  // Build evidence list URL with filters
  const listUrl = useMemo(() => {
    const params = new URLSearchParams();
    if (filters.competitor) params.set("competitor", filters.competitor);
    if (filters.severity) params.set("severity", filters.severity);
    if (filters.violationType) params.set("violation_type", filters.violationType);
    if (filters.dateFrom) params.set("date_from", filters.dateFrom);
    if (filters.dateTo) params.set("date_to", filters.dateTo);
    if (filters.keywords) params.set("keywords", filters.keywords);
    if (filters.sourceType) params.set("source_type", filters.sourceType);
    params.set("limit", String(pageSize));
    params.set("offset", String(page * pageSize));
    return `${API_BASE}/evidence?${params.toString()}`;
  }, [filters, page]);

  // Fetch evidence list
  const {
    data: evidence,
    error: evidenceError,
    isLoading: evidenceLoading,
    mutate: mutateEvidence,
  } = useSWR<EvidenceListResponse>(listUrl, fetcher, {
    refreshInterval: REFRESH_INTERVAL,
  });

  // Fetch summary
  const {
    data: summary,
    error: summaryError,
    isLoading: summaryLoading,
    mutate: mutateSummary,
  } = useSWR<EvidenceSummary>(`${API_BASE}/evidence/summary`, fetcher, {
    refreshInterval: REFRESH_INTERVAL,
  });

  // Fetch competitors for filter dropdown
  const {
    data: competitors,
    error: competitorsError,
  } = useSWR<string[]>(`${API_BASE}/evidence/competitors`, fetcher);

  // Download evidence package
  const downloadEvidence = useCallback(async (id: string) => {
    const response = await fetch(`${API_BASE}/evidence/${id}/download`);
    if (!response.ok) {
      throw new Error(`Download failed: ${response.status}`);
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `evidence-${id}.zip`;
    a.click();
    window.URL.revokeObjectURL(url);
  }, []);

  // Refresh all data
  const refresh = useCallback(() => {
    mutateEvidence();
    mutateSummary();
  }, [mutateEvidence, mutateSummary]);

  const isLoading = evidenceLoading || summaryLoading;
  const error = evidenceError || summaryError || competitorsError || null;

  return {
    evidence: evidence ?? null,
    summary: summary ?? null,
    competitors: competitors ?? [],
    filters,
    setFilters,
    page,
    setPage,
    pageSize,
    isLoading,
    error,
    refresh,
    downloadEvidence,
  };
}

/**
 * Hook for fetching a single evidence detail.
 */
export function useEvidenceDetail(id: string | null) {
  const { data, error, isLoading } = useSWR<EvidenceDetail>(
    id ? `${API_BASE}/evidence/${id}` : null,
    fetcher
  );
  return { detail: data ?? null, error, isLoading };
}

/**
 * Hook for fetching competitor timeline data.
 */
export function useCompetitorTimeline(name: string | null) {
  const { data, error, isLoading } = useSWR<CompetitorTimelineEntry[]>(
    name ? `${API_BASE}/evidence/competitors/${encodeURIComponent(name)}/timeline` : null,
    fetcher
  );
  return { timeline: data ?? [], error, isLoading };
}

export default useEvidence;
