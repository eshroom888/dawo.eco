/**
 * Tests for ApprovalActions component.
 *
 * Tests button rendering, click handlers, loading states, and keyboard shortcuts.
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApprovalActions } from "../ApprovalActions";

// Mock handlers
const mockOnApprove = jest.fn();
const mockOnReject = jest.fn();
const mockOnEdit = jest.fn();

const defaultProps = {
  onApprove: mockOnApprove,
  onReject: mockOnReject,
  onEdit: mockOnEdit,
  isLoading: false,
  isEditing: false,
};

describe("ApprovalActions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Button Rendering", () => {
    it("renders all three action buttons", () => {
      render(<ApprovalActions {...defaultProps} />);

      expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    });

    it("applies correct styling to Approve button (green)", () => {
      render(<ApprovalActions {...defaultProps} />);

      const approveButton = screen.getByRole("button", { name: /approve/i });
      expect(approveButton).toHaveClass("bg-green-600");
    });

    it("applies correct styling to Reject button (red)", () => {
      render(<ApprovalActions {...defaultProps} />);

      const rejectButton = screen.getByRole("button", { name: /reject/i });
      expect(rejectButton).toHaveClass("bg-red-600");
    });

    it("applies correct styling to Edit button (blue)", () => {
      render(<ApprovalActions {...defaultProps} />);

      const editButton = screen.getByRole("button", { name: /edit/i });
      expect(editButton).toHaveClass("bg-blue-600");
    });

    it("shows keyboard shortcut hints", () => {
      render(<ApprovalActions {...defaultProps} />);

      expect(screen.getByText(/\(a\)/i)).toBeInTheDocument();
      expect(screen.getByText(/\(r\)/i)).toBeInTheDocument();
      expect(screen.getByText(/\(e\)/i)).toBeInTheDocument();
    });
  });

  describe("Click Handlers", () => {
    it("calls onApprove when Approve button is clicked", async () => {
      render(<ApprovalActions {...defaultProps} />);

      const approveButton = screen.getByRole("button", { name: /approve/i });
      await userEvent.click(approveButton);

      expect(mockOnApprove).toHaveBeenCalledTimes(1);
    });

    it("calls onReject when Reject button is clicked", async () => {
      render(<ApprovalActions {...defaultProps} />);

      const rejectButton = screen.getByRole("button", { name: /reject/i });
      await userEvent.click(rejectButton);

      expect(mockOnReject).toHaveBeenCalledTimes(1);
    });

    it("calls onEdit when Edit button is clicked", async () => {
      render(<ApprovalActions {...defaultProps} />);

      const editButton = screen.getByRole("button", { name: /edit/i });
      await userEvent.click(editButton);

      expect(mockOnEdit).toHaveBeenCalledTimes(1);
    });
  });

  describe("Loading States", () => {
    it("disables all buttons when isLoading is true", () => {
      render(<ApprovalActions {...defaultProps} isLoading={true} />);

      expect(screen.getByRole("button", { name: /approve/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /reject/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /edit/i })).toBeDisabled();
    });

    it("shows loading spinner on approve button when loadingAction is approve", () => {
      render(<ApprovalActions {...defaultProps} isLoading={true} loadingAction="approve" />);

      const approveButton = screen.getByRole("button", { name: /approve/i });
      expect(approveButton.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("shows loading spinner on reject button when loadingAction is reject", () => {
      render(<ApprovalActions {...defaultProps} isLoading={true} loadingAction="reject" />);

      const rejectButton = screen.getByRole("button", { name: /reject/i });
      expect(rejectButton.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("shows loading spinner on edit button when loadingAction is edit", () => {
      render(<ApprovalActions {...defaultProps} isLoading={true} loadingAction="edit" />);

      const editButton = screen.getByRole("button", { name: /edit/i });
      expect(editButton.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Edit Mode", () => {
    it("hides action buttons when isEditing is true", () => {
      render(<ApprovalActions {...defaultProps} isEditing={true} />);

      expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
    });
  });

  describe("Keyboard Shortcuts", () => {
    it("triggers onApprove when 'a' key is pressed", () => {
      render(<ApprovalActions {...defaultProps} enableKeyboardShortcuts={true} />);

      fireEvent.keyDown(document, { key: "a" });

      expect(mockOnApprove).toHaveBeenCalledTimes(1);
    });

    it("triggers onReject when 'r' key is pressed", () => {
      render(<ApprovalActions {...defaultProps} enableKeyboardShortcuts={true} />);

      fireEvent.keyDown(document, { key: "r" });

      expect(mockOnReject).toHaveBeenCalledTimes(1);
    });

    it("triggers onEdit when 'e' key is pressed", () => {
      render(<ApprovalActions {...defaultProps} enableKeyboardShortcuts={true} />);

      fireEvent.keyDown(document, { key: "e" });

      expect(mockOnEdit).toHaveBeenCalledTimes(1);
    });

    it("does not trigger shortcuts when modifier keys are pressed", () => {
      render(<ApprovalActions {...defaultProps} enableKeyboardShortcuts={true} />);

      fireEvent.keyDown(document, { key: "a", ctrlKey: true });
      fireEvent.keyDown(document, { key: "a", metaKey: true });

      expect(mockOnApprove).not.toHaveBeenCalled();
    });

    it("does not trigger shortcuts when isEditing is true", () => {
      render(<ApprovalActions {...defaultProps} enableKeyboardShortcuts={true} isEditing={true} />);

      fireEvent.keyDown(document, { key: "a" });
      fireEvent.keyDown(document, { key: "r" });
      fireEvent.keyDown(document, { key: "e" });

      expect(mockOnApprove).not.toHaveBeenCalled();
      expect(mockOnReject).not.toHaveBeenCalled();
      expect(mockOnEdit).not.toHaveBeenCalled();
    });

    it("does not trigger shortcuts when isLoading is true", () => {
      render(<ApprovalActions {...defaultProps} enableKeyboardShortcuts={true} isLoading={true} />);

      fireEvent.keyDown(document, { key: "a" });

      expect(mockOnApprove).not.toHaveBeenCalled();
    });

    it("does not trigger shortcuts when enableKeyboardShortcuts is false", () => {
      render(<ApprovalActions {...defaultProps} enableKeyboardShortcuts={false} />);

      fireEvent.keyDown(document, { key: "a" });

      expect(mockOnApprove).not.toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("has proper aria-labels on all buttons", () => {
      render(<ApprovalActions {...defaultProps} />);

      expect(screen.getByLabelText(/approve content/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/reject content/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/edit content/i)).toBeInTheDocument();
    });

    it("buttons are focusable", () => {
      render(<ApprovalActions {...defaultProps} />);

      const approveButton = screen.getByRole("button", { name: /approve/i });
      approveButton.focus();
      expect(document.activeElement).toBe(approveButton);
    });
  });
});
