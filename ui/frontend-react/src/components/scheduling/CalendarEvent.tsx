/**
 * CalendarEvent component.
 *
 * Story 4-4, Task 1.6: Renders individual calendar event
 * with color-coding by content type and conflict indicators.
 * Story 4-5, Task 7.1: Extended with publish status display.
 */

import React from "react";
import {
  CalendarEvent as CalendarEventType,
  getPublishStatusColor,
} from "@/types/schedule";
import { SourcePriority } from "@/types/approval";
import { PublishingSoonBadge } from "./PublishingSoonBadge";
import { cn } from "@/lib/utils";

// Source priority to color mapping
const PRIORITY_COLORS: Record<number, string> = {
  [SourcePriority.TRENDING]: "bg-red-500",
  [SourcePriority.SCHEDULED]: "bg-blue-500",
  [SourcePriority.EVERGREEN]: "bg-green-500",
  [SourcePriority.RESEARCH]: "bg-purple-500",
};

// Status icon components
const PublishedIcon = () => (
  <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const FailedIcon = () => (
  <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

export interface CalendarEventComponentProps {
  /** Calendar event data */
  event: CalendarEventType;
}

/**
 * Individual calendar event renderer.
 *
 * Displays event with:
 * - Color based on source priority or publish status
 * - Conflict indicator (red dot)
 * - Publishing soon badge
 * - Publish status icon (checkmark/X)
 * - Truncated title
 */
export function CalendarEventComponent({
  event,
}: CalendarEventComponentProps): React.ReactElement {
  const item = event.resource;
  const hasConflicts = item.conflicts.length > 0;

  // Story 4-5, Task 7.1: Use publish status color if published/failed
  const isPublished = item.status === "published";
  const isFailed = item.status === "publish_failed";
  const isPublishing = item.status === "publishing";

  // Determine color: published status overrides source priority
  const colorClass = isPublished || isFailed || isPublishing
    ? getPublishStatusColor(item.status)
    : PRIORITY_COLORS[item.source_priority] || "bg-gray-500";

  return (
    <div
      className={cn(
        "flex items-center gap-1 overflow-hidden px-1 py-0.5 rounded text-xs",
        colorClass,
        "text-white",
        hasConflicts && "ring-2 ring-red-600",
        item.is_imminent && "opacity-75",
        isPublishing && "animate-pulse"
      )}
      data-testid={`calendar-event-${item.id}`}
      draggable={!item.is_imminent && !isPublished && !isFailed}
    >
      {/* Status icons - Story 4-5, Task 7.7 */}
      {isPublished && <PublishedIcon />}
      {isFailed && <FailedIcon />}

      {item.is_imminent && !isPublished && !isFailed && <PublishingSoonBadge />}
      {hasConflicts && !isPublished && !isFailed && (
        <span
          className="w-2 h-2 bg-red-600 rounded-full flex-shrink-0"
          data-testid="conflict-indicator"
          title="Conflict: multiple posts scheduled same hour"
        />
      )}
      <span className="truncate">{item.title}</span>
    </div>
  );
}

export default CalendarEventComponent;
