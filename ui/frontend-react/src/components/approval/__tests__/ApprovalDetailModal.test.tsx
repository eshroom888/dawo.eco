/**
 * Tests for ApprovalDetailModal component.
 *
 * Task 9.4: Test ApprovalDetailModal opens and displays content
 * Task 9.5: Test FlaggedPhrasesAccordion expands/collapses (via ComplianceDetails)
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ApprovalDetailModal } from "../ApprovalDetailModal";
import { ApprovalQueueItem, ComplianceStatus, SourcePriority } from "@/types/approval";

// Mock item with full details for testing
const mockItem: ApprovalQueueItem = {
  id: "test-id-123",
  thumbnail_url: "https://example.com/thumb.jpg?w=200&h=200",
  caption_excerpt: "Test caption excerpt",
  full_caption: "Full caption with complete details, hashtags, and more content for the detail view.",
  quality_score: 8.5,
  quality_color: "green",
  compliance_status: ComplianceStatus.WARNING,
  would_auto_publish: false,
  suggested_publish_time: "2026-02-10T14:00:00Z",
  source_type: "instagram_post",
  source_priority: SourcePriority.TRENDING,
  hashtags: ["#DAWO", "#mushrooms", "#wellness"],
  compliance_details: [
    {
      phrase: "boosts immunity",
      status: "prohibited",
      explanation: "Health claim not approved under EC 1924/2006",
      regulation_reference: "EC 1924/2006 Art. 10",
    },
    {
      phrase: "natural energy",
      status: "borderline",
      explanation: "Requires clarification or rephrasing",
    },
    {
      phrase: "functional mushrooms",
      status: "permitted",
      explanation: "Descriptive term, no health claim",
    },
  ],
  quality_breakdown: {
    compliance_score: 6.0,
    brand_voice_score: 9.0,
    visual_quality_score: 8.0,
    platform_optimization_score: 8.5,
    engagement_prediction_score: 7.5,
    authenticity_score: 8.0,
  },
  created_at: "2026-02-08T10:00:00Z",
};

describe("ApprovalDetailModal", () => {
  const mockOnClose = jest.fn();
  const mockOnNavigate = jest.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
    mockOnNavigate.mockClear();
  });

  describe("modal display (AC #3)", () => {
    it("renders nothing when item is null", () => {
      const { container } = render(
        <ApprovalDetailModal
          item={null}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      expect(container).toBeEmptyDOMElement();
    });

    it("displays full-size image when open", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      const img = screen.getByAltText("Content preview");
      // Should strip thumbnail size params for full view
      expect(img).toHaveAttribute("src", "https://example.com/thumb.jpg");
    });

    it("displays full caption", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      expect(screen.getByText(mockItem.full_caption)).toBeInTheDocument();
    });

    it("displays all hashtags", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      expect(screen.getByText("#DAWO")).toBeInTheDocument();
      expect(screen.getByText("#mushrooms")).toBeInTheDocument();
      expect(screen.getByText("#wellness")).toBeInTheDocument();
    });

    it("displays compliance details section", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      expect(screen.getByText("Compliance Details")).toBeInTheDocument();
    });

    it("displays quality breakdown section", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      expect(screen.getByText("Quality Breakdown")).toBeInTheDocument();
    });
  });

  describe("keyboard navigation (AC #3)", () => {
    it("closes on Escape key", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      fireEvent.keyDown(document, { key: "Escape" });
      expect(mockOnClose).toHaveBeenCalled();
    });

    it("navigates to previous on ArrowLeft when hasPrev", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
          onNavigate={mockOnNavigate}
          hasPrev={true}
          hasNext={false}
        />
      );
      fireEvent.keyDown(document, { key: "ArrowLeft" });
      expect(mockOnNavigate).toHaveBeenCalledWith("prev");
    });

    it("navigates to next on ArrowRight when hasNext", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
          onNavigate={mockOnNavigate}
          hasPrev={false}
          hasNext={true}
        />
      );
      fireEvent.keyDown(document, { key: "ArrowRight" });
      expect(mockOnNavigate).toHaveBeenCalledWith("next");
    });

    it("does not navigate left when hasPrev is false", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
          onNavigate={mockOnNavigate}
          hasPrev={false}
          hasNext={true}
        />
      );
      fireEvent.keyDown(document, { key: "ArrowLeft" });
      expect(mockOnNavigate).not.toHaveBeenCalled();
    });
  });

  describe("navigation buttons", () => {
    it("disables Previous button when hasPrev is false", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
          onNavigate={mockOnNavigate}
          hasPrev={false}
          hasNext={true}
        />
      );
      const prevButton = screen.getByLabelText("Previous item");
      expect(prevButton).toBeDisabled();
    });

    it("disables Next button when hasNext is false", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
          onNavigate={mockOnNavigate}
          hasPrev={true}
          hasNext={false}
        />
      );
      const nextButton = screen.getByLabelText("Next item");
      expect(nextButton).toBeDisabled();
    });
  });

  describe("flagged phrases accordion (Task 9.5)", () => {
    it("displays prohibited phrases section", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      expect(screen.getByText(/Prohibited Phrases/)).toBeInTheDocument();
    });

    it("displays borderline phrases section", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      expect(screen.getByText(/Borderline Phrases/)).toBeInTheDocument();
    });

    it("shows flagged phrase with explanation", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      // Prohibited section should be expanded by default
      expect(screen.getByText(/"boosts immunity"/)).toBeInTheDocument();
      expect(screen.getByText(/Health claim not approved/)).toBeInTheDocument();
    });

    it("shows EU regulation reference for violations", () => {
      render(
        <ApprovalDetailModal
          item={mockItem}
          isOpen={true}
          onClose={mockOnClose}
        />
      );
      expect(screen.getByText(/EC 1924\/2006 Art. 10/)).toBeInTheDocument();
    });
  });
});
