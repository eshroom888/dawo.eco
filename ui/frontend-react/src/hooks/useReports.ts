/**
 * useReports hook.
 *
 * Story 6-10, Task 10: Data fetching hook for violation report generation.
 * Provides report list, templates, generate, and download via SWR.
 */

import useSWR from "swr";
import { useState, useCallback } from "react";
import {
  ReportGenerateRequest,
  ReportGenerateResponse,
  ReportListResponse,
  TEMPLATE_LABELS,
} from "@/types/reports";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export interface UseReportsResult {
  reports: ReportListResponse | null;
  templates: Record<string, string>;
  page: number;
  setPage: (page: number) => void;
  pageSize: number;
  isLoading: boolean;
  isGenerating: boolean;
  error: Error | null;
  generateError: Error | null;
  refresh: () => void;
  generateReport: (request: ReportGenerateRequest) => Promise<ReportGenerateResponse>;
  downloadReport: (reportId: string, filename: string) => Promise<void>;
}

/**
 * Hook for managing violation report generation and listing.
 */
export function useReports(): UseReportsResult {
  const [page, setPage] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<Error | null>(null);
  const pageSize = 25;

  // Fetch paginated report list
  const {
    data: reports,
    error: reportsError,
    isLoading: reportsLoading,
    mutate: mutateReports,
  } = useSWR<ReportListResponse>(
    `${API_BASE}/reports?limit=${pageSize}&offset=${page * pageSize}`,
    fetcher
  );

  // Fetch available templates
  const {
    data: templatesData,
    error: templatesError,
    isLoading: templatesLoading,
  } = useSWR<{ templates: string[] }>(
    `${API_BASE}/reports/templates`,
    fetcher
  );

  // Map template names from API to display labels
  const templates: Record<string, string> = {};
  if (templatesData?.templates) {
    for (const name of templatesData.templates) {
      templates[name] = TEMPLATE_LABELS[name] ?? name;
    }
  }

  // Generate a new report
  const generateReport = useCallback(
    async (request: ReportGenerateRequest): Promise<ReportGenerateResponse> => {
      setIsGenerating(true);
      setGenerateError(null);
      try {
        const response = await fetch(`${API_BASE}/reports/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        });
        if (!response.ok) {
          const errorBody = await response.text();
          throw new Error(`Report generation failed: ${response.status} ${errorBody}`);
        }
        const result: ReportGenerateResponse = await response.json();
        mutateReports();
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setGenerateError(error);
        throw error;
      } finally {
        setIsGenerating(false);
      }
    },
    [mutateReports]
  );

  // Download a report PDF
  const downloadReport = useCallback(
    async (reportId: string, filename: string) => {
      const response = await fetch(`${API_BASE}/reports/${reportId}/download`);
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);
    },
    []
  );

  // Refresh report list
  const refresh = useCallback(() => {
    mutateReports();
  }, [mutateReports]);

  const isLoading = reportsLoading || templatesLoading;
  const error = reportsError || templatesError || null;

  return {
    reports: reports ?? null,
    templates: Object.keys(templates).length > 0 ? templates : TEMPLATE_LABELS,
    page,
    setPage,
    pageSize,
    isLoading,
    isGenerating,
    error,
    generateError,
    refresh,
    generateReport,
    downloadReport,
  };
}

export default useReports;
