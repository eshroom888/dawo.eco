/**
 * PipelineStageColumn component.
 *
 * Story 5-5, Task 8.2: Single status column with lead count badge.
 * Used in kanban/board view of the pipeline.
 */

import React from "react";
import { cn } from "@/lib/utils";
import { PipelineLead, STATUS_CONFIGS, LeadStatus } from "@/types/pipeline";
import { LeadCard } from "./LeadCard";

export interface PipelineStageColumnProps {
  status: LeadStatus;
  leads: PipelineLead[];
  count: number;
  onLeadClick?: (lead: PipelineLead) => void;
  className?: string;
}

/**
 * Column displaying leads in a specific pipeline stage.
 */
export function PipelineStageColumn({
  status,
  leads,
  count,
  onLeadClick,
  className,
}: PipelineStageColumnProps): React.ReactElement {
  const config = STATUS_CONFIGS[status];

  return (
    <div className={cn("flex flex-col min-w-[280px] max-w-[320px]", className)}>
      {/* Column header */}
      <div className="flex items-center gap-2 mb-3 px-1">
        <span
          className={cn(
            "w-2.5 h-2.5 rounded-full",
            config.bgColor.replace("bg-", "bg-").replace("-100", "-400")
          )}
        />
        <h3 className="text-sm font-semibold text-gray-700">{config.label}</h3>
        <span className="ml-auto px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-medium">
          {count}
        </span>
      </div>

      {/* Lead cards */}
      <div className="flex flex-col gap-2 overflow-y-auto max-h-[calc(100vh-300px)] pr-1">
        {leads.map((lead) => (
          <LeadCard key={lead.id} lead={lead} onClick={onLeadClick} />
        ))}
        {leads.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">No leads</p>
        )}
      </div>
    </div>
  );
}

export default PipelineStageColumn;
