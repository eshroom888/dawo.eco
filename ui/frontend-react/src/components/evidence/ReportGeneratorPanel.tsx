/**
 * ReportGeneratorPanel component.
 *
 * Story 6-10, Task 11: UI panel for generating and managing
 * on-demand violation report PDFs.
 */

import React, { useState, useCallback } from "react";
import { useReports } from "@/hooks/useReports";
import { ReportGenerateRequest, ReportListItem, TEMPLATE_LABELS } from "@/types/reports";

export interface ReportGeneratorPanelProps {
  /** Pre-selected evidence IDs from the evidence page. */
  selectedEvidenceIds?: string[];
  /** Pre-selected competitor name filter. */
  competitorName?: string | null;
  className?: string;
}

/**
 * Panel for generating violation reports and listing existing reports.
 */
export function ReportGeneratorPanel({
  selectedEvidenceIds = [],
  competitorName = null,
  className = "",
}: ReportGeneratorPanelProps): React.ReactElement {
  const {
    reports,
    templates,
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
  } = useReports();

  const [templateType, setTemplateType] = useState("standard");
  const [reportTitle, setReportTitle] = useState("");
  const [lastResult, setLastResult] = useState<{
    report_id: string;
    filename: string;
    evidence_count: number;
  } | null>(null);

  const handleGenerate = useCallback(async () => {
    const request: ReportGenerateRequest = {
      template_type: templateType,
    };
    if (selectedEvidenceIds.length > 0) {
      request.evidence_ids = selectedEvidenceIds;
    }
    if (competitorName) {
      request.competitor_name = competitorName;
    }
    if (reportTitle.trim()) {
      request.report_title = reportTitle.trim();
    }

    try {
      const result = await generateReport(request);
      setLastResult({
        report_id: result.report_id,
        filename: result.filename,
        evidence_count: result.evidence_count,
      });
    } catch {
      // Error state is handled by the hook
    }
  }, [templateType, selectedEvidenceIds, competitorName, reportTitle, generateReport]);

  const handleDownload = useCallback(
    (item: ReportListItem) => {
      downloadReport(item.report_id, item.filename);
    },
    [downloadReport]
  );

  const totalCount = reports?.total_count ?? 0;
  const items = reports?.items ?? [];
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className={`bg-white rounded-lg shadow ${className}`}>
      {/* Generate Section */}
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold mb-3">Generate Violation Report</h2>

        <div className="space-y-3">
          {/* Template selector */}
          <div>
            <label htmlFor="template-type" className="block text-sm font-medium text-gray-700 mb-1">
              Report Template
            </label>
            <select
              id="template-type"
              value={templateType}
              onChange={(e) => setTemplateType(e.target.value)}
              className="w-full border rounded-md px-3 py-2 text-sm"
            >
              {Object.entries(templates).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Optional title */}
          <div>
            <label htmlFor="report-title" className="block text-sm font-medium text-gray-700 mb-1">
              Report Title (optional)
            </label>
            <input
              id="report-title"
              type="text"
              value={reportTitle}
              onChange={(e) => setReportTitle(e.target.value)}
              placeholder="Auto-generated if empty"
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          {/* Selection info */}
          {selectedEvidenceIds.length > 0 && (
            <p className="text-sm text-gray-500">
              {selectedEvidenceIds.length} evidence item{selectedEvidenceIds.length !== 1 ? "s" : ""} selected
            </p>
          )}
          {competitorName && (
            <p className="text-sm text-gray-500">
              Competitor: {competitorName}
            </p>
          )}

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isGenerating ? "Generating..." : "Generate Report"}
          </button>

          {/* Generation error */}
          {generateError && (
            <div className="bg-red-50 border border-red-200 rounded p-2">
              <p className="text-red-600 text-sm">{generateError.message}</p>
            </div>
          )}

          {/* Success message */}
          {lastResult && (
            <div className="bg-green-50 border border-green-200 rounded p-2">
              <p className="text-green-700 text-sm">
                Report generated with {lastResult.evidence_count} evidence items.
              </p>
              <button
                onClick={() => downloadReport(lastResult.report_id, lastResult.filename)}
                className="text-green-700 text-sm underline mt-1"
              >
                Download {lastResult.filename}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Reports List Section */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">
            Reports {totalCount > 0 && `(${totalCount})`}
          </h2>
          <button
            onClick={refresh}
            disabled={isLoading}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            Refresh
          </button>
        </div>

        {/* Error state */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded p-3 mb-3">
            <p className="text-red-600 text-sm">{error.message}</p>
          </div>
        )}

        {/* Loading skeleton */}
        {isLoading && items.length === 0 && !error && (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-200 rounded animate-pulse" />
            ))}
          </div>
        )}

        {/* Report list */}
        {items.length > 0 && (
          <div className="space-y-2">
            {items.map((item) => (
              <div
                key={item.report_id}
                className="flex items-center justify-between border rounded-md p-3 hover:bg-gray-50"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{item.filename}</p>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span>{TEMPLATE_LABELS[item.template_type] ?? item.template_type}</span>
                    <span>{item.evidence_count} items</span>
                    {item.competitor_name && <span>{item.competitor_name}</span>}
                    <span>{new Date(item.generated_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <button
                  onClick={() => handleDownload(item)}
                  className="ml-3 px-3 py-1 text-sm border rounded hover:bg-gray-100 flex-shrink-0"
                >
                  Download
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && items.length === 0 && !error && (
          <p className="text-center text-gray-500 text-sm py-6">
            No reports generated yet. Use the form above to create one.
          </p>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-4">
            <button
              onClick={() => setPage(page - 1)}
              disabled={page === 0}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-gray-600">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage(page + 1)}
              disabled={!reports?.has_more}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ReportGeneratorPanel;
