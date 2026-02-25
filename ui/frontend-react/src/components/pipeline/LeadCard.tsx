/**
 * LeadCard component.
 *
 * Story 5-5, Task 8.3: Compact card displaying lead info in the pipeline list.
 * Shows company, contact name, score, status, and follow-up indicator.
 */

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { PipelineLead, STATUS_CONFIGS, LeadStatus } from "@/types/pipeline";
import { FollowUpBadge } from "./FollowUpBadge";

export interface LeadCardProps {
  lead: PipelineLead;
  onClick?: (lead: PipelineLead) => void;
  className?: string;
}

/**
 * Score badge with color coding.
 */
function ScoreBadge({ score }: { score: number }): React.ReactElement {
  const color =
    score >= 80 ? "text-green-700 bg-green-50" :
    score >= 50 ? "text-yellow-700 bg-yellow-50" :
    "text-red-700 bg-red-50";

  return (
    <span className={cn("px-2 py-0.5 rounded text-xs font-semibold", color)}>
      {score.toFixed(0)}
    </span>
  );
}

/**
 * Compact lead card for pipeline list view.
 */
export function LeadCard({
  lead,
  onClick,
  className,
}: LeadCardProps): React.ReactElement {
  const statusConfig = STATUS_CONFIGS[lead.status as LeadStatus] ?? {
    label: lead.status,
    color: "text-gray-700",
    bgColor: "bg-gray-100",
  };

  return (
    <Card
      className={cn(
        "cursor-pointer hover:shadow-md transition-shadow",
        lead.needs_followup && "border-l-4 border-l-amber-400",
        className
      )}
      onClick={() => onClick?.(lead)}
    >
      <CardContent className="py-3 px-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="font-medium text-sm truncate">{lead.company}</p>
            <p className="text-xs text-gray-500 truncate">
              {lead.first_name} {lead.last_name}
              {lead.job_title && ` - ${lead.job_title}`}
            </p>
          </div>
          <ScoreBadge score={lead.score} />
        </div>

        <div className="flex items-center gap-2 mt-2">
          <span
            className={cn(
              "px-2 py-0.5 rounded-full text-xs font-medium",
              statusConfig.bgColor,
              statusConfig.color
            )}
          >
            {statusConfig.label}
          </span>

          {lead.needs_followup && lead.days_since_contact != null && (
            <FollowUpBadge daysSinceContact={lead.days_since_contact} />
          )}

          {lead.contact_count > 0 && (
            <span className="text-xs text-gray-400 ml-auto">
              {lead.contact_count}x contacted
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default LeadCard;
