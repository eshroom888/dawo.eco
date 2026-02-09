/**
 * QuickFilters component tests.
 *
 * Story 4-3: Batch Approval Capability
 * Task 5: WOULD_AUTO_PUBLISH quick filter
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QuickFilters, QuickFiltersProps } from "../QuickFilters";
import { ApprovalQueueItem, SourcePriority, ComplianceStatus } from "@/types/approval";

// Mock queue items for testing
const createMockItem = (
  id: string,
  wouldAutoPublish: boolean,
  qualityScore: number = 8.5
): ApprovalQueueItem => ({
  id,
  thumbnail_url: "https://example.com/img.jpg",
  caption_excerpt: "Test caption",
  full_caption: "Full test caption",
  quality_score: qualityScore,
  quality_color: qualityScore >= 8 ? "green" : qualityScore >= 5 ? "yellow" : "red",
  compliance_status: ComplianceStatus.COMPLIANT,
  would_auto_publish: wouldAutoPublish,
  suggested_publish_time: "2026-02-15T10:00:00Z",
  source_type: "instagram_post",
  source_priority: SourcePriority.TRENDING,
  hashtags: ["test"],
  created_at: "2026-02-08T12:00:00Z",
});

const mockItems: ApprovalQueueItem[] = [
  createMockItem("item-1", true, 9.0), // would auto-publish
  createMockItem("item-2", false, 6.0), // would NOT auto-publish
  createMockItem("item-3", true, 8.5), // would auto-publish
  createMockItem("item-4", false, 4.0), // would NOT auto-publish
  createMockItem("item-5", true, 9.5), // would auto-publish
];

describe("QuickFilters", () => {
  let defaultProps: QuickFiltersProps;
  let mockOnSelectWouldAutoPublish: ReturnType<typeof vi.fn>;
  let mockOnApproveAllHighQuality: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnSelectWouldAutoPublish = vi.fn();
    mockOnApproveAllHighQuality = vi.fn();

    defaultProps = {
      items: mockItems,
      onSelectWouldAutoPublish: mockOnSelectWouldAutoPublish,
      onApproveAllHighQuality: mockOnApproveAllHighQuality,
      selectedCount: 0,
      isLoading: false,
    };
  });

  // Task 5.1: QuickFilters component renders above queue list
  describe("Task 5.1: Component renders", () => {
    it("renders the quick filters section", () => {
      render(<QuickFilters {...defaultProps} />);
      expect(screen.getByRole("toolbar", { name: /quick filters/i })).toBeInTheDocument();
    });

    it("displays the correct count of would-auto-publish items", () => {
      render(<QuickFilters {...defaultProps} />);
      // 3 items have would_auto_publish=true
      expect(screen.getByText(/3 high-quality/i)).toBeInTheDocument();
    });

    it("updates count when items change", () => {
      const { rerender } = render(<QuickFilters {...defaultProps} />);
      expect(screen.getByText(/3 high-quality/i)).toBeInTheDocument();

      // Remove one auto-publish item
      rerender(<QuickFilters {...defaultProps} items={mockItems.slice(1)} />);
      expect(screen.getByText(/2 high-quality/i)).toBeInTheDocument();
    });
  });

  // Task 5.2: "Select All WOULD_AUTO_PUBLISH" button
  describe("Task 5.2: Select All button", () => {
    it("renders 'Select All High-Quality' button", () => {
      render(<QuickFilters {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /select all high-quality/i })
      ).toBeInTheDocument();
    });

    it("button shows count of items to select", () => {
      render(<QuickFilters {...defaultProps} />);
      const button = screen.getByRole("button", { name: /select all high-quality/i });
      expect(button).toHaveTextContent("3");
    });

    it("disables button when no high-quality items exist", () => {
      const noHighQuality = mockItems.filter((i) => !i.would_auto_publish);
      render(<QuickFilters {...defaultProps} items={noHighQuality} />);
      expect(
        screen.getByRole("button", { name: /select all high-quality/i })
      ).toBeDisabled();
    });
  });

  // Task 5.3: Filter selects only would_auto_publish=true items
  describe("Task 5.3: Filter selects correct items", () => {
    it("calls onSelectWouldAutoPublish when button clicked", () => {
      render(<QuickFilters {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /select all high-quality/i }));
      expect(mockOnSelectWouldAutoPublish).toHaveBeenCalledTimes(1);
    });

    it("does not call handler when loading", () => {
      render(<QuickFilters {...defaultProps} isLoading={true} />);
      const button = screen.getByRole("button", { name: /select all high-quality/i });
      fireEvent.click(button);
      expect(mockOnSelectWouldAutoPublish).not.toHaveBeenCalled();
    });
  });

  // Task 5.4: Selected count display when filter applied
  describe("Task 5.4: Selected count display", () => {
    it("shows selected count when items are selected", () => {
      render(<QuickFilters {...defaultProps} selectedCount={3} />);
      expect(screen.getByText(/3 selected/i)).toBeInTheDocument();
    });

    it("does not show selected count when none selected", () => {
      render(<QuickFilters {...defaultProps} selectedCount={0} />);
      expect(screen.queryByText(/selected/i)).not.toBeInTheDocument();
    });
  });

  // Task 5.5: "Approve All High-Quality" one-click action
  describe("Task 5.5: Approve All High-Quality action", () => {
    it("renders 'Approve All High-Quality' button", () => {
      render(<QuickFilters {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /approve all high-quality/i })
      ).toBeInTheDocument();
    });

    it("calls onApproveAllHighQuality when clicked", () => {
      render(<QuickFilters {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /approve all high-quality/i }));
      expect(mockOnApproveAllHighQuality).toHaveBeenCalledTimes(1);
    });

    it("disables button when loading", () => {
      render(<QuickFilters {...defaultProps} isLoading={true} />);
      expect(
        screen.getByRole("button", { name: /approve all high-quality/i })
      ).toBeDisabled();
    });

    it("disables button when no high-quality items exist", () => {
      const noHighQuality = mockItems.filter((i) => !i.would_auto_publish);
      render(<QuickFilters {...defaultProps} items={noHighQuality} />);
      expect(
        screen.getByRole("button", { name: /approve all high-quality/i })
      ).toBeDisabled();
    });

    it("shows loading state on button when isLoading", () => {
      render(<QuickFilters {...defaultProps} isLoading={true} />);
      expect(screen.getByText(/processing/i)).toBeInTheDocument();
    });
  });

  // Task 5.6: Tracking (covered by handler invocation)
  describe("Task 5.6: Usage tracking", () => {
    it("approve all button passes through for tracking", () => {
      render(<QuickFilters {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /approve all high-quality/i }));
      // Tracking is handled in parent component via the callback
      expect(mockOnApproveAllHighQuality).toHaveBeenCalledWith();
    });
  });

  // Edge cases
  describe("Edge cases", () => {
    it("handles empty items array", () => {
      render(<QuickFilters {...defaultProps} items={[]} />);
      expect(screen.getByText(/0 high-quality/i)).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /select all high-quality/i })
      ).toBeDisabled();
    });

    it("renders with correct accessibility attributes", () => {
      render(<QuickFilters {...defaultProps} />);
      const toolbar = screen.getByRole("toolbar", { name: /quick filters/i });
      expect(toolbar).toBeInTheDocument();
    });
  });
});
