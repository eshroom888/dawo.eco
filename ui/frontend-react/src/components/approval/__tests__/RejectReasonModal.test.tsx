/**
 * Tests for RejectReasonModal component.
 *
 * Tests dropdown selection, validation, and submission.
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RejectReasonModal } from "../RejectReasonModal";
import { RejectReason } from "@/types/approval";

// Mock handlers
const mockOnClose = jest.fn();
const mockOnSubmit = jest.fn();

const defaultProps = {
  isOpen: true,
  onClose: mockOnClose,
  onSubmit: mockOnSubmit,
  isLoading: false,
};

describe("RejectReasonModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockOnSubmit.mockResolvedValue(undefined);
  });

  describe("Rendering", () => {
    it("renders modal when isOpen is true", () => {
      render(<RejectReasonModal {...defaultProps} />);

      expect(screen.getByText("Reject Content")).toBeInTheDocument();
      expect(screen.getByText("Rejection Reason *")).toBeInTheDocument();
      expect(screen.getByText("Additional Details")).toBeInTheDocument();
    });

    it("renders all rejection reasons in dropdown", async () => {
      render(<RejectReasonModal {...defaultProps} />);

      const trigger = screen.getByRole("combobox");
      await userEvent.click(trigger);

      expect(screen.getByText("Contains prohibited claims")).toBeInTheDocument();
      expect(screen.getByText("Doesn't match DAWO tone")).toBeInTheDocument();
      expect(screen.getByText("Quality score too low")).toBeInTheDocument();
      expect(screen.getByText("Topic not suitable")).toBeInTheDocument();
      expect(screen.getByText("Similar post already exists")).toBeInTheDocument();
      expect(screen.getByText("Other reason")).toBeInTheDocument();
    });

    it("shows Cancel and Reject Content buttons", () => {
      render(<RejectReasonModal {...defaultProps} />);

      expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /reject content/i })).toBeInTheDocument();
    });
  });

  describe("Validation", () => {
    it("shows error when submitting without selecting a reason", async () => {
      render(<RejectReasonModal {...defaultProps} />);

      const submitButton = screen.getByRole("button", { name: /reject content/i });
      await userEvent.click(submitButton);

      expect(screen.getByText("Please select a rejection reason")).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it("shows error when OTHER is selected without reason text", async () => {
      render(<RejectReasonModal {...defaultProps} />);

      // Select OTHER reason
      const trigger = screen.getByRole("combobox");
      await userEvent.click(trigger);
      await userEvent.click(screen.getByText("Other reason"));

      // Submit without text
      const submitButton = screen.getByRole("button", { name: /reject content/i });
      await userEvent.click(submitButton);

      expect(screen.getByText("Please provide details when selecting 'Other'")).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it("allows submission without reason text when reason is not OTHER", async () => {
      render(<RejectReasonModal {...defaultProps} />);

      // Select a non-OTHER reason
      const trigger = screen.getByRole("combobox");
      await userEvent.click(trigger);
      await userEvent.click(screen.getByText("Contains prohibited claims"));

      // Submit
      const submitButton = screen.getByRole("button", { name: /reject content/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          reason: RejectReason.COMPLIANCE_ISSUE,
          reason_text: null,
        });
      });
    });
  });

  describe("Submission", () => {
    it("calls onSubmit with selected reason and text", async () => {
      render(<RejectReasonModal {...defaultProps} />);

      // Select reason
      const trigger = screen.getByRole("combobox");
      await userEvent.click(trigger);
      await userEvent.click(screen.getByText("Quality score too low"));

      // Add reason text
      const textarea = screen.getByPlaceholderText(/optional additional details/i);
      await userEvent.type(textarea, "Score is only 3.5");

      // Submit
      const submitButton = screen.getByRole("button", { name: /reject content/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          reason: RejectReason.LOW_QUALITY,
          reason_text: "Score is only 3.5",
        });
      });
    });

    it("calls onClose after successful submission", async () => {
      render(<RejectReasonModal {...defaultProps} />);

      // Select reason
      const trigger = screen.getByRole("combobox");
      await userEvent.click(trigger);
      await userEvent.click(screen.getByText("Contains prohibited claims"));

      // Submit
      const submitButton = screen.getByRole("button", { name: /reject content/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalled();
      });
    });

    it("shows error message when submission fails", async () => {
      mockOnSubmit.mockRejectedValue(new Error("API error"));

      render(<RejectReasonModal {...defaultProps} />);

      // Select reason
      const trigger = screen.getByRole("combobox");
      await userEvent.click(trigger);
      await userEvent.click(screen.getByText("Contains prohibited claims"));

      // Submit
      const submitButton = screen.getByRole("button", { name: /reject content/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText("API error")).toBeInTheDocument();
      });
      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe("Loading State", () => {
    it("disables inputs when isLoading is true", () => {
      render(<RejectReasonModal {...defaultProps} isLoading={true} />);

      expect(screen.getByRole("combobox")).toBeDisabled();
      expect(screen.getByRole("textbox")).toBeDisabled();
      expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
    });

    it("shows loading spinner on submit button when isLoading is true", () => {
      render(<RejectReasonModal {...defaultProps} isLoading={true} />);

      expect(screen.getByText(/rejecting/i)).toBeInTheDocument();
    });
  });

  describe("Character Count", () => {
    it("displays character count for reason text", async () => {
      render(<RejectReasonModal {...defaultProps} />);

      expect(screen.getByText("0/500")).toBeInTheDocument();

      const textarea = screen.getByRole("textbox");
      await userEvent.type(textarea, "Test text");

      expect(screen.getByText("9/500")).toBeInTheDocument();
    });
  });

  describe("Close Behavior", () => {
    it("calls onClose when Cancel button is clicked", async () => {
      render(<RejectReasonModal {...defaultProps} />);

      await userEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("resets form when modal closes and reopens", async () => {
      const { rerender } = render(<RejectReasonModal {...defaultProps} />);

      // Select a reason and enter text
      const trigger = screen.getByRole("combobox");
      await userEvent.click(trigger);
      await userEvent.click(screen.getByText("Contains prohibited claims"));

      const textarea = screen.getByRole("textbox");
      await userEvent.type(textarea, "Some text");

      // Close modal
      await userEvent.click(screen.getByRole("button", { name: /cancel/i }));

      // Reopen modal
      rerender(<RejectReasonModal {...defaultProps} />);

      // Form should be reset
      expect(screen.getByText("0/500")).toBeInTheDocument();
      expect(screen.getByText("Select a reason...")).toBeInTheDocument();
    });
  });
});
