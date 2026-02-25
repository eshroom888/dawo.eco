/**
 * PipelineMetricsPanel component.
 *
 * Story 5-5, Task 8.9: Conversion funnel visualization and weekly trend display.
 * Uses text-based visualization (no chart library dependency).
 */

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PipelineMetrics, STATUS_CONFIGS, LeadStatus } from "@/types/pipeline";

export interface PipelineMetricsPanelProps {
  metrics: PipelineMetrics | null;
  isLoading: boolean;
  className?: string;
}

/**
 * Simple horizontal bar for stage timing.
 */
function StageBar({
  label,
  days,
  maxDays,
}: {
  label: string;
  days: number;
  maxDays: number;
}): React.ReactElement {
  const width = maxDays > 0 ? Math.max(2, (days / maxDays) * 100) : 0;

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 w-28 text-right truncate">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-3">
        <div
          className="bg-blue-400 h-3 rounded-full transition-all"
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-xs text-gray-600 w-12">{days.toFixed(1)}d</span>
    </div>
  );
}

/**
 * Pipeline metrics panel with funnel and trends.
 */
export function PipelineMetricsPanel({
  metrics,
  isLoading,
  className = "",
}: PipelineMetricsPanelProps): React.ReactElement {
  const maxDays = metrics
    ? Math.max(...Object.values(metrics.avg_time_per_stage), 1)
    : 1;

  return (
    <div className={`grid grid-cols-1 lg:grid-cols-2 gap-4 ${className}`}>
      {/* Avg time per stage */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Avg. Time per Stage</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-5 w-full" />
              ))}
            </div>
          ) : metrics && Object.keys(metrics.avg_time_per_stage).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(metrics.avg_time_per_stage).map(([stage, days]) => {
                const config = STATUS_CONFIGS[stage as LeadStatus];
                return (
                  <StageBar
                    key={stage}
                    label={config?.label ?? stage}
                    days={days}
                    maxDays={maxDays}
                  />
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-4">No stage data yet</p>
          )}
        </CardContent>
      </Card>

      {/* Weekly trend */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Weekly Trend</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-5 w-full" />
              ))}
            </div>
          ) : metrics && metrics.weekly_trend.length > 0 ? (
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
                <span className="w-20">Week</span>
                <span className="flex-1">New</span>
                <span className="w-16 text-right">Converted</span>
              </div>
              {metrics.weekly_trend.map((week) => (
                <div key={week.week} className="flex items-center gap-2 text-sm">
                  <span className="w-20 text-xs text-gray-500">{week.week}</span>
                  <span className="flex-1 font-medium text-blue-600">
                    +{week.new_leads}
                  </span>
                  <span className="w-16 text-right font-medium text-green-600">
                    {week.converted > 0 ? `+${week.converted}` : "-"}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-4">No trend data yet</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default PipelineMetricsPanel;
