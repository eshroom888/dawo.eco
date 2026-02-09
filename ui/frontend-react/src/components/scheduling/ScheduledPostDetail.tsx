/**
 * ScheduledPostDetail component.
 *
 * Story 4-4, Task 5: Post detail popup/sidebar for calendar item click.
 *
 * Displays:
 * - Thumbnail and caption preview
 * - Quality score and compliance status
 * - Time picker for manual adjustment
 * - Optimal time suggestions with "Apply" button
 * - Conflict warnings
 * - Unschedule button
 */

import React, { useState, useCallback } from "react";
import { ScheduledItem, OptimalTimeSlot } from "@/types/schedule";
import { QualityColor, ComplianceStatus } from "@/types/approval";
import { PublishingSoonBadge } from "./PublishingSoonBadge";
import { ConflictWarning } from "./ConflictWarning";
import { useOptimalTimes } from "@/hooks/useOptimalTimes";
import { cn } from "@/lib/utils";

export interface ScheduledPostDetailProps {
  /** The scheduled item to display */
  item: ScheduledItem;
  /** Whether the panel is open */
  isOpen: boolean;
  /** Close the panel */
  onClose: () => void;
  /** Callback when time is changed */
  onReschedule: (newTime: Date) => Promise<void>;
  /** Callback when item is unscheduled */
  onUnschedule?: () => Promise<void>;
  /** Loading state for actions */
  isLoading?: boolean;
}

const QUALITY_COLORS: Record<QualityColor, string> = {
  green: "bg-green-100 text-green-800",
  yellow: "bg-yellow-100 text-yellow-800",
  red: "bg-red-100 text-red-800",
};

const COMPLIANCE_COLORS: Record<string, string> = {
  COMPLIANT: "bg-green-100 text-green-800",
  WARNING: "bg-yellow-100 text-yellow-800",
  REJECTED: "bg-red-100 text-red-800",
};

/**
 * Detail panel for a scheduled post.
 *
 * Shows when user clicks on a calendar event, providing
 * detailed information and scheduling controls.
 */
