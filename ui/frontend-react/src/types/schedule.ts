/**
 * TypeScript types for Content Scheduling Interface.
 *
 * Story 4-4: Calendar-based scheduling with drag-and-drop,
 * optimal time suggestions, and conflict detection.
 */

import { SourcePriority, ComplianceStatus, QualityColor } from "./approval";

/**
 * Publish status values.
 * Story 4-5: Publishing status tracking.
 */
export type PublishStatus =
  | "scheduled"
  | "publishing"
  | "published"
  | "publish_failed";

/**
 * Scheduled item for calendar display.
 * Optimized for calendar rendering with minimal data.
 */
export interface ScheduledItem {
  id: string;
  title: string; // Truncated caption for calendar display
  thumbnail_url: string;
  scheduled_publish_time: string; // ISO datetime
  source_type: string;
  source_priority: SourcePriority;
  quality_score: number;
  quality_color: QualityColor;
  compliance_status: ComplianceStatus;
  conflicts: string[]; // IDs of conflicting items
  is_imminent: boolean; // < 1 hour to publish
  // Story 4-5: Publishing status fields
  status?: PublishStatus;
  instagram_permalink?: string;
  published_at?: string;
  publish_error?: string;
}

/**
 * Calendar event for react-big-calendar.
 */
export interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  resource: ScheduledItem;
}

/**
 * Suggested optimal publish time slot.
 */
export interface OptimalTimeSlot {
  time: string; // ISO datetime
  score: number; // 0-1 score
  reasoning: string; // "Peak engagement time, no conflicts"
}

/**
 * Response for optimal time suggestions API.
 */
export interface OptimalTimesResponse {
  item_id: string;
  suggestions: OptimalTimeSlot[];
}

/**
 * Request to reschedule a post.
 */
export interface RescheduleRequest {
  new_publish_time: string; // ISO datetime
  force?: boolean; // Override imminent lock
}

/**
 * Response from reschedule API.
 */
export interface RescheduleResponse {
  success: boolean;
  message: string;
  item_id: string;
  new_publish_time: string;
  conflicts?: ConflictInfo[];
}

/**
 * Conflict information for a time slot.
 */
export interface ConflictInfo {
  hour: string; // ISO datetime (hour)
  posts_count: number;
  post_ids: string[];
  severity: ConflictSeverity;
}

/**
 * Conflict severity levels.
 */
export type ConflictSeverity = "warning" | "critical";

/**
 * Calendar response from API.
 */
export interface ScheduleCalendarResponse {
  items: ScheduledItem[];
  conflicts: ConflictInfo[];
  date_range: {
    start: string;
    end: string;
  };
}

/**
 * Calendar view type.
 */
export type CalendarView = "day" | "week" | "month";

/**
 * Source type color mapping for calendar events.
 */
export const SOURCE_TYPE_COLORS: Record<string, string> = {
  trending: "bg-red-500", // Urgent trending content
  scheduled: "bg-blue-500", // Pre-scheduled content
  evergreen: "bg-green-500", // Flexible timing
  research: "bg-purple-500", // Research-based
  instagram_post: "bg-pink-500", // Instagram posts
};

/**
 * Get color class for a source type.
 */
export function getSourceTypeColor(sourceType: string): string {
  return SOURCE_TYPE_COLORS[sourceType] || "bg-gray-500";
}

/**
 * Check if a scheduled item is imminent (within 1 hour).
 */
export function isImminent(scheduledTime: string | Date): boolean {
  const scheduled = typeof scheduledTime === "string"
    ? new Date(scheduledTime)
    : scheduledTime;
  const now = new Date();
  const diffMs = scheduled.getTime() - now.getTime();
  const oneHourMs = 60 * 60 * 1000;
  return diffMs > 0 && diffMs < oneHourMs;
}

/**
 * Check if a scheduled item is in the past.
 */
export function isPastSchedule(scheduledTime: string | Date): boolean {
  const scheduled = typeof scheduledTime === "string"
    ? new Date(scheduledTime)
    : scheduledTime;
  return scheduled.getTime() < Date.now();
}

/**
 * Conflict rules constants.
 */
export const CONFLICT_RULES = {
  MAX_POSTS_PER_HOUR: 2,
  MAX_POSTS_PER_DAY: 8,
  WARNING_THRESHOLD: 2, // Show warning at this count
  CRITICAL_THRESHOLD: 3, // Show critical at this count
} as const;

/**
 * Get conflict severity based on post count.
 */
export function getConflictSeverity(postsCount: number): ConflictSeverity | null {
  if (postsCount >= CONFLICT_RULES.CRITICAL_THRESHOLD) return "critical";
  if (postsCount >= CONFLICT_RULES.WARNING_THRESHOLD) return "warning";
  return null;
}

/**
 * Request to retry a failed publish.
 * Story 4-5, Task 6.
 */
export interface RetryPublishRequest {
  force?: boolean;
}

/**
 * Response from retry publish API.
 * Story 4-5, Task 6.
 */
export interface RetryPublishResponse {
  success: boolean;
  message: string;
  item_id: string;
  job_id?: string;
  scheduled_for?: string;
}

/**
 * Publish status color mapping.
 * Story 4-5, Task 7.1.
 */
export const PUBLISH_STATUS_COLORS: Record<PublishStatus, string> = {
  scheduled: "bg-blue-500",
  publishing: "bg-yellow-500",
  published: "bg-green-500",
  publish_failed: "bg-red-500",
};

/**
 * Publish status display labels.
 */
export const PUBLISH_STATUS_LABELS: Record<PublishStatus, string> = {
  scheduled: "Scheduled",
  publishing: "Publishing...",
  published: "Published",
  publish_failed: "Failed",
};

/**
 * Get color class for publish status.
 */
export function getPublishStatusColor(status?: PublishStatus): string {
  return status ? PUBLISH_STATUS_COLORS[status] : "bg-gray-500";
}

/**
 * Get label for publish status.
 */
export function getPublishStatusLabel(status?: PublishStatus): string {
  return status ? PUBLISH_STATUS_LABELS[status] : "Unknown";
}

/**
 * Check if an item can be retried.
 */
export function canRetryPublish(status?: PublishStatus): boolean {
  return status === "publish_failed";
}

