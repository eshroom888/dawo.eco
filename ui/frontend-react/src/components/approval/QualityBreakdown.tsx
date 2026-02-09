/**
 * QualityBreakdown component.
 *
 * Displays quality score breakdown by factor with:
 * - Each factor with its weight percentage
 * - Individual scores with progress bars
 * - Highlighting for low-scoring factors
 */

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { QualityBreakdown as QualityBreakdownType, QUALITY_FACTORS, getQualityColor } from "@/types/approval";
import { QualityScoreBadge } from "./QualityScoreBadge";

export interface QualityBreakdownProps {
  breakdown: QualityBreakdownType;
  overallScore: number;
  className?: string;
}

/**
 * Get color class for progress bar based on score.
 */
function getProgressColor(score: number): string {
  if (score >= 8) return "bg-green-500";
  if (score >= 5) return "bg-yellow-500";
  return "bg-red-500";
}

/**
 * Check if a score is low (needs attention).
 */
function isLowScore(score: number): boolean {
  return score < 5;
}

/**
 * Individual quality factor row.
 */
function QualityFactorRow({
  label,
  weight,
  score,
}: {
  label: string;
  weight: number;
  score: number;
}): React.ReactElement {
  const isLow = isLowScore(score);
  const progressValue = (score / 10) * 100;

  return (
    <div className={`p-3 rounded-lg ${isLow ? "bg-red-50 border border-red-200" : "bg-gray-50"}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${isLow ? "text-red-700" : "text-gray-700"}`}>
            {label}
          </span>
          <span className="text-xs text-gray-400">({Math.round(weight * 100)}%)</span>
        </div>
        <span className={`text-sm font-semibold ${isLow ? "text-red-700" : "text-gray-900"}`}>
          {score.toFixed(1)}/10
        </span>
      </div>
      <div className="relative">
        <Progress
          value={progressValue}
          className="h-2"
        />
        <div
          className={`absolute inset-0 h-2 rounded-full ${getProgressColor(score)}`}
          style={{ width: `${progressValue}%` }}
        />
      </div>
      {isLow && (
        <p className="text-xs text-red-600 mt-1">
          {"\u26A0"} Needs improvement
        </p>
      )}
    </div>
  );
}

/**
 * Quality breakdown component with factor analysis.
 */
export function QualityBreakdown({
  breakdown,
  overallScore,
  className = "",
}: QualityBreakdownProps): React.ReactElement {
  // Build factors with scores
  const factors = QUALITY_FACTORS.map((factor) => ({
    ...factor,
    score: breakdown[factor.key],
  }));

  // Count low-scoring factors
  const lowScoreCount = factors.filter((f) => isLowScore(f.score)).length;

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center justify-between">
          <span>Quality Breakdown</span>
          <QualityScoreBadge score={overallScore} size="lg" />
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Summary */}
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            6 factors analyzed
            {lowScoreCount > 0 && (
              <span className="text-red-600 font-medium ml-1">
                ({lowScoreCount} need{lowScoreCount === 1 ? "s" : ""} attention)
              </span>
            )}
          </p>
        </div>

        {/* Factor rows */}
        <div className="space-y-3">
          {factors.map((factor) => (
            <QualityFactorRow
              key={factor.key}
              label={factor.label}
              weight={factor.weight}
              score={factor.score}
            />
          ))}
        </div>

        {/* Weighted calculation note */}
        <p className="text-xs text-gray-400 mt-4 text-center">
          Overall score is calculated as weighted average of all factors
        </p>
      </CardContent>
    </Card>
  );
}

export default QualityBreakdown;
