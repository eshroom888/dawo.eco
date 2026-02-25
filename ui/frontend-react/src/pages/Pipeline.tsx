/**
 * Pipeline page component.
 *
 * Story 5-5, Task 7.1: Main pipeline dashboard page.
 * Displays summary cards, filters, lead list, metrics, and lead detail drawer.
 */

import React, { useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { usePipeline } from "@/hooks/usePipeline";
import { PipelineLead } from "@/types/pipeline";
import {
  PipelineSummaryCards,
  PipelineFilters,
  LeadCard,
  PipelineMetricsPanel,
  CSVExportButton,
  LeadDetailDrawer,
} from "@/components/pipeline";

export interface PipelineProps {
  className?: string;
}

/**
 * Pipeline dashboard page.
 */
export function Pipeline({ className = "" }: PipelineProps): React.ReactElement {
  const {
    summary,
    metrics,
    leads,
    totalCount,
    hasMore,
    followups,
    isLoading,
    error,
    filters,
    setFilters,
    updateLeadStatus,
    addNote,
    exportCSV,
    refresh,
  } = usePipeline();

  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);

  const handleLeadClick = useCallback((lead: PipelineLead) => {
    setSelectedLeadId(lead.id);
    setIsDrawerOpen(true);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setIsDrawerOpen(false);
    setSelectedLeadId(null);
  }, []);

  const handleStatusChange = useCallback(
    async (leadId: string, newStatus: string, reason?: string) => {
      await updateLeadStatus(leadId, newStatus, reason);
    },
    [updateLeadStatus]
  );

  const handleAddNote = useCallback(
    async (leadId: string, note: string) => {
      await addNote(leadId, note);
    },
    [addNote]
  );

  const handleLoadMore = useCallback(() => {
    setFilters({ offset: filters.offset + filters.limit });
  }, [filters, setFilters]);

  return (
    <div className={`p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Lead Pipeline</h1>
          <p className="text-sm text-gray-500">
            {totalCount} total lead{totalCount !== 1 ? "s" : ""}
            {followups.length > 0 && (
              <span className="text-amber-600 ml-2">
                ({followups.length} need follow-up)
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowMetrics(!showMetrics)}
          >
            {showMetrics ? "Hide Metrics" : "Show Metrics"}
          </Button>
          <CSVExportButton
            onExport={exportCSV}
            currentStatus={filters.status}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={refresh}
            disabled={isLoading}
            aria-label="Refresh pipeline"
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <PipelineSummaryCards
        summary={summary}
        isLoading={isLoading}
        className="mb-6"
      />

      {/* Metrics panel (collapsible) */}
      {showMetrics && (
        <PipelineMetricsPanel
          metrics={metrics}
          isLoading={isLoading}
          className="mb-6"
        />
      )}

      {/* Filters */}
      <PipelineFilters
        status={filters.status}
        search={filters.search}
        sort={filters.sort}
        onStatusChange={(status) => setFilters({ status })}
        onSearchChange={(search) => setFilters({ search })}
        onSortChange={(sort) => setFilters({ sort })}
        className="mb-4"
      />

      {/* Error state */}
      {error && (
        <Card className="border-red-200 mb-4">
          <CardContent className="py-4 text-center">
            <p className="text-red-600 text-sm mb-2">{error.message}</p>
            <Button variant="outline" size="sm" onClick={refresh}>
              Try Again
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Follow-up alerts */}
      {followups.length > 0 && !filters.status && (
        <Card className="border-amber-200 bg-amber-50 mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-amber-800">
              Follow-up Required ({followups.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {followups.slice(0, 6).map((lead) => (
                <LeadCard key={lead.id} lead={lead} onClick={handleLeadClick} />
              ))}
            </div>
            {followups.length > 6 && (
              <p className="text-xs text-amber-600 mt-2 text-center">
                +{followups.length - 6} more leads need follow-up
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Lead list */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {leads.map((lead) => (
          <LeadCard key={lead.id} lead={lead} onClick={handleLeadClick} />
        ))}
      </div>

      {/* Empty state */}
      {!isLoading && leads.length === 0 && !error && (
        <Card className="text-center py-12">
          <CardContent>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No leads found
            </h3>
            <p className="text-gray-500">
              {filters.status || filters.search
                ? "Try adjusting your filters."
                : "Run the lead scanner to discover leads."}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Load more */}
      {hasMore && (
        <div className="text-center mt-4">
          <Button variant="outline" onClick={handleLoadMore} disabled={isLoading}>
            Load More
          </Button>
        </div>
      )}

      {/* Lead detail drawer */}
      <LeadDetailDrawer
        leadId={selectedLeadId}
        isOpen={isDrawerOpen}
        onClose={handleCloseDrawer}
        onStatusChange={handleStatusChange}
        onAddNote={handleAddNote}
      />
    </div>
  );
}

export default Pipeline;
