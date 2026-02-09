/**
 * useApprovalActions hook.
 *
 * Provides mutation functions for approval workflow actions:
 * - Approve: Move content to scheduled queue
 * - Reject: Archive with rejection reason
 * - Edit: Update caption with auto-revalidation
 *
 * Features:
 * - Optimistic updates for smooth UX
 * - Error recovery and rollback
 * - Auto-refresh queue after actions
 * - Loading state management per action
 */

import { useState, useCallback } from "react";
import { useSWRConfig } from "swr";
import {
  ApprovalActionType,
  ApprovalActionResponse,
  ApproveActionRequest,
  RejectActionRequest,
  EditActionRequest,
  RevalidationResult,
} from "@/types/approval";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

export interface UseApprovalActionsResult {
  approve: (itemId: string, request?: ApproveActionRequest) => Promise<ApprovalActionResponse>;
  reject: (itemId: string, request: RejectActionRequest) => Promise<ApprovalActionResponse>;
  edit: (itemId: string, request: EditActionRequest) => Promise<ApprovalActionResponse>;
  revalidate: (itemId: string) => Promise<RevalidationResult>;
  applyRewrite: (itemId: string, suggestionIds: string[]) => Promise<ApprovalActionResponse>;
  isLoading: boolean;
  loadingAction: ApprovalActionType | null;
  error: Error | null;
  clearError: () => void;
}

/**
 * Hook for executing approval workflow actions.
 *
 * @returns Action functions and state management utilities
 */
export function useApprovalActions(): UseApprovalActionsResult {
  const { mutate } = useSWRConfig();
  const [isLoading, setIsLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState<ApprovalActionType | null>(null);
  const [error, setError] = useState<Error | null>(null);

  /**
   * Refresh the approval queue after an action.
   */
  const refreshQueue = useCallback(() => {
    // Revalidate all approval queue queries
    mutate((key: string) => typeof key === "string" && key.includes("/approval-queue"));
  }, [mutate]);

  /**
   * Execute an API request with error handling.
   */
  const executeAction = useCallback(
    async <T>(
      action: ApprovalActionType,
      url: string,
      method: string,
      body?: object
    ): Promise<T> => {
      setIsLoading(true);
      setLoadingAction(action);
      setError(null);

      try {
        const response = await fetch(url, {
          method,
          headers: {
            "Content-Type": "application/json",
          },
          body: body ? JSON.stringify(body) : undefined,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Action failed: ${response.statusText}`);
        }

        const data = await response.json();
        refreshQueue();
        return data;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Unknown error occurred");
        setError(error);
        throw error;
      } finally {
        setIsLoading(false);
        setLoadingAction(null);
      }
    },
    [refreshQueue]
  );

  /**
   * Approve an item and move to scheduled queue.
   */
  const approve = useCallback(
    async (
      itemId: string,
      request: ApproveActionRequest = {}
    ): Promise<ApprovalActionResponse> => {
      return executeAction<ApprovalActionResponse>(
        "approve",
        `${API_BASE}/approval-queue/${itemId}/approve`,
        "POST",
        request
      );
    },
    [executeAction]
  );

  /**
   * Reject an item with a reason.
   */
  const reject = useCallback(
    async (
      itemId: string,
      request: RejectActionRequest
    ): Promise<ApprovalActionResponse> => {
      // Validate reason_text is provided when reason is OTHER
      if (request.reason === "other" && !request.reason_text?.trim()) {
        throw new Error("Please provide a reason when selecting 'Other'");
      }

      return executeAction<ApprovalActionResponse>(
        "reject",
        `${API_BASE}/approval-queue/${itemId}/reject`,
        "POST",
        request
      );
    },
    [executeAction]
  );

  /**
   * Edit caption and trigger revalidation.
   */
  const edit = useCallback(
    async (
      itemId: string,
      request: EditActionRequest
    ): Promise<ApprovalActionResponse> => {
      // Validate caption is not empty
      if (!request.caption?.trim()) {
        throw new Error("Caption cannot be empty");
      }

      return executeAction<ApprovalActionResponse>(
        "edit",
        `${API_BASE}/approval-queue/${itemId}/edit`,
        "PUT",
        request
      );
    },
    [executeAction]
  );

  /**
   * Manually trigger revalidation for an item.
   */
  const revalidate = useCallback(
    async (itemId: string): Promise<RevalidationResult> => {
      return executeAction<RevalidationResult>(
        "revalidate",
        `${API_BASE}/approval-queue/${itemId}/revalidate`,
        "POST"
      );
    },
    [executeAction]
  );

  /**
   * Apply AI rewrite suggestions to an item.
   */
  const applyRewrite = useCallback(
    async (
      itemId: string,
      suggestionIds: string[]
    ): Promise<ApprovalActionResponse> => {
      return executeAction<ApprovalActionResponse>(
        "edit",
        `${API_BASE}/approval-queue/${itemId}/apply-rewrite`,
        "PUT",
        { suggestion_ids: suggestionIds }
      );
    },
    [executeAction]
  );

  /**
   * Clear the current error state.
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    approve,
    reject,
    edit,
    revalidate,
    applyRewrite,
    isLoading,
    loadingAction,
    error,
    clearError,
  };
}

export default useApprovalActions;
