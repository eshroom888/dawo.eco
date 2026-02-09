/**
 * OptimalTimesSuggestion component.
 *
 * Story 4-4, Task 5.4: Display optimal time suggestions with "Apply" button.
 *
 * Shows top 3 suggested publish times based on:
 * - Instagram peak engagement hours
 * - Conflict avoidance (existing scheduled posts)
 * - Historical engagement data (when available)
 *
 * Features:
 * - Score visualization (progress bar)
 * - Human-readable reasoning
 * - One-click apply button
 * - Loading and error states
 */

import React from "react";
import { OptimalTimeSlot } from "@/types/schedule";
import { cn } from "@/lib/utils";

export interface OptimalTimesSuggestionProps {
  /** List of optimal time suggestions */
  suggestions: OptimalTimeSlot[];
  /** Loading state */
  isLoading?: boolean;
  /** Error message */
  error?: string | null;
  /** Callback when a time is selected */
  onApply: (time: Date) => void;
  /** Currently selected time (for highlighting) */
  selectedTime?: Date | null;
  /** Whether apply action is in progress */
  isApplying?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Get score color based on value.
 */
function getScoreColor(score: number): string {
  if (score >= 0.8) return "bg-green-500";
  if (score >= 0.6) return "bg-yellow-500";
  return "bg-orange-500";
}

/**
 * Format time for display.
 */
function formatTime(date: Date): string {
  return date.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/**
 * Format date for display.
 */
function formatDate(date: Date): string {
  return date.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

/**
 * Component displaying optimal publish time suggestions.
 *
 * Story 4-4, Task 5.4: Optimal time suggestions with Apply button.
 */
export function OptimalTimesSuggestion({
  suggestions,
  isLoading = false,
  error = null,
  onApply,
  selectedTime = null,
  isApplying = false,
  className,
}: OptimalTimesSuggestionProps): React.ReactElement {
  // Loading state
  if (isLoading) {
    return (
      <div
        className={cn("space-y-2", className)}
        data-testid="optimal-times-loading"
      >
        <div className="text-sm font-medium text-gray-700">
          Calculating optimal times...
        </div>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 bg-gray-100 animate-pulse rounded-lg"
            />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className={cn("p-3 bg-red-50 border border-red-200 rounded-lg", className)}
        data-testid="optimal-times-error"
      >
        <div className="text-sm text-red-700">{error}</div>
      </div>
    );
  }

  // Empty state
  if (suggestions.length === 0) {
    return (
      <div
        className={cn("p-3 bg-gray-50 rounded-lg text-sm text-gray-500", className)}
        data-testid="optimal-times-empty"
      >
        No time suggestions available
      </div>
    );
  }

  return (
    <div
      className={cn("space-y-2", className)}
      data-testid="optimal-times-suggestion"
    >
      <div className="text-sm font-medium text-gray-700 flex items-center gap-2">
        <span className="w-4 h-4 text-yellow-500">&#9733;</span>
        Suggested Times
      </div>

      <div className="space-y-2">
        {suggestions.map((slot, index) => {
          const slotTime = new Date(slot.time);
          const isSelected =
            selectedTime &&
            slotTime.getTime() === selectedTime.getTime();

          return (
            <div
              key={index}
              className={cn(
                "p-3 rounded-lg border transition-colors",
                isSelected
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 bg-white hover:border-gray-300"
              )}
              data-testid={`optimal-time-slot-${index}`}
            >
              <div className="flex items-center justify-between gap-3">
                {/* Time and date */}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-900">
                    {formatTime(slotTime)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatDate(slotTime)}
                  </div>
                </div>

                {/* Score bar */}
                <div className="w-20">
                  <div className="flex items-center gap-1">
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all",
                          getScoreColor(slot.score)
                        )}
                        style={{ width: `${slot.score * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 w-8 text-right">
                      {Math.round(slot.score * 100)}%
                    </span>
                  </div>
                </div>

                {/* Apply button */}
                <button
                  onClick={() => onApply(slotTime)}
                  disabled={isApplying || isSelected}
                  className={cn(
                    "px-3 py-1 text-sm rounded-md transition-colors",
                    isSelected
                      ? "bg-blue-500 text-white cursor-default"
                      : "bg-gray-100 hover:bg-gray-200 text-gray-700",
                    isApplying && "opacity-50 cursor-not-allowed"
                  )}
                  data-testid={`apply-time-${index}`}
                >
                  {isSelected ? "Selected" : "Apply"}
                </button>
              </div>

              {/* Reasoning */}
              <div className="mt-2 text-xs text-gray-500">
                {slot.reasoning}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default OptimalTimesSuggestion;
