/**
 * Toast components.
 *
 * Story 4-3: Task 7 - Success/error feedback for batch operations
 *
 * Features:
 * - Toast notification display
 * - Auto-dismiss with configurable duration
 * - Retry action for error toasts
 * - Stacked notifications
 */

import React from "react";
import { Toast as ToastType } from "@/hooks/useToast";
import { Button } from "@/components/ui/button";

export interface ToastProps extends ToastType {
  onDismiss: (id: string) => void;
}

/**
 * Get icon and colors for toast type.
 */
function getToastStyles(type: ToastType["type"]): {
  icon: string;
  bgClass: string;
  borderClass: string;
  textClass: string;
} {
  switch (type) {
    case "success":
      return {
        icon: "\u2713",
        bgClass: "bg-green-50",
        borderClass: "border-green-200",
        textClass: "text-green-800",
      };
    case "error":
      return {
        icon: "\u2717",
        bgClass: "bg-red-50",
        borderClass: "border-red-200",
        textClass: "text-red-800",
      };
    case "warning":
      return {
        icon: "\u26A0",
        bgClass: "bg-yellow-50",
        borderClass: "border-yellow-200",
        textClass: "text-yellow-800",
      };
    case "info":
    default:
      return {
        icon: "\u2139",
        bgClass: "bg-blue-50",
        borderClass: "border-blue-200",
        textClass: "text-blue-800",
      };
  }
}

/**
 * Individual toast notification.
 */
export function Toast({
  id,
  type,
  title,
  message,
  action,
  onDismiss,
}: ToastProps): React.ReactElement {
  const styles = getToastStyles(type);

  return (
    <div
      className={`${styles.bgClass} ${styles.borderClass} border rounded-lg p-4 shadow-lg min-w-[300px] max-w-[400px] animate-in slide-in-from-right-5 duration-200`}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <span className={`text-lg ${styles.textClass}`}>{styles.icon}</span>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className={`font-medium ${styles.textClass}`}>{title}</p>
          {message && (
            <p className={`text-sm mt-1 ${styles.textClass} opacity-90`}>
              {message}
            </p>
          )}

          {/* Action button (e.g., Retry) */}
          {action && (
            <Button
              variant="ghost"
              size="sm"
              className={`mt-2 ${styles.textClass} hover:bg-opacity-20`}
              onClick={() => {
                action.onClick();
                onDismiss(id);
              }}
            >
              {action.label}
            </Button>
          )}
        </div>

        {/* Dismiss button */}
        <button
          type="button"
          className={`${styles.textClass} opacity-70 hover:opacity-100`}
          onClick={() => onDismiss(id)}
          aria-label="Dismiss"
        >
          {"\u2715"}
        </button>
      </div>
    </div>
  );
}

export interface ToastContainerProps {
  toasts: ToastType[];
  onDismiss: (id: string) => void;
}

/**
 * Container for stacked toast notifications.
 */
export function ToastContainer({
  toasts,
  onDismiss,
}: ToastContainerProps): React.ReactElement | null {
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

export default Toast;
