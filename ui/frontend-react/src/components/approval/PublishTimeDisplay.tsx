/**
 * PublishTimeDisplay component.
 *
 * Displays suggested publish time in human-readable format.
 * Shows relative time for upcoming publishes.
 */

import React from "react";

export interface PublishTimeDisplayProps {
  suggestedPublishTime: string | null;
  className?: string;
}

/**
 * Format date for display.
 */
function formatPublishTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  // Show relative time for upcoming dates
  if (diffMs > 0) {
    if (diffHours < 1) {
      const diffMinutes = Math.round(diffMs / (1000 * 60));
      return `in ${diffMinutes} min`;
    }
    if (diffHours < 24) {
      return `in ${Math.round(diffHours)} hours`;
    }
    if (diffDays < 7) {
      return `in ${Math.round(diffDays)} days`;
    }
  }

  // Show absolute date for past or far future
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Display suggested publish time.
 */
export function PublishTimeDisplay({
  suggestedPublishTime,
  className = "",
}: PublishTimeDisplayProps): React.ReactElement {
  if (!suggestedPublishTime) {
    return (
      <span className={`text-gray-400 text-sm ${className}`}>
        Not scheduled
      </span>
    );
  }

  const formattedTime = formatPublishTime(suggestedPublishTime);

  return (
    <span
      className={`text-gray-600 text-sm ${className}`}
      title={new Date(suggestedPublishTime).toLocaleString()}
    >
      {"\uD83D\uDCC5"} {formattedTime}
    </span>
  );
}

export default PublishTimeDisplay;
