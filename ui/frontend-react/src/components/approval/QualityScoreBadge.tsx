/**
 * QualityScoreBadge component.
 *
 * Displays quality score with color coding:
 * - Green: score >= 8 (high quality)
 * - Yellow: score >= 5 and < 8 (medium quality)
 * - Red: score < 5 (low quality)
 */

import React from "react";
import { Badge } from "@/components/ui/badge";
import { QualityColor, getQualityColor } from "@/types/approval";

export interface QualityScoreBadgeProps {
  score: number;
  showScore?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const colorClasses: Record<QualityColor, string> = {
  green: "bg-green-100 text-green-800 border-green-300 hover:bg-green-100",
  yellow: "bg-yellow-100 text-yellow-800 border-yellow-300 hover:bg-yellow-100",
  red: "bg-red-100 text-red-800 border-red-300 hover:bg-red-100",
};

const sizeClasses = {
  sm: "text-xs px-1.5 py-0.5",
  md: "text-sm px-2 py-1",
  lg: "text-base px-3 py-1.5",
};

/**
 * Quality score badge with color coding based on score value.
 */
export function QualityScoreBadge({
  score,
  showScore = true,
  size = "md",
  className = "",
}: QualityScoreBadgeProps): React.ReactElement {
  const color = getQualityColor(score);
  const displayScore = Math.round(score * 10) / 10;

  return (
    <Badge
      variant="outline"
      className={`${colorClasses[color]} ${sizeClasses[size]} font-medium ${className}`}
      aria-label={`Quality score: ${displayScore} out of 10`}
    >
      {showScore ? displayScore.toFixed(1) : color}
    </Badge>
  );
}

export default QualityScoreBadge;
