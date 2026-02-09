/**
 * ComplianceStatusBadge component.
 *
 * Displays content compliance status with appropriate styling:
 * - COMPLIANT: Green checkmark
 * - WARNING: Yellow warning
 * - REJECTED: Red X
 */

import React from "react";
import { Badge } from "@/components/ui/badge";
import { ComplianceStatus } from "@/types/approval";

export interface ComplianceStatusBadgeProps {
  status: ComplianceStatus;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const statusConfig: Record<ComplianceStatus, { label: string; className: string; icon: string }> = {
  [ComplianceStatus.COMPLIANT]: {
    label: "Compliant",
    className: "bg-green-100 text-green-800 border-green-300 hover:bg-green-100",
    icon: "\u2713", // Checkmark
  },
  [ComplianceStatus.WARNING]: {
    label: "Warning",
    className: "bg-yellow-100 text-yellow-800 border-yellow-300 hover:bg-yellow-100",
    icon: "\u26A0", // Warning sign
  },
  [ComplianceStatus.REJECTED]: {
    label: "Rejected",
    className: "bg-red-100 text-red-800 border-red-300 hover:bg-red-100",
    icon: "\u2717", // X mark
  },
};

const sizeClasses = {
  sm: "text-xs px-1.5 py-0.5",
  md: "text-sm px-2 py-1",
  lg: "text-base px-3 py-1.5",
};

/**
 * Compliance status badge with icon and color coding.
 */
export function ComplianceStatusBadge({
  status,
  size = "md",
  className = "",
}: ComplianceStatusBadgeProps): React.ReactElement {
  const config = statusConfig[status];

  return (
    <Badge
      variant="outline"
      className={`${config.className} ${sizeClasses[size]} font-medium ${className}`}
      aria-label={`Compliance status: ${config.label}`}
    >
      <span className="mr-1" aria-hidden="true">
        {config.icon}
      </span>
      {config.label}
    </Badge>
  );
}

export default ComplianceStatusBadge;
