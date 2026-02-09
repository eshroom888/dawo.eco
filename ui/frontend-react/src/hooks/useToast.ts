/**
 * useToast hook.
 *
 * Provides toast notification functionality for the application.
 * Supports success, error, warning, and info toast types.
 *
 * Story 4-3: Task 7 - Success/error feedback for batch operations
 */

import { useState, useCallback, useRef, useEffect } from "react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface UseToastReturn {
  /** Current list of active toasts */
  toasts: Toast[];
  /** Show a toast notification */
  showToast: (toast: Omit<Toast, "id">) => string;
  /** Show a success toast */
  success: (title: string, message?: string) => string;
  /** Show an error toast with optional retry action */
  error: (title: string, message?: string, onRetry?: () => void) => string;
  /** Show a warning toast */
  warning: (title: string, message?: string) => string;
  /** Show an info toast */
  info: (title: string, message?: string) => string;
  /** Dismiss a specific toast */
  dismiss: (id: string) => void;
  /** Dismiss all toasts */
  dismissAll: () => void;
}

// Default duration in ms
const DEFAULT_DURATION = 5000;
const ERROR_DURATION = 8000;

let toastIdCounter = 0;

/**
 * Hook for managing toast notifications.
 *
 * @example
 * ```tsx
 * const { success, error } = useToast();
 *
 * // Show success toast
 * success("Items approved", "5 items approved, scheduled for Feb 10 - Feb 15");
 *
 * // Show error with retry
 * error("Batch failed", "2 items failed", () => retryBatch());
 * ```
 */
export function useToast(): UseToastReturn {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      timers.current.forEach((timer) => clearTimeout(timer));
    };
  }, []);

  const dismiss = useCallback((id: string) => {
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    timers.current.forEach((timer) => clearTimeout(timer));
    timers.current.clear();
    setToasts([]);
  }, []);

  const showToast = useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = `toast-${++toastIdCounter}`;
      const duration = toast.duration ?? DEFAULT_DURATION;

      setToasts((prev) => [...prev, { ...toast, id }]);

      // Auto-dismiss after duration
      if (duration > 0) {
        const timer = setTimeout(() => dismiss(id), duration);
        timers.current.set(id, timer);
      }

      return id;
    },
    [dismiss]
  );

  const success = useCallback(
    (title: string, message?: string) => {
      return showToast({ type: "success", title, message });
    },
    [showToast]
  );

  const error = useCallback(
    (title: string, message?: string, onRetry?: () => void) => {
      return showToast({
        type: "error",
        title,
        message,
        duration: ERROR_DURATION,
        action: onRetry ? { label: "Retry", onClick: onRetry } : undefined,
      });
    },
    [showToast]
  );

  const warning = useCallback(
    (title: string, message?: string) => {
      return showToast({ type: "warning", title, message });
    },
    [showToast]
  );

  const info = useCallback(
    (title: string, message?: string) => {
      return showToast({ type: "info", title, message });
    },
    [showToast]
  );

  return {
    toasts,
    showToast,
    success,
    error,
    warning,
    info,
    dismiss,
    dismissAll,
  };
}

export default useToast;
