/**
 * BatchApproveConfirmDialog component tests.
 *
 * Story 4-3: Batch Approval Capability
 * Task 6: Batch confirmation dialogs
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  BatchApproveConfirmDialog,
  BatchApproveConfirmDialogProps,
} from "../BatchApproveConfirmDialog";
import { ApprovalQueueItem, SourcePriority, ComplianceStatus } from "@/types/approval";

// Mock queue items for testing
const createMockItem = (
  id: string,
  suggestedTime: string | null,
  thumbnailUrl: string = "https://example.com/thumb.jpg"
): ApprovalQueueItem => ({
  id,
  thumbnail_url: thumbnailUrl,
  caption_excerpt: `Caption excerpt for ${id}`,
  full_caption: `Full caption for ${id}`,
  quality_score: 9.0,
  quality_color: "green",
  compliance_status: ComplianceStatus.COMPLIANT,
  would_auto_publish: true,
  suggested_publish_time: suggestedTime,
  source_type: "instagram_post",
  source_priority: SourcePriority.TRENDING,
  hashtags: ["test"],
  created_at: "2026-02-08T12:00:00Z",
});

const mockItems: ApprovalQueueItem[] = [
  createMockItem("item-1", "2026-02-10T10:00:00Z"),
  createMockItem("item-2", "2026-02-12T14:00:00Z"),
  createMockItem("item-3", "2026-02-15T09:00:00Z"),
  createMockItem("item-4", "2026-02-11T11:00:00Z"),
  createMockItem("item-5", "2026-02-13T16:00:00Z"),
];

describe("BatchApproveConfirmDialog", () => {
  let defaultProps: BatchApproveConfirmDialogProps;
  let mockOnConfirm: ReturnType<typeof vi.fn>;
  let mockOnCancel: ReturnType<typeof vi.fn>;
  let mockOnDontShowAgainChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnConfirm = vi.fn().mockResolvedValue(undefined);
    mockOnCancel = vi.fn();
    mockOnDontShowAgainChange = vi.fn();

    defaultProps = {
      isOpen: true,
      items: mockItems,
      onConfirm: mockOnConfirm,
      onCancel: mockOnCancel,
      isLoading: false,
      dontShowAgain: false,
      onDontShowAgainChange: mockOnDontShowAgainChange,
    };
  });

  // Task 6.1: Dialog shows summary before action
  describe("Task 6.1: Summary display", () => {
    it("renders the dialog when isOpen is true", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("does not render when isOpen is false", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("displays dialog title", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      expect(screen.getByRole("heading", { name: /confirm batch approval/i })).toBeInTheDocument();
    });
  });

  // Task 6.2: Display item count and date range
  describe("Task 6.2: Item count and date range", () => {
    it("displays the count of items to be approved", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      expect(screen.getByText(/5 items/i)).toBeInTheDocument();
    });

    it("displays the date range of scheduled posts", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      // Date range: Feb 10 - Feb 15
      expect(screen.getByText(/feb 10.*feb 15/i)).toBeInTheDocument();
    });

    it("handles single item date display", () => {
      const singleItem = [mockItems[0]];
      render(<BatchApproveConfirmDialog {...defaultProps} items={singleItem} />);
      expect(screen.getByText(/1 item/i)).toBeInTheDocument();
    });

    it("handles items without publish times", () => {
      const noTimeItems = [
        createMockItem("item-1", null),
        createMockItem("item-2", null),
      ];
      render(<BatchApproveConfirmDialog {...defaultProps} items={noTimeItems} />);
      expect(screen.getByText(/no scheduled times/i)).toBeInTheDocument();
    });
  });

  // Task 6.3: Show preview of first 3 items with thumbnails
  describe("Task 6.3: Item preview thumbnails", () => {
    it("shows thumbnails for first 3 items", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      const thumbnails = screen.getAllByRole("img");
      expect(thumbnails.length).toBe(3);
    });

    it("shows +N indicator when more than 3 items", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      expect(screen.getByText(/\+2 more/i)).toBeInTheDocument();
    });

    it("does not show +N indicator for 3 or fewer items", () => {
      const threeItems = mockItems.slice(0, 3);
      render(<BatchApproveConfirmDialog {...defaultProps} items={threeItems} />);
      expect(screen.queryByText(/\+.*more/i)).not.toBeInTheDocument();
    });

    it("displays caption excerpts for preview items", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      expect(screen.getByText(/caption excerpt for item-1/i)).toBeInTheDocument();
    });
  });

  // Task 6.6: Don't show again checkbox
  describe("Task 6.6: Don't show again checkbox", () => {
    it("renders the 'Don't show again' checkbox", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      expect(
        screen.getByRole("checkbox", { name: /don't show again/i })
      ).toBeInTheDocument();
    });

    it("calls onDontShowAgainChange when checkbox is toggled", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      const checkbox = screen.getByRole("checkbox", { name: /don't show again/i });
      fireEvent.click(checkbox);
      expect(mockOnDontShowAgainChange).toHaveBeenCalledWith(true);
    });

    it("reflects dontShowAgain prop state", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} dontShowAgain={true} />);
      const checkbox = screen.getByRole("checkbox", { name: /don't show again/i });
      expect(checkbox).toBeChecked();
    });
  });

  // Confirm and Cancel actions
  describe("Confirm and Cancel actions", () => {
    it("calls onConfirm when Approve button is clicked", async () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /approve/i }));
      await waitFor(() => {
        expect(mockOnConfirm).toHaveBeenCalledTimes(1);
      });
    });

    it("calls onCancel when Cancel button is clicked", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
      expect(mockOnCancel).toHaveBeenCalledTimes(1);
    });

    it("disables buttons when loading", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} isLoading={true} />);
      expect(screen.getByRole("button", { name: /approving/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
    });

    it("shows loading spinner when loading", () => {
      render(<BatchApproveConfirmDialog {...defaultProps} isLoading={true} />);
      expect(screen.getByText(/approving/i)).toBeInTheDocument();
    });
  });
});
