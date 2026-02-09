/**
 * RetryButton component.
 *
 * Story 4-5, Task 7.6: Retry button for failed posts.
 * Calls POST /api/schedule/{item_id}/retry-publish.
 */

import React, { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { RetryPublishRequest, RetryPublishResponse } from "@/types/schedule";

export interface RetryButtonProps {
  /** Item ID to retry */
  itemId: string;
  /** Button size variant */
  size?: "sm" | "md" | "lg";
  /** Optional CSS classes */
  className?: string;
  /** Callback after successful retry */
  onRetrySuccess?: (response: RetryPublishResponse) => void;
  /** Callback after retry error */
  onRetryError?: (error: Error) => void;
}

/**
 * Button to retry publishing a failed post.
 *
 * Shows loading state during retry and handles errors gracefully.
 */
export function RetryButton({
  itemId,
  size = "sm",
  className,
  onRetrySuccess,
  onRetryError,
}: RetryButtonProps): React.ReactElement {
  const [isRetrying, setIsRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRetry = useCallback(async () => {
    setIsRetrying(true);
    setError(null);

    try {
      const request: RetryPublishRequest = { force: false };

      const response = await fetch(`/api/schedule/${itemId}/retry-publish`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Retry failed: ${response.status}`);
      }

      const data: RetryPublishResponse = await response.json();

      if (data.success) {
        onRetrySuccess?.(data);
      } else {
        throw new Error(data.message || "Retry failed");
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error.message);
      onRetryError?.(error);
    } finally {
      setIsRetrying(false);
    }
  }, [itemId, onRetrySuccess, onRetryError]);

  const sizeClasses = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1.5 text-sm",
    lg: "px-4 py-2 text-base",
  };

  return (
    <div className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={handleRetry}
        disabled={isRetrying}
        className={cn(
          "inline-flex items-center gap-1 rounded font-medium",
          "bg-orange-500 hover:bg-orange-600 text-white",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "transition-colors duration-150",
          sizeClasses[size],
          className
        )}
        data-testid={`retry-button-${itemId}`}
      >
        {isRetrying ? (
          <>
            <svg
              className="w-4 h-4 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Retrying...</span>
          </>
        ) : (
          <>
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>Retry</span>
          </>
        )}
      </button>
      {error && (
        <span className="text-xs text-red-500" data-testid="retry-error">
          {error}
        </span>
      )}
    </div>
  );
}

export default RetryButton;
