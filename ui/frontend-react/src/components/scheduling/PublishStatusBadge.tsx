/**
 * PublishStatusBadge component.
 *
 * Story 4-5, Task 7.1: Display PUBLISHING, PUBLISHED, PUBLISH_FAILED
 * status with appropriate color coding.
 */

import React from "react";
import { cn } from "@/lib/utils";
import {
  PublishStatus,
  getPublishStatusColor,
  getPublishStatusLabel,
} from "@/types/schedule";

export interface PublishStatusBadgeProps {
  /** Current publish status */
  status?: PublishStatus;
  /** Optional CSS classes */
  className?: string;
  /** Show label text (default true) */
  showLabel?: boolean;
}

/**
 * Badge showing current publish status with color coding.
 *
 * Colors:
 * - Scheduled: Blue
 * - Publishing: Yellow (animated pulse)
 * - Published: Green
 * - Failed: Red
 */
export function PublishStatusBadge({
  status,
  className,
  showLabel = true,
}: PublishStatusBadgeProps): React.ReactElement | null {
  if (!status) return null;

  const colorClass = getPublishStatusColor(status);
  const label = getPublishStatusLabel(status);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white",
        colorClass,
        status === "publishing" && "animate-pulse",
        className
      )}
      data-testid={`publish-status-${status}`}
    >
      {status === "published" && (
        <svg
          className="w-3 h-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
      )}
      {status === "publish_failed" && (
        <svg
          className="w-3 h-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      )}
      {showLabel && <span>{label}</span>}
    </span>
  );
}

export default PublishStatusBadge;
