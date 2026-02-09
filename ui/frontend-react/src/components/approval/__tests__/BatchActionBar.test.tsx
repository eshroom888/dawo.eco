/**
 * Tests for BatchActionBar component.
 *
 * Story 4-3: Batch Approval Capability
 * Task 2: Create batch action bar component
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BatchActionBar } from "../BatchActionBar";

describe("BatchActionBar", () => {
  const mockOnApproveAll = jest.fn();
  const mockOnRejectAll = jest.fn();
  const mockOnClearSelection = jest.fn();

  beforeEach(() => {
    mockOnApproveAll.mockClear();
    mockOnRejectAll.mockClear();
    mockOnClearSelection.mockClear();
  });

  // Task 2.1: Component renders when items selected
  describe("visibility", () => {
    it("renders when selectedCount > 0", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      expect(screen.getByText(/3 items? selected/i)).toBeInTheDocument();
    });

    it("does not render when selectedCount is 0", () => {
      const { container } = render(
        <BatchActionBar
          selectedCount={0}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  // Task 2.3: Display selected count
  describe("selected count display", () => {
    it("shows singular 'item' for count of 1", () => {
      render(
        <BatchActionBar
          selectedCount={1}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      expect(screen.getByText("1 item selected")).toBeInTheDocument();
    });

    it("shows plural 'items' for count > 1", () => {
      render(
        <BatchActionBar
          selectedCount={5}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      expect(screen.getByText("5 items selected")).toBeInTheDocument();
    });
  });

  // Task 2.4: Approve All button
  describe("Approve All button", () => {
    it("renders Approve All button", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      expect(screen.getByRole("button", { name: /approve all/i })).toBeInTheDocument();
    });

    it("calls onApproveAll when clicked", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /approve all/i }));
      expect(mockOnApproveAll).toHaveBeenCalledTimes(1);
    });

    it("is disabled when isLoading is true", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={true}
        />
      );

      expect(screen.getByRole("button", { name: /processing/i })).toBeDisabled();
    });
  });

  // Task 2.5: Reject All button
  describe("Reject All button", () => {
    it("renders Reject All button", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      expect(screen.getByRole("button", { name: /reject all/i })).toBeInTheDocument();
    });

    it("calls onRejectAll when clicked", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /reject all/i }));
      expect(mockOnRejectAll).toHaveBeenCalledTimes(1);
    });

    it("is disabled when isLoading is true", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={true}
        />
      );

      const rejectButton = screen.getByRole("button", { name: /reject all/i });
      expect(rejectButton).toBeDisabled();
    });
  });

  // Task 2.6: Clear Selection button
  describe("Clear Selection button", () => {
    it("renders Clear button", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      expect(screen.getByRole("button", { name: /clear/i })).toBeInTheDocument();
    });

    it("calls onClearSelection when clicked", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /clear/i }));
      expect(mockOnClearSelection).toHaveBeenCalledTimes(1);
    });
  });

  // Task 2.2: Sticky positioning (visual test - check className)
  describe("styling", () => {
    it("has fixed positioning at bottom", () => {
      const { container } = render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      const bar = container.firstChild as HTMLElement;
      expect(bar).toHaveClass("fixed");
      expect(bar).toHaveClass("bottom-0");
    });

    it("has high z-index for overlay", () => {
      const { container } = render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      const bar = container.firstChild as HTMLElement;
      expect(bar).toHaveClass("z-50");
    });
  });

  // Task 2.7: Animation (presence of animation class)
  describe("animation", () => {
    it("has animation class for appearance", () => {
      const { container } = render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      const bar = container.firstChild as HTMLElement;
      expect(bar.className).toMatch(/animate|slide|transition/i);
    });
  });

  // Task 2.8: Keyboard shortcuts
  describe("keyboard shortcuts", () => {
    it("triggers approve on Shift+A when bar is visible", async () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      // Simulate Shift+A keypress
      fireEvent.keyDown(document, { key: "a", shiftKey: true });

      expect(mockOnApproveAll).toHaveBeenCalledTimes(1);
    });

    it("triggers reject on Shift+R when bar is visible", async () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      // Simulate Shift+R keypress
      fireEvent.keyDown(document, { key: "r", shiftKey: true });

      expect(mockOnRejectAll).toHaveBeenCalledTimes(1);
    });

    it("does not trigger shortcuts without Shift key", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      fireEvent.keyDown(document, { key: "a", shiftKey: false });
      fireEvent.keyDown(document, { key: "r", shiftKey: false });

      expect(mockOnApproveAll).not.toHaveBeenCalled();
      expect(mockOnRejectAll).not.toHaveBeenCalled();
    });

    it("does not trigger shortcuts when isLoading is true", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={true}
        />
      );

      fireEvent.keyDown(document, { key: "a", shiftKey: true });
      fireEvent.keyDown(document, { key: "r", shiftKey: true });

      expect(mockOnApproveAll).not.toHaveBeenCalled();
      expect(mockOnRejectAll).not.toHaveBeenCalled();
    });
  });

  // Loading state shows processing text
  describe("loading state", () => {
    it("shows 'Processing...' text when loading", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={true}
        />
      );

      expect(screen.getByText(/processing/i)).toBeInTheDocument();
    });
  });

  // Accessibility
  describe("accessibility", () => {
    it("has proper ARIA attributes", () => {
      render(
        <BatchActionBar
          selectedCount={3}
          onApproveAll={mockOnApproveAll}
          onRejectAll={mockOnRejectAll}
          onClearSelection={mockOnClearSelection}
          isLoading={false}
        />
      );

      const bar = screen.getByRole("toolbar");
      expect(bar).toHaveAttribute("aria-label", "Batch actions");
    });
  });
});
