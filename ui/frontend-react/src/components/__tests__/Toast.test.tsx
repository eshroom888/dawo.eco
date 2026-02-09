/**
 * Toast component tests.
 *
 * Story 4-3: Batch Approval Capability
 * Task 10: Frontend component tests
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Toast, ToastContainer, ToastProps } from "../Toast";
import { Toast as ToastType } from "@/hooks/useToast";

describe("Toast", () => {
  let defaultProps: ToastProps;
  let mockOnDismiss: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnDismiss = vi.fn();
    defaultProps = {
      id: "toast-1",
      type: "success",
      title: "Success Title",
      message: "Success message",
      onDismiss: mockOnDismiss,
    };
  });

  describe("rendering", () => {
    it("renders success toast with correct styling", () => {
      render(<Toast {...defaultProps} />);
      expect(screen.getByText("Success Title")).toBeInTheDocument();
      expect(screen.getByText("Success message")).toBeInTheDocument();
    });

    it("renders error toast", () => {
      render(<Toast {...defaultProps} type="error" title="Error Title" />);
      expect(screen.getByText("Error Title")).toBeInTheDocument();
    });

    it("renders warning toast", () => {
      render(<Toast {...defaultProps} type="warning" title="Warning Title" />);
      expect(screen.getByText("Warning Title")).toBeInTheDocument();
    });

    it("renders info toast", () => {
      render(<Toast {...defaultProps} type="info" title="Info Title" />);
      expect(screen.getByText("Info Title")).toBeInTheDocument();
    });

    it("renders without message", () => {
      render(<Toast {...defaultProps} message={undefined} />);
      expect(screen.getByText("Success Title")).toBeInTheDocument();
      expect(screen.queryByText("Success message")).not.toBeInTheDocument();
    });
  });

  describe("dismiss button", () => {
    it("calls onDismiss when dismiss button clicked", () => {
      render(<Toast {...defaultProps} />);
      fireEvent.click(screen.getByLabelText("Dismiss"));
      expect(mockOnDismiss).toHaveBeenCalledWith("toast-1");
    });
  });

  describe("action button", () => {
    it("renders action button when provided", () => {
      const mockAction = vi.fn();
      render(
        <Toast
          {...defaultProps}
          action={{ label: "Retry", onClick: mockAction }}
        />
      );
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });

    it("calls action onClick and dismisses when action button clicked", () => {
      const mockAction = vi.fn();
      render(
        <Toast
          {...defaultProps}
          action={{ label: "Retry", onClick: mockAction }}
        />
      );
      fireEvent.click(screen.getByText("Retry"));
      expect(mockAction).toHaveBeenCalled();
      expect(mockOnDismiss).toHaveBeenCalledWith("toast-1");
    });
  });

  describe("accessibility", () => {
    it("has alert role", () => {
      render(<Toast {...defaultProps} />);
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("has polite aria-live", () => {
      render(<Toast {...defaultProps} />);
      expect(screen.getByRole("alert")).toHaveAttribute("aria-live", "polite");
    });
  });
});

describe("ToastContainer", () => {
  let mockOnDismiss: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnDismiss = vi.fn();
  });

  it("returns null when no toasts", () => {
    const { container } = render(
      <ToastContainer toasts={[]} onDismiss={mockOnDismiss} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders multiple toasts", () => {
    const toasts: ToastType[] = [
      { id: "1", type: "success", title: "Toast 1" },
      { id: "2", type: "error", title: "Toast 2" },
      { id: "3", type: "info", title: "Toast 3" },
    ];

    render(<ToastContainer toasts={toasts} onDismiss={mockOnDismiss} />);

    expect(screen.getByText("Toast 1")).toBeInTheDocument();
    expect(screen.getByText("Toast 2")).toBeInTheDocument();
    expect(screen.getByText("Toast 3")).toBeInTheDocument();
  });

  it("has notifications aria-label", () => {
    const toasts: ToastType[] = [{ id: "1", type: "success", title: "Toast 1" }];

    render(<ToastContainer toasts={toasts} onDismiss={mockOnDismiss} />);

    expect(screen.getByLabelText("Notifications")).toBeInTheDocument();
  });
});
