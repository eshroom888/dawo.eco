/**
 * LeadHistoryTimeline component.
 *
 * Story 5-5, Task 8.8: Vertical timeline of lead activities.
 * Shows status changes, notes, emails, and other events chronologically.
 */

import React from "react";
import { cn } from "@/lib/utils";
import { LeadHistoryEntry } from "@/types/pipeline";

export interface LeadHistoryTimelineProps {
  entries: LeadHistoryEntry[];
  className?: string;
}

const ACTIVITY_ICONS: Record<string, string> = {
  created: "O",
  status_change: "->",
  email_sent: "@",
  email_delivered: "v",
  email_opened: "*",
  email_replied: "<-",
  note_added: "#",
  score_updated: "^",
  enriched: "+",
};

const ACTIVITY_COLORS: Record<string, string> = {
  created: "bg-blue-100 text-blue-700",
  status_change: "bg-purple-100 text-purple-700",
  email_sent: "bg-orange-100 text-orange-700",
  email_delivered: "bg-green-100 text-green-700",
  email_opened: "bg-teal-100 text-teal-700",
  email_replied: "bg-cyan-100 text-cyan-700",
  note_added: "bg-yellow-100 text-yellow-700",
  score_updated: "bg-indigo-100 text-indigo-700",
  enriched: "bg-pink-100 text-pink-700",
};

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return `Today at ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  }
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
}

/**
 * Vertical timeline of lead activities.
 */
export function LeadHistoryTimeline({
  entries,
  className,
}: LeadHistoryTimelineProps): React.ReactElement {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-4">No activity history</p>
    );
  }

  return (
    <div className={cn("relative", className)}>
      {/* Vertical line */}
      <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200" />

      <div className="space-y-4">
        {entries.map((entry) => {
          const icon = ACTIVITY_ICONS[entry.activity_type] ?? "?";
          const colorClass = ACTIVITY_COLORS[entry.activity_type] ?? "bg-gray-100 text-gray-700";

          return (
            <div key={entry.id} className="relative flex gap-3 pl-1">
              {/* Timeline dot */}
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono shrink-0 z-10",
                  colorClass
                )}
              >
                {icon}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 pt-0.5">
                <p className="text-sm text-gray-800">{entry.description}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-gray-400">
                    {formatTimestamp(entry.timestamp)}
                  </span>
                  <span className="text-xs text-gray-400">
                    by {entry.actor}
                  </span>
                </div>

                {/* Metadata */}
                {entry.metadata && Object.keys(entry.metadata).length > 0 && (
                  <div className="mt-1 text-xs text-gray-400">
                    {entry.metadata.old_status && entry.metadata.new_status && (
                      <span>
                        {String(entry.metadata.old_status)} {"->"} {String(entry.metadata.new_status)}
                      </span>
                    )}
                    {entry.metadata.reason && (
                      <span className="ml-2">({String(entry.metadata.reason)})</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default LeadHistoryTimeline;
