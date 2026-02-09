/**
 * AutoPublishBadge component.
 *
 * Displays badge indicating content meets auto-publish criteria.
 * Only shown when would_auto_publish is true.
 */

import React from "react";
import { Badge } from "@/components/ui/badge";

export interface AutoPublishBadgeProps {
  wouldAutoPublish: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeClasses = {
  sm: "text-xs px-1.5 py-0.5",
  md: "text-sm px-2 py-1",
  lg: "text-base px-3 py-1.5",
};

/**
 * Auto-publish eligibility badge.
 *
 * Only renders when content meets auto-publish criteria
 * (quality score >= 9 and compliance status is COMPLIANT).
 */
export function AutoPublishBadge({
  wouldAutoPublish,
  size = "md",
  className = "",
}: AutoPublishBadgeProps): React.ReactElement | null {
  if (!wouldAutoPublish) {
    return null;
  }

  return (
    <Badge
      variant="outline"
      className={`bg-purple-100 text-purple-800 border-purple-300 hover:bg-purple-100 ${sizeClasses[size]} font-medium ${className}`}
      aria-label="Eligible for auto-publish"
    >
      <span className="mr-1" aria-hidden="true">
        {"\u26A1"} {/* Lightning bolt */}
      </span>
      Auto-Publish
    </Badge>
  );
}

export default AutoPublishBadge;
