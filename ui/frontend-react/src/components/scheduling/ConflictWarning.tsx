/**
 * ConflictWarning component.
 *
 * Story 4-4, Task 7.3: Visual indicator for scheduling conflicts
 * when multiple posts are scheduled for the same hour.
 */

import React from "react";
import { ConflictInfo, ConflictSeverity, CONFLICT_RULES } from "@/types/schedule";
import { cn } from "@/lib/utils";

export interface ConflictWarningProps {
  /** Conflict information */
  conflict: ConflictInfo;
  /** Additional CSS classes */
  className?: string;
  /** Show details */
  showDetails?: boolean;
}

const SEVERITY_STYLES: Record<ConflictSeverity, string> = {
  warning: "bg-yellow-100 border-yellow-400 text-yellow-800",
  critical: "bg-red-100 border-red-400 text-red-800",
};

const SEVERITY_ICONS: Record<ConflictSeverity, string> = {
  warning: "⚠️",
  critical: "🚫",
};

/**
 * Warning indicator for scheduling conflicts.
 *
 * Shows when multiple posts are scheduled for the same hour,
 * with severity based on post count:
 * - Warning (2 posts): Yellow indicator
 * - Critical (3+ posts): Red indicator
 */
export function ConflictWarning({
  conflict,
  className,
  showDetails = true,
}: ConflictWarningProps): React.ReactElement {
  const { severity, posts_count, hour } = conflict;
  const formattedHour = new Date(hour).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <div
      className={cn(
        "flex items-start gap-2 p-2 rounded border",
        SEVERITY_STYLES[severity],
        className
      )}
      role="alert"
      data-testid="conflict-warning"
    >
      <span className="text-lg" aria-hidden="true">
        {SEVERITY_ICONS[severity]}
      </span>

      <div className="flex-1 min-w-0">
        <div className="font-medium">
          {posts_count} posts at {formattedHour}
        </div>

        {showDetails && (
          <div className="text-sm mt-1">
            {severity === "critical" ? (
              <>
                <strong>Too many posts!</strong> Maximum{" "}
                {CONFLICT_RULES.MAX_POSTS_PER_HOUR} posts per hour recommended.
              </>
            ) : (
              <>Consider spreading posts for better engagement.</>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Compact conflict indicator for calendar cells.
 */
export function ConflictIndicator({
  severity,
  count,
}: {
  severity: ConflictSeverity;
  count: number;
}): React.ReactElement {
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold",
        severity === "critical"
          ? "bg-red-500 text-white"
          : "bg-yellow-400 text-yellow-900"
      )}
      data-testid="conflict-indicator"
      title={`${count} posts scheduled (conflict)`}
    >
      {count}
    </span>
  );
}

export default ConflictWarning;
