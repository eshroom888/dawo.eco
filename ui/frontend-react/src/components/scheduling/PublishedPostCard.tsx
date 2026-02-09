/**
 * PublishedPostCard component.
 *
 * Story 4-5, Task 7.2-7.7: Card showing published post details
 * with Instagram link, timestamp, and retry button for failures.
 */

import React from "react";
import { cn } from "@/lib/utils";
import { ScheduledItem, canRetryPublish } from "@/types/schedule";
import { PublishStatusBadge } from "./PublishStatusBadge";
import { RetryButton } from "./RetryButton";

export interface PublishedPostCardProps {
  /** Scheduled/published item data */
  item: ScheduledItem;
  /** Optional CSS classes */
  className?: string;
  /** Callback after successful retry */
  onRetrySuccess?: () => void;
}

/**
 * Card component for displaying published or failed post details.
 *
 * Features:
 * - Thumbnail preview
 * - Status badge with color coding
 * - Instagram permalink (if published)
 * - Published timestamp in local timezone
 * - Error message (if failed)
 * - Retry button (if failed)
 * - Green checkmark for successful publish
 */
export function PublishedPostCard({
  item,
  className,
  onRetrySuccess,
}: PublishedPostCardProps): React.ReactElement {
  const isPublished = item.status === "published";
  const isFailed = item.status === "publish_failed";

  // Format timestamp to local timezone
  const formatTimestamp = (isoString?: string): string => {
    if (!isoString) return "N/A";
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  };

  return (
    <div
      className={cn(
        "flex gap-3 p-3 bg-white border rounded-lg shadow-sm",
        isPublished && "border-green-200",
        isFailed && "border-red-200",
        className
      )}
      data-testid={`published-post-card-${item.id}`}
    >
      {/* Thumbnail */}
      <div className="relative flex-shrink-0">
        <img
          src={item.thumbnail_url}
          alt={item.title}
          className="w-16 h-16 object-cover rounded"
        />
        {/* Story 4-5, Task 7.7: Green checkmark for published */}
        {isPublished && (
          <div
            className="absolute -top-1 -right-1 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center"
            data-testid="published-checkmark"
          >
            <svg
              className="w-3 h-3 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-sm font-medium text-gray-900 truncate">
            {item.title}
          </h4>
          <PublishStatusBadge status={item.status} />
        </div>

        {/* Story 4-5, Task 7.3: Instagram permalink */}
        {isPublished && item.instagram_permalink && (
          <a
            href={item.instagram_permalink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-1 text-xs text-blue-600 hover:text-blue-800"
            data-testid="instagram-link"
          >
            <svg
              className="w-3 h-3"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073z"/>
            </svg>
            <span>View on Instagram</span>
            <svg
              className="w-3 h-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        )}

        {/* Story 4-5, Task 7.4: Publish timestamp */}
        {item.published_at && (
          <p className="mt-1 text-xs text-gray-500">
            Published: {formatTimestamp(item.published_at)}
          </p>
        )}

        {/* Error message for failed posts */}
        {isFailed && item.publish_error && (
          <p
            className="mt-1 text-xs text-red-600"
            data-testid="publish-error"
          >
            Error: {item.publish_error}
          </p>
        )}

        {/* Story 4-5, Task 7.6: Retry button for failed posts */}
        {canRetryPublish(item.status) && (
          <div className="mt-2">
            <RetryButton
              itemId={item.id}
              size="sm"
              onRetrySuccess={onRetrySuccess}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default PublishedPostCard;
