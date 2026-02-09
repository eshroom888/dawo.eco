/**
 * Tests for EditHistoryAccordion component.
 *
 * Tests version display, revert functionality, and empty state.
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EditHistoryAccordion } from "../EditHistoryAccordion";
import { EditHistoryEntry } from "@/types/approval";

// Mock handlers
const mockOnRevert = jest.fn();

const mockHistory: EditHistoryEntry[] = [
  {
    id: "edit-1",
    previous_caption: "Original caption text here",
    new_caption: "Updated caption with changes",
    edited_at: "2026-02-08T10:30:00Z",
    editor: "operator",
  },
  {
    id: "edit-2",
    previous_caption: "Even older caption",
    new_caption: "Original caption text here",
    edited_at: "2026-02-08T09:00:00Z",
    editor: "system",
  },
];

const defaultProps = {
  history: mockHistory,
  onRevert: mockOnRevert,
  isLoading: false,
  currentCaption: "Updated caption with changes",
};

describe("EditHistoryAccordion", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Empty State", () => {
    it("shows empty message when no history", () => {
      render(<EditHistoryAccordion {...defaultProps} history={[]} />);

      expect(screen.getByText(/no edit history available/i)).toBeInTheDocument();
      expect(screen.getByText(/changes will appear here after editing/i)).toBeInTheDocument();
    });
  });

  describe("Version Display", () => {
    it("renders all history entries", () => {
      render(<EditHistoryAccordion {...defaultProps} />);

      expect(screen.getByText("Edit History (2 edits)")).toBeInTheDocument();
      expect(screen.getByText("v2")).toBeInTheDocument();
      expect(screen.getByText("v1")).toBeInTheDocument();
    });

    it("shows editor name for each entry", () => {
      render(<EditHistoryAccordion {...defaultProps} />);

      expect(screen.getByText("operator")).toBeInTheDocument();
      expect(screen.getByText("system")).toBeInTheDocument();
    });

    it("formats timestamps correctly", () => {
      render(<EditHistoryAccordion {...defaultProps} />);

      // Timestamps should be formatted (exact format depends on locale)
      expect(screen.getByText(/feb/i)).toBeInTheDocument();
    });

    it("expands accordion to show diff", async () => {
      render(<EditHistoryAccordion {...defaultProps} />);

      // Click on the first accordion trigger
      const triggers = screen.getAllByRole("button");
      await userEvent.click(triggers[0]);

      // Should show diff content
      await waitFor(() => {
        expect(screen.getByText(/before:/i)).toBeInTheDocument();
        expect(screen.getByText(/after:/i)).toBeInTheDocument();
      });
    });
  });

  describe("Revert Functionality", () => {
    it("shows revert button for non-current versions", async () => {
      render(
        <EditHistoryAccordion
          {...defaultProps}
          currentCaption="Different caption"
        />
      );

      // Expand first accordion
      const triggers = screen.getAllByRole("button");
      await userEvent.click(triggers[0]);

      await waitFor(() => {
        expect(screen.getByText(/revert to this version/i)).toBeInTheDocument();
      });
    });

    it("hides revert button for current version", async () => {
      render(<EditHistoryAccordion {...defaultProps} />);

      // Expand first accordion (which matches currentCaption)
      const triggers = screen.getAllByRole("button");
      await userEvent.click(triggers[0]);

      await waitFor(() => {
        // The first entry's new_caption matches currentCaption, so no revert button
        const revertButtons = screen.queryAllByText(/revert to this version/i);
        expect(revertButtons.length).toBe(0);
      });
    });

    it("calls onRevert when revert button is clicked", async () => {
      render(
        <EditHistoryAccordion
          {...defaultProps}
          currentCaption="Different caption"
        />
      );

      // Expand first accordion
      const triggers = screen.getAllByRole("button");
      await userEvent.click(triggers[0]);

      await waitFor(() => {
        expect(screen.getByText(/revert to this version/i)).toBeInTheDocument();
      });

      const revertButton = screen.getByText(/revert to this version/i);
      await userEvent.click(revertButton);

      expect(mockOnRevert).toHaveBeenCalledWith("edit-1");
    });

    it("shows loading spinner during revert", async () => {
      mockOnRevert.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(
        <EditHistoryAccordion
          {...defaultProps}
          currentCaption="Different caption"
        />
      );

      // Expand first accordion
      const triggers = screen.getAllByRole("button");
      await userEvent.click(triggers[0]);

      await waitFor(() => {
        expect(screen.getByText(/revert to this version/i)).toBeInTheDocument();
      });

      const revertButton = screen.getByText(/revert to this version/i);
      await userEvent.click(revertButton);

      // Should show spinner
      await waitFor(() => {
        expect(revertButton.querySelector(".animate-spin")).toBeInTheDocument();
      });
    });

    it("disables all revert buttons while reverting", async () => {
      mockOnRevert.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(
        <EditHistoryAccordion
          {...defaultProps}
          currentCaption="Different caption"
        />
      );

      // Expand both accordions
      const triggers = screen.getAllByRole("button");
      await userEvent.click(triggers[0]);
      await userEvent.click(triggers[1]);

      await waitFor(() => {
        const revertButtons = screen.getAllByText(/revert to this version/i);
        expect(revertButtons.length).toBeGreaterThan(0);
      });

      // Click first revert button
      const revertButtons = screen.getAllByText(/revert to this version/i);
      await userEvent.click(revertButtons[0]);

      // All revert buttons should be disabled
      await waitFor(() => {
        const buttons = screen.getAllByRole("button", { name: /revert/i });
        buttons.forEach((btn) => {
          expect(btn).toBeDisabled();
        });
      });
    });
  });

  describe("Loading State", () => {
    it("disables revert buttons when isLoading is true", async () => {
      render(
        <EditHistoryAccordion
          {...defaultProps}
          isLoading={true}
          currentCaption="Different caption"
        />
      );

      // Expand first accordion
      const triggers = screen.getAllByRole("button");
      await userEvent.click(triggers[0]);

      await waitFor(() => {
        const revertButton = screen.getByText(/revert to this version/i);
        expect(revertButton).toBeDisabled();
      });
    });
  });

  describe("Diff View", () => {
    it("shows previous caption with strikethrough styling", async () => {
      render(<EditHistoryAccordion {...defaultProps} />);

      // Expand first accordion
      const triggers = screen.getAllByRole("button");
      await userEvent.click(triggers[0]);

      await waitFor(() => {
        const beforeSection = screen.getByText(/before:/i).parentElement;
        expect(beforeSection).toBeInTheDocument();
        expect(beforeSection?.querySelector(".line-through")).toBeInTheDocument();
      });
    });

    it("shows new caption with green styling", async () => {
      render(<EditHistoryAccordion {...defaultProps} />);

      // Expand first accordion
      const triggers = screen.getAllByRole("button");
      await userEvent.click(triggers[0]);

      await waitFor(() => {
        const afterSection = screen.getByText(/after:/i).parentElement;
        expect(afterSection).toBeInTheDocument();
        expect(afterSection?.querySelector(".text-green-600")).toBeInTheDocument();
      });
    });
  });

  describe("Singular/Plural Text", () => {
    it("shows 'edit' for single entry", () => {
      render(
        <EditHistoryAccordion {...defaultProps} history={[mockHistory[0]]} />
      );

      expect(screen.getByText("Edit History (1 edit)")).toBeInTheDocument();
    });

    it("shows 'edits' for multiple entries", () => {
      render(<EditHistoryAccordion {...defaultProps} />);

      expect(screen.getByText("Edit History (2 edits)")).toBeInTheDocument();
    });
  });
});
