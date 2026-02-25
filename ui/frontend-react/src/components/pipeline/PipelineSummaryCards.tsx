/**
 * PipelineSummaryCards component.
 *
 * Story 5-5, Task 8.1: Top-level metric cards for the pipeline dashboard.
 * Shows total leads, conversion rate, follow-up count, and avg time in pipeline.
 */

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PipelineSummary } from "@/types/pipeline";

export interface PipelineSummaryCardsProps {
  summary: PipelineSummary | null;
  isLoading: boolean;
  className?: string;
}

interface MetricCardProps {
  label: string;
  value: string | number;
  detail?: string;
  isLoading: boolean;
}

function MetricCard({ label, value, detail, isLoading }: MetricCardProps): React.ReactElement {
  return (
    <Card>
      <CardContent className="pt-4 pb-3">
        {isLoading ? (
          <>
            <Skeleton className="h-4 w-24 mb-2" />
            <Skeleton className="h-8 w-16" />
          </>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-1">{label}</p>
            <p className="text-2xl font-bold">{value}</p>
            {detail && <p className="text-xs text-gray-400 mt-1">{detail}</p>}
          </>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Dashboard summary metric cards.
 */
export function PipelineSummaryCards({
  summary,
  isLoading,
  className = "",
}: PipelineSummaryCardsProps): React.ReactElement {
  return (
    <div className={`grid grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
      <MetricCard
        label="Total Leads"
        value={summary?.total_leads ?? 0}
        isLoading={isLoading}
      />
      <MetricCard
        label="Conversion Rate"
        value={summary ? `${summary.conversion_rate.toFixed(1)}%` : "0%"}
        detail={summary ? `${summary.status_counts?.converted ?? 0} converted` : undefined}
        isLoading={isLoading}
      />
      <MetricCard
        label="Need Follow-up"
        value={summary?.followup_count ?? 0}
        detail="Overdue > 7 days"
        isLoading={isLoading}
      />
      <MetricCard
        label="Avg. Pipeline Time"
        value={summary ? `${summary.avg_days_in_pipeline.toFixed(0)}d` : "0d"}
        detail="Days from new to close"
        isLoading={isLoading}
      />
    </div>
  );
}

export default PipelineSummaryCards;
