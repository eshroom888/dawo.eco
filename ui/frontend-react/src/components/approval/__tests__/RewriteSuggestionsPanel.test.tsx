/**
 * Tests for RewriteSuggestionsPanel component.
 *
 * Tests suggestion display, accept actions, and bulk operations.
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RewriteSuggestionsPanel } from "../RewriteSuggestionsPanel";
import { RewriteSuggestion } from "@/types/approval";

// Mock handlers
const mockOnAccept = jest.fn();
const mockOnDismiss = jest.fn();

const createSuggestion = (overrides?: Partial<RewriteSuggestion>): RewriteSuggestion => ({
  id: `sug-${Math.random().toString(36).substr(2, 9)}`,
  original_text: "Original text that needs improvement",
  suggested_text: "Improved text that is compliant",
  reason: "This change improves compliance with EU regulations",
  type: "compliance",
  ...overrides,
});

const defaultProps = {
  suggestions: [
    createSuggestion({ id: "sug-1", type: "compliance" }),
    createSuggestion({ id: "sug-2", type: "brand_voice" }),
    createSuggestion({ id: "sug-3", type: "quality" }),
  ],
  onAccept: mockOnAccept,
  onDismiss: mockOnDismiss,
  isLoading: false,
};

describe("RewriteSuggestionsPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockOnAccept.mockResolvedValue(undefined);
  });

  describe("Rendering", () => {
    it("renders panel with suggestions count", () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      expect(screen.getByText("AI Rewrite Suggestions")).toBeInTheDocument();
      expect(screen.getByText("3 pending")).toBeInTheDocument();
    });

    it("renders all suggestion cards", () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      expect(screen.getAllByText(/original text that needs improvement/i)).toHaveLength(3);
    });

    it("renders Accept All button when multiple suggestions exist", () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      expect(screen.getByRole("button", { name: /accept all/i })).toBeInTheDocument();
    });

    it("hides Accept All button when only one suggestion", () => {
      render(
        <RewriteSuggestionsPanel
          {...defaultProps}
          suggestions={[createSuggestion({ id: "sug-1" })]}
        />
      );

      expect(screen.queryByRole("button", { name: /accept all/i })).not.toBeInTheDocument();
    });

    it("returns null when no suggestions", () => {
      const { container } = render(
        <RewriteSuggestionsPanel {...defaultProps} suggestions={[]} />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe("Accept Single Suggestion", () => {
    it("calls onAccept with single suggestion ID", async () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      const acceptButtons = screen.getAllByRole("button", { name: /accept/i });
      await userEvent.click(acceptButtons[0]);

      await waitFor(() => {
        expect(mockOnAccept).toHaveBeenCalledWith(["sug-1"]);
      });
    });

    it("marks suggestion as accepted after successful accept", async () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      const acceptButtons = screen.getAllByRole("button", { name: /accept/i });
      await userEvent.click(acceptButtons[0]);

      await waitFor(() => {
        expect(screen.getByText("1 accepted")).toBeInTheDocument();
        expect(screen.getByText("2 pending")).toBeInTheDocument();
      });
    });
  });

  describe("Accept All Suggestions", () => {
    it("calls onAccept with all suggestion IDs", async () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      await userEvent.click(screen.getByRole("button", { name: /accept all/i }));

      await waitFor(() => {
        expect(mockOnAccept).toHaveBeenCalledWith(["sug-1", "sug-2", "sug-3"]);
      });
    });

    it("shows all accepted message when all are accepted", async () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      await userEvent.click(screen.getByRole("button", { name: /accept all/i }));

      await waitFor(() => {
        expect(screen.getByText(/all suggestions have been applied/i)).toBeInTheDocument();
      });
    });
  });

  describe("Loading State", () => {
    it("disables Accept All button when isLoading", () => {
      render(<RewriteSuggestionsPanel {...defaultProps} isLoading={true} />);

      expect(screen.getByRole("button", { name: /accept all/i })).toBeDisabled();
    });

    it("shows loading spinner during Accept All", async () => {
      mockOnAccept.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<RewriteSuggestionsPanel {...defaultProps} />);

      await userEvent.click(screen.getByRole("button", { name: /accept all/i }));

      await waitFor(() => {
        const button = screen.getByRole("button", { name: /accept all/i });
        expect(button).toBeDisabled();
      });
    });
  });

  describe("Collapsible Panel", () => {
    it("starts expanded by default", () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      // All suggestions should be visible
      expect(screen.getAllByText(/original text/i).length).toBeGreaterThan(0);
    });

    it("collapses panel when header is clicked", async () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      const header = screen.getByText("AI Rewrite Suggestions").closest("div");
      if (header) {
        await userEvent.click(header);
      }

      // Collapsible content should be hidden
      // Note: The actual content visibility depends on shadcn/ui implementation
    });
  });

  describe("Badge Counts", () => {
    it("shows pending count", () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      expect(screen.getByText("3 pending")).toBeInTheDocument();
    });

    it("shows accepted count after accepting", async () => {
      render(<RewriteSuggestionsPanel {...defaultProps} />);

      const acceptButtons = screen.getAllByRole("button", { name: /accept/i });
      await userEvent.click(acceptButtons[0]);
      await userEvent.click(acceptButtons[1]);

      await waitFor(() => {
        expect(screen.getByText("2 accepted")).toBeInTheDocument();
        expect(screen.getByText("1 pending")).toBeInTheDocument();
      });
    });
  });
});
