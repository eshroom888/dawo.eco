/**
 * BatchRejectConfirmDialog component tests.
 *
 * Story 4-3: Batch Approval Capability
 * Task 6: Batch confirmation dialogs
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  BatchRejectConfirmDialog,
  BatchRejectConfirmDialogProps,
} from "../BatchRejectConfirmDialog";
import {
  ApprovalQueueItem,
  SourcePriority,
  ComplianceStatus,
  RejectReason,
} from "@/types/approval";

// Mock queue items for testing
const createMockItem = (id: string): ApprovalQueueItem => ({
  id,
  thumbnail_url: `https://example.com/${id}.jpg`,
  caption_excerpt: `Caption excerpt for ${id}`,
  full_caption: `Full caption for ${id}`,
  quality_score: 6.0,
  quality_color: "yellow",
  compliance_status: ComplianceStatus.WARNING,
  would_auto_publish: false,
  suggested_publish_time: "2026-02-10T10:00:00Z",
  source_type: "instagram_post",
  source_priority: SourcePriority.SCHEDULED,
  hashtags: ["test"],
  created_at: "2026-02-08T12:00:00Z",
});

const mockItems: ApprovalQueueItem[] = [
  createMockItem("item-1"),
  createMockItem("item-2"),
  createMockItem("item-3"),
];

describe("BatchRejectConfirmDialog", () => {
  let defaultProps: BatchRejectConfirmDialogProps;
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

  // Task 6.4: BatchRejectConfirmDialog creation
  describe("Task 6.4: Dialog renders", () => {
    it("renders the dialog when isOpen is true", () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("does not render when isOpen is false", () => {
      render(<BatchRejectConfirmDialog {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("displays dialog title", () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);
      expect(
        screen.getByRole("heading", { name: /confirm batch rejection/i })
      ).toBeInTheDocument();
    });

    it("displays the count of items to be rejected", () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);
      expect(screen.getByText(/3 items/i)).toBeInTheDocument();
    });
  });

  // Task 6.5: Use RejectReason enum from Story 4-2
  describe("Task 6.5: Reject reason selection", () => {
    it("renders rejection reason dropdown", () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("requires reason selection before confirmation", () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);
      const confirmButton = screen.getByRole("button", { name: /reject/i });
      // Should be disabled without reason selected
      expect(confirmButton).toBeDisabled();
    });

    it("enables confirm button after reason is selected", async () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);

      // Click the dropdown to open
      fireEvent.click(screen.getByRole("combobox"));

      // Select a reason
      await waitFor(() => {
        const option = screen.getByText(/contains prohibited claims/i);
        fireEvent.click(option);
      });

      // Button should be enabled
      const confirmButton = screen.getByRole("button", { name: /reject/i });
      expect(confirmButton).not.toBeDisabled();
    });

    it("shows reason text field when OTHER is selected", async () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);

      fireEvent.click(screen.getByRole("combobox"));

      await waitFor(() => {
        const option = screen.getByText(/other reason/i);
        fireEvent.click(option);
      });

      expect(screen.getByPlaceholderText(/describe the reason/i)).toBeInTheDocument();
    });

    it("passes reason to onConfirm", async () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);

      fireEvent.click(screen.getByRole("combobox"));

      await waitFor(() => {
        const option = screen.getByText(/contains prohibited claims/i);
        fireEvent.click(option);
      });

      fireEvent.click(screen.getByRole("button", { name: /reject/i }));

      await waitFor(() => {
        expect(mockOnConfirm).toHaveBeenCalledWith({
          reason: RejectReason.COMPLIANCE_ISSUE,
          reason_text: null,
        });
      });
    });
  });

  // Task 6.6: Don't show again checkbox
  describe("Task 6.6: Don't show again checkbox", () => {
    it("renders the 'Don't show again' checkbox", () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);
      expect(
        screen.getByRole("checkbox", { name: /don't show again/i })
      ).toBeInTheDocument();
    });

    it("calls onDontShowAgainChange when checkbox is toggled", () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);
      const checkbox = screen.getByRole("checkbox", { name: /don't show again/i });
      fireEvent.click(checkbox);
      expect(mockOnDontShowAgainChange).toHaveBeenCalledWith(true);
    });
  });

  // Cancel action
  describe("Cancel action", () => {
    it("calls onCancel when Cancel button is clicked", () => {
      render(<BatchRejectConfirmDialog {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
      expect(mockOnCancel).toHaveBeenCalledTimes(1);
    });
  });

  // Loading state
  describe("Loading state", () => {
    it("disables buttons when loading", async () => {
      render(<BatchRejectConfirmDialog {...defaultProps} isLoading={true} />);
      expect(screen.getByRole("button", { name: /rejecting/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
    });
  });
});
