/**
 * FollowUpBadge component.
 *
 * Story 5-5, Task 8.4: Visual indicator for leads needing follow-up.
 * Shows days since last contact with urgency coloring.
 */

import React from "react";
import { cn } from "@/lib/utils";

export interface FollowUpBadgeProps {
  daysSinceContact: number;
  className?: string;
}

/**
 * Badge showing follow-up urgency based on days since contact.
 */
export function FollowUpBadge({
  daysSinceContact,
  className,
}: FollowUpBadgeProps): React.ReactElement {
  const isUrgent = daysSinceContact >= 14;
  const isWarning = daysSinceContact >= 7;

  const colorClass = isUrgent
    ? "bg-red-100 text-red-800 border-red-200"
    : isWarning
      ? "bg-amber-100 text-amber-800 border-amber-200"
      : "bg-gray-100 text-gray-600 border-gray-200";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border",
        colorClass,
        className
      )}
      title={`${daysSinceContact} days since last contact`}
    >
      {isUrgent ? "!!" : isWarning ? "!" : ""} {daysSinceContact}d
    </span>
  );
}

export default FollowUpBadge;
