/**
 * Tests for ApprovalQueueItem component.
 *
 * Verifies that all required fields from AC #1 are rendered correctly.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ApprovalQueueItem } from "../ApprovalQueueItem";
import { ApprovalQueueItem as ApprovalQueueItemType, ComplianceStatus, SourcePriority } from "@/types/approval";

// Mock item for testing
const mockItem: ApprovalQueueItemType = {
  id: "test-id-123",
  thumbnail_url: "https://example.com/thumb.jpg?w=200&h=200",
  caption_excerpt: "Test caption excerpt for display",
  full_caption: "Full caption with more details and hashtags #DAWO #mushrooms",
  quality_score: 8.5,
  quality_color: "green",
  compliance_status: ComplianceStatus.COMPLIANT,
  would_auto_publish: true,
  suggested_publish_time: "2026-02-10T14:00:00Z",
  source_type: "instagram_post",
  source_priority: SourcePriority.TRENDING,
  hashtags: ["#DAWO", "#mushrooms"],
  created_at: "2026-02-08T10:00:00Z",
};

describe("ApprovalQueueItem", () => {
  const mockOnClick = jest.fn();
  const mockOnSelectionChange = jest.fn();

  beforeEach(() => {
    mockOnClick.mockClear();
    mockOnSelectionChange.mockClear();
  });

  // Story 4-3, Task 1: Selection checkbox tests
  describe("selection checkbox (Story 4-3)", () => {
    it("renders checkbox when selectable is true", () => {
      render(
        <ApprovalQueueItem
          item={mockItem}
          onClick={mockOnClick}
          selectable={true}
          isSelected={false}
          onSelectionChange={mockOnSelectionChange}
        />
      );
      expect(screen.getByRole("checkbox")).toBeInTheDocument();
    });

    it("does not render checkbox when selectable is false", () => {
      render(
        <ApprovalQueueItem
          item={mockItem}
          onClick={mockOnClick}
          selectable={false}
        />
      );
      expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    });

    it("does not render checkbox when selectable is not provided", () => {
      render(
        <ApprovalQueueItem item={mockItem} onClick={mockOnClick} />
      );
      expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    });

    it("checkbox is checked when isSelected is true", () => {
      render(
        <ApprovalQueueItem
          item={mockItem}
          onClick={mockOnClick}
          selectable={true}
          isSelected={true}
          onSelectionChange={mockOnSelectionChange}
        />
      );
      expect(screen.getByRole("checkbox")).toBeChecked();
    });

    it("checkbox is unchecked when isSelected is false", () => {
      render(
        <ApprovalQueueItem
          item={mockItem}
          onClick={mockOnClick}
          selectable={true}
          isSelected={false}
          onSelectionChange={mockOnSelectionChange}
        />
      );
      expect(screen.getByRole("checkbox")).not.toBeChecked();
    });

    it("calls onSelectionChange when checkbox is clicked", () => {
      render(
        <ApprovalQueueItem
          item={mockItem}
          onClick={mockOnClick}
          selectable={true}
          isSelected={false}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const checkbox = screen.getByRole("checkbox");
      fireEvent.click(checkbox);

      expect(mockOnSelectionChange).toHaveBeenCalledWith(mockItem.id);
    });

    it("checkbox click does not trigger card onClick", () => {
      render(
        <ApprovalQueueItem
          item={mockItem}
          onClick={mockOnClick}
          selectable={true}
          isSelected={false}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const checkbox = screen.getByRole("checkbox");
      fireEvent.click(checkbox);

      expect(mockOnSelectionChange).toHaveBeenCalled();
      expect(mockOnClick).not.toHaveBeenCalled();
    });

    it("has visual highlight when selected (Task 1.4)", () => {
      const { container } = render(
        <ApprovalQueueItem
          item={mockItem}
          onClick={mockOnClick}
          selectable={true}
          isSelected={true}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      // Should have a selection indicator (border or background)
      const card = container.querySelector("[data-selected='true']");
      expect(card).toBeInTheDocument();
    });

    it("checkbox has accessible label", () => {
      render(
        <ApprovalQueueItem
          item={mockItem}
          onClick={mockOnClick}
          selectable={true}
          isSelected={false}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toHaveAttribute("aria-label");
    });
  });

  // Task 9.1: Test ApprovalQueueItem renders all required fields
  describe("renders all required fields (AC #1)", () => {
    it("renders thumbnail image", () => {
      render(<ApprovalQueueItem item={mockItem} onClick={mockOnClick} />);
      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("src", mockItem.thumbnail_url);
    });

    it("renders caption excerpt", () => {
      render(<ApprovalQueueItem item={mockItem} onClick={mockOnClick} />);
      expect(screen.getByText(mockItem.caption_excerpt)).toBeInTheDocument();
    });

    it("renders quality score badge", () => {
      render(<ApprovalQueueItem item={mockItem} onClick={mockOnClick} />);
      expect(screen.getByText("8.5")).toBeInTheDocument();
    });

    it("renders compliance status badge", () => {
      render(<ApprovalQueueItem item={mockItem} onClick={mockOnClick} />);
      expect(screen.getByText("COMPLIANT")).toBeInTheDocument();
    });

    it("renders WOULD_AUTO_PUBLISH badge when applicable", () => {
      render(<ApprovalQueueItem item={mockItem} onClick={mockOnClick} />);
      expect(screen.getByText(/auto/i)).toBeInTheDocument();
    });

    it("renders source type badge", () => {
      render(<ApprovalQueueItem item={mockItem} onClick={mockOnClick} />);
      expect(screen.getByText(/instagram/i)).toBeInTheDocument();
    });

    it("renders suggested publish time", () => {
      render(<ApprovalQueueItem item={mockItem} onClick={mockOnClick} />);
      // Should show formatted time
      expect(screen.getByText(/2026|Feb|14:00/i)).toBeInTheDocument();
    });
  });

  describe("click handling", () => {
    it("calls onClick when clicked", () => {
      render(<ApprovalQueueItem item={mockItem} onClick={mockOnClick} />);
      const card = screen.getByRole("article");
      fireEvent.click(card);
      expect(mockOnClick).toHaveBeenCalledWith(mockItem);
    });
  });

  describe("compliance status variations", () => {
    it("renders WARNING status correctly", () => {
      const warningItem = { ...mockItem, compliance_status: ComplianceStatus.WARNING };
      render(<ApprovalQueueItem item={warningItem} onClick={mockOnClick} />);
      expect(screen.getByText("WARNING")).toBeInTheDocument();
    });

    it("renders REJECTED status correctly", () => {
      const rejectedItem = { ...mockItem, compliance_status: ComplianceStatus.REJECTED };
      render(<ApprovalQueueItem item={rejectedItem} onClick={mockOnClick} />);
      expect(screen.getByText("REJECTED")).toBeInTheDocument();
    });
  });

  describe("auto-publish badge visibility", () => {
    it("does not show auto-publish badge when would_auto_publish is false", () => {
      const noAutoItem = { ...mockItem, would_auto_publish: false };
      render(<ApprovalQueueItem item={noAutoItem} onClick={mockOnClick} />);
      expect(screen.queryByText(/auto/i)).not.toBeInTheDocument();
    });
  });
});
