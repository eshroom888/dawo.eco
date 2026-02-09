/**
 * Tests for RetryButton component.
 *
 * Story 4-5, Task 9.7: Test dashboard displays retry functionality correctly.
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RetryButton } from "../RetryButton";

// Mock fetch
global.fetch = jest.fn();

describe("RetryButton", () => {
  const mockItemId = "test-item-123";

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Initial rendering", () => {
    it("renders retry button with correct text", () => {
      render(<RetryButton itemId={mockItemId} />);
      expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    });

    it("renders with correct testid", () => {
      render(<RetryButton itemId={mockItemId} />);
      expect(screen.getByTestId(`retry-button-${mockItemId}`)).toBeInTheDocument();
    });

    it("renders with small size by default", () => {
      render(<RetryButton itemId={mockItemId} />);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("px-2", "py-1", "text-xs");
    });

    it("renders with medium size when specified", () => {
      render(<RetryButton itemId={mockItemId} size="md" />);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("px-3", "py-1.5", "text-sm");
    });

    it("renders with large size when specified", () => {
      render(<RetryButton itemId={mockItemId} size="lg" />);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("px-4", "py-2", "text-base");
    });
  });

  describe("Retry functionality", () => {
    it("shows loading state when clicked", async () => {
      (global.fetch as jest.Mock).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<RetryButton itemId={mockItemId} />);
      const button = screen.getByRole("button");

      fireEvent.click(button);

      expect(screen.getByText("Retrying...")).toBeInTheDocument();
      expect(button).toBeDisabled();
    });

    it("calls correct API endpoint on click", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: "Retry initiated",
          item_id: mockItemId,
          job_id: "job-123",
        }),
      });

      render(<RetryButton itemId={mockItemId} />);
      fireEvent.click(screen.getByRole("button"));

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          `/api/schedule/${mockItemId}/retry-publish`,
          expect.objectContaining({
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ force: false }),
          })
        );
      });
    });

    it("calls onRetrySuccess callback on successful retry", async () => {
      const successResponse = {
        success: true,
        message: "Retry initiated",
        item_id: mockItemId,
        job_id: "job-123",
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => successResponse,
      });

      const onRetrySuccess = jest.fn();
      render(
        <RetryButton itemId={mockItemId} onRetrySuccess={onRetrySuccess} />
      );

      fireEvent.click(screen.getByRole("button"));

      await waitFor(() => {
        expect(onRetrySuccess).toHaveBeenCalledWith(successResponse);
      });
    });

    it("calls onRetryError callback on failed retry", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: "Item must be in PUBLISH_FAILED status" }),
      });

      const onRetryError = jest.fn();
      render(<RetryButton itemId={mockItemId} onRetryError={onRetryError} />);

      fireEvent.click(screen.getByRole("button"));

      await waitFor(() => {
        expect(onRetryError).toHaveBeenCalledWith(
          expect.objectContaining({
            message: "Item must be in PUBLISH_FAILED status",
          })
        );
      });
    });

    it("displays error message when retry fails", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 429,
        json: async () => ({ detail: "Too many recent attempts" }),
      });

      render(<RetryButton itemId={mockItemId} />);
      fireEvent.click(screen.getByRole("button"));

      await waitFor(() => {
        expect(screen.getByTestId("retry-error")).toBeInTheDocument();
        expect(screen.getByText("Too many recent attempts")).toBeInTheDocument();
      });
    });

    it("handles network errors gracefully", async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error("Network error"));

      const onRetryError = jest.fn();
      render(<RetryButton itemId={mockItemId} onRetryError={onRetryError} />);

      fireEvent.click(screen.getByRole("button"));

      await waitFor(() => {
        expect(onRetryError).toHaveBeenCalled();
        expect(screen.getByText("Network error")).toBeInTheDocument();
      });
    });
  });

  describe("Button state", () => {
    it("is not disabled initially", () => {
      render(<RetryButton itemId={mockItemId} />);
      expect(screen.getByRole("button")).not.toBeDisabled();
    });

    it("is disabled while retrying", async () => {
      (global.fetch as jest.Mock).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: async () => ({ success: true }),
                }),
              100
            )
          )
      );

      render(<RetryButton itemId={mockItemId} />);
      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByRole("button")).toBeDisabled();
    });

    it("re-enables after retry completes", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      render(<RetryButton itemId={mockItemId} />);
      fireEvent.click(screen.getByRole("button"));

      await waitFor(() => {
        expect(screen.getByRole("button")).not.toBeDisabled();
      });
    });
  });

  describe("Custom styling", () => {
    it("applies custom className", () => {
      render(<RetryButton itemId={mockItemId} className="custom-class" />);
      expect(screen.getByRole("button")).toHaveClass("custom-class");
    });
  });
});
