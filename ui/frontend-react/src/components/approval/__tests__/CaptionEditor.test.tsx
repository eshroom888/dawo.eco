/**
 * Tests for CaptionEditor component.
 *
 * Tests inline editing, validation, and save/cancel actions.
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CaptionEditor } from "../CaptionEditor";

// Mock handlers
const mockOnSave = jest.fn();
const mockOnCancel = jest.fn();
const mockOnRevert = jest.fn();

const defaultProps = {
  caption: "Test caption text for DAWO mushrooms wellness content.",
  hashtags: ["DAWO", "mushrooms", "wellness"],
  onSave: mockOnSave,
  onCancel: mockOnCancel,
  isLoading: false,
};

describe("CaptionEditor", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockOnSave.mockResolvedValue(undefined);
    mockOnRevert.mockResolvedValue(undefined);
  });

  describe("Rendering", () => {
    it("renders caption textarea with current content", () => {
      render(<CaptionEditor {...defaultProps} />);

      const textarea = screen.getByLabelText(/caption/i);
      expect(textarea).toHaveValue(defaultProps.caption);
    });

    it("renders hashtag textarea with formatted hashtags", () => {
      render(<CaptionEditor {...defaultProps} />);

      const hashtagTextarea = screen.getByLabelText(/hashtags/i);
      expect(hashtagTextarea).toHaveValue("DAWO #mushrooms #wellness");
    });

    it("displays character count", () => {
      render(<CaptionEditor {...defaultProps} />);

      expect(screen.getByText(`${defaultProps.caption.length}/2200`)).toBeInTheDocument();
    });

    it("displays word count", () => {
      render(<CaptionEditor {...defaultProps} />);

      // "Test caption text for DAWO mushrooms wellness content." = 8 words
      expect(screen.getByText(/8 words/i)).toBeInTheDocument();
    });

    it("shows Save and Cancel buttons", () => {
      render(<CaptionEditor {...defaultProps} />);

      expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    });
  });

  describe("Validation", () => {
    it("disables save when no changes made", () => {
      render(<CaptionEditor {...defaultProps} />);

      expect(screen.getByRole("button", { name: /save/i })).toBeDisabled();
    });

    it("enables save when caption is modified", async () => {
      render(<CaptionEditor {...defaultProps} />);

      const textarea = screen.getByLabelText(/caption/i);
      await userEvent.type(textarea, " additional text");

      expect(screen.getByRole("button", { name: /save/i })).not.toBeDisabled();
    });

    it("shows warning when word count is below target", async () => {
      render(<CaptionEditor {...defaultProps} caption="Short caption" hashtags={[]} />);

      expect(screen.getByText(/2 words/i)).toBeInTheDocument();
      expect(screen.getByText(/target: 180-220/i)).toBeInTheDocument();
    });

    it("shows error when caption exceeds max characters", async () => {
      const longCaption = "x".repeat(2201);
      render(<CaptionEditor {...defaultProps} caption={longCaption} hashtags={[]} />);

      expect(screen.getByText(/exceeds maximum character limit/i)).toBeInTheDocument();
    });

    it("disables save when caption is empty", async () => {
      render(<CaptionEditor {...defaultProps} />);

      const textarea = screen.getByLabelText(/caption/i);
      await userEvent.clear(textarea);

      expect(screen.getByRole("button", { name: /save/i })).toBeDisabled();
    });
  });

  describe("Save Action", () => {
    it("calls onSave with edited content", async () => {
      render(<CaptionEditor {...defaultProps} />);

      const textarea = screen.getByLabelText(/caption/i);
      await userEvent.clear(textarea);
      await userEvent.type(textarea, "New caption content");

      await userEvent.click(screen.getByRole("button", { name: /save/i }));

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          "New caption content",
          expect.arrayContaining(["DAWO", "mushrooms", "wellness"])
        );
      });
    });

    it("shows loading state during save", async () => {
      mockOnSave.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<CaptionEditor {...defaultProps} />);

      const textarea = screen.getByLabelText(/caption/i);
      await userEvent.type(textarea, " more");

      await userEvent.click(screen.getByRole("button", { name: /save/i }));

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /save/i })).toBeDisabled();
      });
    });

    it("shows error when save fails", async () => {
      mockOnSave.mockRejectedValue(new Error("Network error"));

      render(<CaptionEditor {...defaultProps} />);

      const textarea = screen.getByLabelText(/caption/i);
      await userEvent.type(textarea, " more");

      await userEvent.click(screen.getByRole("button", { name: /save/i }));

      await waitFor(() => {
        expect(screen.getByText("Network error")).toBeInTheDocument();
      });
    });
  });

  describe("Cancel Action", () => {
    it("calls onCancel when Cancel button is clicked", async () => {
      render(<CaptionEditor {...defaultProps} />);

      await userEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(mockOnCancel).toHaveBeenCalled();
    });

    it("calls onCancel on Escape key", async () => {
      render(<CaptionEditor {...defaultProps} />);

      const textarea = screen.getByLabelText(/caption/i);
      await userEvent.type(textarea, "{Escape}");

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  describe("Revert Action", () => {
    it("shows Revert button when original caption exists and is different", () => {
      render(
        <CaptionEditor
          {...defaultProps}
          originalCaption="Original caption text"
          onRevert={mockOnRevert}
        />
      );

      expect(screen.getByRole("button", { name: /revert to original/i })).toBeInTheDocument();
    });

    it("hides Revert button when caption matches original", () => {
      render(
        <CaptionEditor
          {...defaultProps}
          originalCaption={defaultProps.caption}
          onRevert={mockOnRevert}
        />
      );

      expect(screen.queryByRole("button", { name: /revert to original/i })).not.toBeInTheDocument();
    });

    it("calls onRevert when Revert button is clicked", async () => {
      render(
        <CaptionEditor
          {...defaultProps}
          originalCaption="Original caption text"
          onRevert={mockOnRevert}
        />
      );

      await userEvent.click(screen.getByRole("button", { name: /revert to original/i }));

      await waitFor(() => {
        expect(mockOnRevert).toHaveBeenCalled();
      });
    });
  });

  describe("Loading State", () => {
    it("disables all inputs when isLoading is true", () => {
      render(<CaptionEditor {...defaultProps} isLoading={true} />);

      expect(screen.getByLabelText(/caption/i)).toBeDisabled();
      expect(screen.getByLabelText(/hashtags/i)).toBeDisabled();
      expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
    });
  });

  describe("Keyboard Shortcuts", () => {
    it("saves on Ctrl+Enter", async () => {
      render(<CaptionEditor {...defaultProps} />);

      const textarea = screen.getByLabelText(/caption/i);
      await userEvent.type(textarea, " extra text");
      await userEvent.type(textarea, "{Control>}{Enter}{/Control}");

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalled();
      });
    });
  });

  describe("Hashtag Preview", () => {
    it("displays hashtag preview badges", () => {
      render(<CaptionEditor {...defaultProps} />);

      expect(screen.getByText("#DAWO")).toBeInTheDocument();
      expect(screen.getByText("#mushrooms")).toBeInTheDocument();
      expect(screen.getByText("#wellness")).toBeInTheDocument();
    });

    it("shows count for hashtags beyond 10", async () => {
      const manyHashtags = Array.from({ length: 15 }, (_, i) => `tag${i}`);
      render(<CaptionEditor {...defaultProps} hashtags={manyHashtags} />);

      expect(screen.getByText("+5 more")).toBeInTheDocument();
    });
  });
});