export function ScheduledPostDetail({
  item,
  isOpen,
  onClose,
  onReschedule,
  onUnschedule,
  isLoading = false,
}: ScheduledPostDetailProps): React.ReactElement | null {
  const [selectedTime, setSelectedTime] = useState<Date>(
    new Date(item.scheduled_publish_time)
  );
  const [showTimePicker, setShowTimePicker] = useState(false);

  // Fetch optimal time suggestions
  const targetDate = new Date(item.scheduled_publish_time);
  const { suggestions, isLoading: suggestionsLoading } = useOptimalTimes(
    targetDate,
    item.id
  );

  // Handle time change
  const handleTimeChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const [hours, minutes] = e.target.value.split(":").map(Number);
      const newTime = new Date(selectedTime);
      newTime.setHours(hours, minutes, 0, 0);
      setSelectedTime(newTime);
    },
    [selectedTime]
  );

  // Apply selected time
  const handleApplyTime = useCallback(async () => {
    await onReschedule(selectedTime);
    setShowTimePicker(false);
  }, [selectedTime, onReschedule]);

  // Apply optimal time suggestion
  const handleApplySuggestion = useCallback(
    async (suggestion: OptimalTimeSlot) => {
      const newTime = new Date(suggestion.time);
      await onReschedule(newTime);
    },
    [onReschedule]
  );

  if (!isOpen) return null;

  const publishTime = new Date(item.scheduled_publish_time);

  return (
    <div
      className="fixed inset-y-0 right-0 w-96 bg-white shadow-xl z-50 overflow-y-auto"
      data-testid="scheduled-post-detail"
    >
      {/* Header */}
      <div className="sticky top-0 bg-white border-b p-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Post Details</h2>
        <button
          onClick={onClose}
          className="p-2 hover:bg-gray-100 rounded"
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* Thumbnail */}
        <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
          <img
            src={item.thumbnail_url}
            alt="Post thumbnail"
            className="w-full h-full object-cover"
          />
        </div>

        {/* Caption preview */}
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-1">Caption</h3>
          <p className="text-sm text-gray-900 line-clamp-4">{item.title}</p>
        </div>

        {/* Status badges */}
        <div className="flex flex-wrap gap-2">
          {/* Quality score */}
          <span
            className={cn(
              "px-2 py-1 text-xs font-medium rounded",
              QUALITY_COLORS[item.quality_color]
            )}
          >
            Quality: {item.quality_score.toFixed(1)}
          </span>

          {/* Compliance status */}
          <span
            className={cn(
              "px-2 py-1 text-xs font-medium rounded",
              COMPLIANCE_COLORS[item.compliance_status]
            )}
          >
            {item.compliance_status}
          </span>

          {/* Imminent indicator */}
          {item.is_imminent && <PublishingSoonBadge />}
        </div>

        {/* Conflict warnings */}
        {item.conflicts.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
            <div className="text-sm font-medium text-yellow-800 mb-1">
              ⚠️ Scheduling Conflict
            </div>
            <div className="text-sm text-yellow-700">
              {item.conflicts.length} other post(s) scheduled at the same hour.
            </div>
          </div>
        )}

        {/* Scheduled time */}
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-2">
            Scheduled Time
          </h3>
          <div className="flex items-center justify-between bg-gray-50 rounded p-3">
            <div>
              <div className="font-medium">
                {publishTime.toLocaleDateString(undefined, {
                  weekday: "long",
                  month: "short",
                  day: "numeric",
                })}
              </div>
              <div className="text-sm text-gray-600">
                {publishTime.toLocaleTimeString(undefined, {
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </div>
            </div>
            <button
              onClick={() => setShowTimePicker(!showTimePicker)}
              className="px-3 py-1 text-sm bg-white border rounded hover:bg-gray-50"
              disabled={item.is_imminent || isLoading}
            >
              Change
            </button>
          </div>

          {/* Time picker */}
          {showTimePicker && !item.is_imminent && (
            <div className="mt-3 p-3 bg-gray-50 rounded space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  New time
                </label>
                <input
                  type="time"
                  value={`${selectedTime.getHours().toString().padStart(2, "0")}:${selectedTime.getMinutes().toString().padStart(2, "0")}`}
                  onChange={handleTimeChange}
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleApplyTime}
                  disabled={isLoading}
                  className="flex-1 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {isLoading ? "Saving..." : "Apply"}
                </button>
                <button
                  onClick={() => setShowTimePicker(false)}
                  className="px-3 py-2 bg-gray-100 rounded hover:bg-gray-200"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Optimal time suggestions */}
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-2">
            Optimal Times
          </h3>
          {suggestionsLoading ? (
            <div className="text-sm text-gray-500">Loading suggestions...</div>
          ) : suggestions.length > 0 ? (
            <div className="space-y-2">
              {suggestions.map((suggestion, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 bg-gray-50 rounded"
                >
                  <div>
                    <div className="font-medium text-sm">
                      {new Date(suggestion.time).toLocaleTimeString(undefined, {
                        hour: "numeric",
                        minute: "2-digit",
                      })}
                    </div>
                    <div className="text-xs text-gray-500">
                      {suggestion.reasoning}
                    </div>
                  </div>
                  <button
                    onClick={() => handleApplySuggestion(suggestion)}
                    disabled={item.is_imminent || isLoading}
                    className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded hover:bg-green-200 disabled:opacity-50"
                  >
                    Apply
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-gray-500">No suggestions available</div>
          )}
        </div>

        {/* Actions */}
        <div className="border-t pt-4 space-y-2">
          {onUnschedule && (
            <button
              onClick={onUnschedule}
              disabled={item.is_imminent || isLoading}
              className="w-full px-4 py-2 text-red-600 border border-red-200 rounded hover:bg-red-50 disabled:opacity-50"
            >
              Unschedule
            </button>
          )}
          <a
            href={`/approval/${item.id}`}
            className="block w-full px-4 py-2 text-center text-gray-600 border rounded hover:bg-gray-50"
          >
            View Full Details
          </a>
        </div>
      </div>
    </div>
  );
}

export default ScheduledPostDetail;
