/**
 * useBatchApproval hook tests.
 *
 * Story 4-3: Batch Approval Capability
 * Task 8: Create useBatchApproval hook
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useBatchApproval, BatchActionResult } from "../useBatchApproval";
import { UseToastReturn } from "../useToast";
import {
  ApprovalQueueItem,
  SourcePriority,
  ComplianceStatus,
  RejectReason,
} from "@/types/approval";

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock SWR mutate
vi.mock("swr", () => ({
  mutate: vi.fn(),
}));

// Create mock items
const createMockItem = (id: string): ApprovalQueueItem => ({
  id,
  thumbnail_url: "https://example.com/thumb.jpg",
  caption_excerpt: "Test caption",
  full_caption: "Full test caption",
  quality_score: 9.0,
  quality_color: "green",
  compliance_status: ComplianceStatus.COMPLIANT,
  would_auto_publish: true,
  suggested_publish_time: "2026-02-10T10:00:00Z",
  source_type: "instagram_post",
  source_priority: SourcePriority.TRENDING,
  hashtags: ["test"],
  created_at: "2026-02-08T12:00:00Z",
});

const mockItems: ApprovalQueueItem[] = [
  createMockItem("item-1"),
  createMockItem("item-2"),
  createMockItem("item-3"),
];

const createMockToast = (): UseToastReturn => ({
  toasts: [],
  showToast: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
  dismiss: vi.fn(),
  dismissAll: vi.fn(),
});

describe("useBatchApproval", () => {
  let mockToast: UseToastReturn;
  let mockOnSuccess: ReturnType<typeof vi.fn>;
  let mockOnItemsRemoved: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockToast = createMockToast();
    mockOnSuccess = vi.fn();
    mockOnItemsRemoved = vi.fn();
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // Task 8.1: batchApprove mutation
  describe("Task 8.1: batchApprove", () => {
    it("sends batch approve request to API", async () => {
      const mockResult: BatchActionResult = {
        batch_id: "batch-123",
        total_requested: 3,
        successful_count: 3,
        failed_count: 0,
        results: [
          { item_id: "item-1", success: true, scheduled_publish_time: "2026-02-10T10:00:00Z" },
          { item_id: "item-2", success: true, scheduled_publish_time: "2026-02-11T10:00:00Z" },
          { item_id: "item-3", success: true, scheduled_publish_time: "2026-02-12T10:00:00Z" },
        ],
        summary: "3 items approved",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResult),
      });

      const { result } = renderHook(() =>
        useBatchApproval(mockToast, mockOnSuccess, mockOnItemsRemoved)
      );

      await act(async () => {
        await result.current.batchApprove(mockItems);
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/approval-queue/batch/approve",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ item_ids: ["item-1", "item-2", "item-3"] }),
        })
      );
    });

    it("shows success toast on successful approval", async () => {
      const mockResult: BatchActionResult = {
        batch_id: "batch-123",
        total_requested: 3,
        successful_count: 3,
        failed_count: 0,
        results: [
          { item_id: "item-1", success: true, scheduled_publish_time: "2026-02-10T10:00:00Z" },
          { item_id: "item-2", success: true, scheduled_publish_time: "2026-02-11T10:00:00Z" },
          { item_id: "item-3", success: true, scheduled_publish_time: "2026-02-12T10:00:00Z" },
        ],
        summary: "3 items approved",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResult),
      });

      const { result } = renderHook(() =>
        useBatchApproval(mockToast, mockOnSuccess, mockOnItemsRemoved)
      );

      await act(async () => {
        await result.current.batchApprove(mockItems);
      });

      expect(mockToast.success).toHaveBeenCalledWith(
        "3 items approved",
        expect.stringContaining("Feb")
      );
    });

    it("calls onItemsRemoved for optimistic update", async () => {
      const mockResult: BatchActionResult = {
        batch_id: "batch-123",
        total_requested: 3,
        successful_count: 3,
        failed_count: 0,
        results: [],
        summary: "3 items approved",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResult),
      });

      const { result } = renderHook(() =>
        useBatchApproval(mockToast, mockOnSuccess, mockOnItemsRemoved)
      );

      await act(async () => {
        await result.current.batchApprove(mockItems);
      });

      expect(mockOnItemsRemoved).toHaveBeenCalledWith(["item-1", "item-2", "item-3"]);
    });
  });

  // Task 8.2: Integration with useQueueSelection
  describe("Task 8.2: Loading states", () => {
    it("sets isLoading during operation", async () => {
      let resolvePromise: (value: BatchActionResult) => void;
      const promise = new Promise<BatchActionResult>((resolve) => {
        resolvePromise = resolve;
      });

      mockFetch.mockReturnValueOnce({
        ok: true,
        json: () => promise,
      });

      const { result } = renderHook(() =>
        useBatchApproval(mockToast, mockOnSuccess)
      );

      expect(result.current.isLoading).toBe(false);

      let approvePromise: Promise<BatchActionResult>;
      act(() => {
        approvePromise = result.current.batchApprove(mockItems);
      });

      expect(result.current.isLoading).toBe(true);

      await act(async () => {
        resolvePromise!({
          batch_id: "batch-123",
          total_requested: 3,
          successful_count: 3,
          failed_count: 0,
          results: [],
          summary: "",
        });
        await approvePromise;
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  // Task 8.4: Error handling with partial success
  describe("Task 8.4: Partial failure handling", () => {
    it("shows error toast for partial failures with retry action", async () => {
      const mockResult: BatchActionResult = {
        batch_id: "batch-123",
        total_requested: 3,
        successful_count: 2,
        failed_count: 1,
        results: [
          { item_id: "item-1", success: true },
          { item_id: "item-2", success: false, error_message: "Failed" },
          { item_id: "item-3", success: true },
        ],
        summary: "2 items approved, 1 failed",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResult),
      });

      const { result } = renderHook(() =>
        useBatchApproval(mockToast, mockOnSuccess)
      );

      await act(async () => {
        await result.current.batchApprove(mockItems);
      });

      expect(mockToast.error).toHaveBeenCalledWith(
        "1 item failed",
        "Some items could not be approved",
        expect.any(Function)
      );
    });
  });

  // Task 8.5: Progress indicator for large batches
  describe("Task 8.5: Progress indicator", () => {
    it("shows progress for 10+ items", async () => {
      const largeItems = Array.from({ length: 12 }, (_, i) =>
        createMockItem(`item-${i}`)
      );

      const mockResult: BatchActionResult = {
        batch_id: "batch-123",
        total_requested: 12,
        successful_count: 12,
        failed_count: 0,
        results: [],
        summary: "12 items approved",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResult),
      });

      const { result } = renderHook(() =>
        useBatchApproval(mockToast, mockOnSuccess)
      );

      let approvePromise: Promise<BatchActionResult>;
      act(() => {
        approvePromise = result.current.batchApprove(largeItems);
      });

      // Progress should be set for large batches
      expect(result.current.processingCount).toBe(12);

      await act(async () => {
        await approvePromise;
      });
    });
  });

  // Batch reject
  describe("batchReject", () => {
    it("sends batch reject request with reason", async () => {
      const mockResult: BatchActionResult = {
        batch_id: "batch-123",
        total_requested: 3,
        successful_count: 3,
        failed_count: 0,
        results: [],
        summary: "3 items rejected",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResult),
      });

      const { result } = renderHook(() =>
        useBatchApproval(mockToast, mockOnSuccess, mockOnItemsRemoved)
      );

      await act(async () => {
        await result.current.batchReject(mockItems, {
          reason: RejectReason.COMPLIANCE_ISSUE,
          reason_text: "Test reason",
        });
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/approval-queue/batch/reject",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            item_ids: ["item-1", "item-2", "item-3"],
            reason: RejectReason.COMPLIANCE_ISSUE,
            reason_text: "Test reason",
          }),
        })
      );
    });
  });
});
