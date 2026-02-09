/**
 * PublishingSoonBadge component.
 *
 * Story 4-4, Task 6.2: Visual indicator for posts
 * scheduled to publish within 1 hour.
 */

import React from "react";
import { cn } from "@/lib/utils";

export interface PublishingSoonBadgeProps {
  /** Additional CSS classes */
  className?: string;
  /** Show countdown timer */
  showCountdown?: boolean;
  /** Minutes until publish */
  minutesUntilPublish?: number;
  /** Data test ID */
  "data-testid"?: string;
}

/**
 * Badge indicating content is publishing soon.
 *
 * Shows when content is within 1 hour of publish time.
 * Indicates that editing is locked or requires confirmation.
 */
export function PublishingSoonBadge({
  className,
  showCountdown = false,
  minutesUntilPublish,
  "data-testid": testId = "publishing-soon-badge",
}: PublishingSoonBadgeProps): React.ReactElement {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium",
        "bg-amber-500 text-white",
        "animate-pulse",
        className
      )}
      data-testid={testId}
      title="Publishing soon - editing is locked"
    >
      <svg
        className="w-3 h-3"
        fill="currentColor"
        viewBox="0 0 20 20"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
          clipRule="evenodd"
        />
      </svg>
      {showCountdown && minutesUntilPublish !== undefined ? (
        <span>{minutesUntilPublish}m</span>
      ) : (
        <span>Soon</span>
      )}
    </span>
  );
}

export default PublishingSoonBadge;
