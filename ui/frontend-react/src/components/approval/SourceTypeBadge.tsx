/**
 * SourceTypeBadge component.
 *
 * Displays content source type with icon and color coding.
 */

import React from "react";
import { Badge } from "@/components/ui/badge";
import { SOURCE_TYPES } from "@/types/approval";

export interface SourceTypeBadgeProps {
  sourceType: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeClasses = {
  sm: "text-xs px-1.5 py-0.5",
  md: "text-sm px-2 py-1",
  lg: "text-base px-3 py-1.5",
};

/**
 * Get icon for source type.
 */
function getSourceIcon(iconType: string): string {
  const icons: Record<string, string> = {
    instagram: "\uD83D\uDCF7", // Camera
    mail: "\u2709", // Envelope
    clock: "\u23F0", // Alarm clock
    video: "\uD83C\uDFA5", // Film camera
  };
  return icons[iconType] || "\uD83D\uDCC4"; // Default: document
}

/**
 * Source type badge with icon and styling.
 */
export function SourceTypeBadge({
  sourceType,
  size = "md",
  className = "",
}: SourceTypeBadgeProps): React.ReactElement {
  const config = SOURCE_TYPES[sourceType] || {
    label: sourceType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    icon: "document",
    color: "bg-gray-100 text-gray-800",
  };

  return (
    <Badge
      variant="outline"
      className={`${config.color} ${sizeClasses[size]} font-medium ${className}`}
      aria-label={`Source type: ${config.label}`}
    >
      <span className="mr-1" aria-hidden="true">
        {getSourceIcon(config.icon)}
      </span>
      {config.label}
    </Badge>
  );
}

export default SourceTypeBadge;
