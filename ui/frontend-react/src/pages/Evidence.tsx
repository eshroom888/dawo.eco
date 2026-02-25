/**
 * Evidence page component.
 *
 * Story 6-9, Task 9: Main evidence search page with summary cards,
 * filters, evidence grid, pagination, and detail drawer.
 */

import React, { useState, useCallback } from "react";
import { useEvidence } from "@/hooks/useEvidence";
import { Evidence as EvidenceType } from "@/types/evidence";
import { EvidenceSummaryCards } from "@/components/evidence/EvidenceSummaryCards";
import { EvidenceFilters } from "@/components/evidence/EvidenceFilters";
import { EvidenceCard } from "@/components/evidence/EvidenceCard";
import { EvidenceDetailDrawer } from "@/components/evidence/EvidenceDetailDrawer";
import { CompetitorProfile } from "@/components/evidence/CompetitorProfile";
import { ReportGeneratorPanel } from "@/components/evidence/ReportGeneratorPanel";

export interface EvidencePageProps {
  className?: string;
}

/**
 * CleanMarket evidence search page.
 */
export function Evidence({ className = "" }: EvidencePageProps): React.ReactElement {
  const {
    evidence,
    summary,
    competitors,
    filters,
    setFilters,
    page,
    setPage,
    pageSize,
    isLoading,
    error,
    refresh,
    downloadEvidence,
  } = useEvidence();

  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [competitorView, setCompetitorView] = useState<string | null>(null);
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<Set<string>>(new Set());
  const [showReportPanel, setShowReportPanel] = useState(false);

  const handleEvidenceClick = useCallback((ev: EvidenceType) => {
    setSelectedEvidenceId(ev.id);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setSelectedEvidenceId(null);
  }, []);

  const handleCompetitorClick = useCallback((name: string) => {
    setCompetitorView(name);
    setFilters({ competitor: name });
  }, [setFilters]);

  const handleCloseCompetitor = useCallback(() => {
    setCompetitorView(null);
    setFilters({ competitor: undefined });
  }, [setFilters]);

  const handleToggleEvidence = useCallback((ev: EvidenceType) => {
    setSelectedEvidenceIds((prev: Set<string>) => {
      const next = new Set(prev);
      if (next.has(ev.id)) {
        next.delete(ev.id);
      } else {
        next.add(ev.id);
      }
      return next;
    });
  }, []);

  const totalCount = evidence?.total_count ?? 0;
  const items = evidence?.items ?? [];
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className={`p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">CleanMarket Evidence</h1>
          <p className="text-sm text-gray-500">
            {totalCount} evidence record{totalCount !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selectedEvidenceIds.size > 0 && (
            <span className="text-sm text-gray-500">
              {selectedEvidenceIds.size} selected
            </span>
          )}
          <button
            onClick={() => setShowReportPanel(!showReportPanel)}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
          >
            {showReportPanel ? "Hide Reports" : "Generate Report"}
          </button>
          <button
            onClick={refresh}
            disabled={isLoading}
            className="px-4 py-2 text-sm border rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Report generator panel */}
      {showReportPanel && (
        <div className="mb-6">
          <ReportGeneratorPanel
            selectedEvidenceIds={Array.from(selectedEvidenceIds)}
            competitorName={filters.competitor ?? null}
            className=""
          />
        </div>
      )}

      {/* Summary cards */}
      <div className="mb-6">
        <EvidenceSummaryCards summary={summary} />
      </div>

      {/* Competitor profile view */}
      {competitorView ? (
        <CompetitorProfile
          competitorName={competitorView}
          violations={items}
          onClose={handleCloseCompetitor}
          onEvidenceClick={handleEvidenceClick}
        />
      ) : (
        <>
          {/* Filters */}
          <div className="mb-4">
            <EvidenceFilters
              filters={filters}
              competitors={competitors}
              onFilterChange={setFilters}
            />
          </div>

          {/* Error state */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4 text-center">
              <p className="text-red-600 text-sm mb-2">{error.message}</p>
              <button
                onClick={refresh}
                className="px-3 py-1 text-sm border border-red-300 rounded hover:bg-red-100"
              >
                Try Again
              </button>
            </div>
          )}

          {/* Loading skeleton */}
          {isLoading && items.length === 0 && !error && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-24 bg-gray-200 rounded-lg animate-pulse" />
              ))}
            </div>
          )}

          {/* Evidence grid */}
          {items.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {items.map((ev) => (
                <EvidenceCard
                  key={ev.id}
                  evidence={ev}
                  onClick={handleEvidenceClick}
                  onCompetitorClick={handleCompetitorClick}
                  onSelect={handleToggleEvidence}
                  isSelected={selectedEvidenceIds.has(ev.id)}
                />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!isLoading && items.length === 0 && !error && (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No evidence found
              </h3>
              <p className="text-gray-500">
                {Object.values(filters).some(Boolean)
                  ? "Try adjusting your filters."
                  : "Run the evidence collection pipeline to capture violations."}
              </p>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
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
                disabled={!evidence?.has_more}
                className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {/* Evidence detail drawer */}
      <EvidenceDetailDrawer
        evidenceId={selectedEvidenceId}
        onClose={handleCloseDrawer}
        onDownload={downloadEvidence}
      />
    </div>
  );
}

export default Evidence;
