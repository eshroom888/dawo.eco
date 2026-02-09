/**
 * Tests for PublishStatusBadge component.
 *
 * Story 4-5, Task 9.7: Test dashboard displays published post correctly.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { PublishStatusBadge } from "../PublishStatusBadge";

describe("PublishStatusBadge", () => {
  describe("Status display", () => {
    it("renders null when no status provided", () => {
      const { container } = render(<PublishStatusBadge />);
      expect(container).toBeEmptyDOMElement();
    });

    it("renders scheduled status with blue color", () => {
      render(<PublishStatusBadge status="scheduled" />);
      const badge = screen.getByTestId("publish-status-scheduled");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("bg-blue-500");
    });

    it("renders publishing status with yellow color and pulse animation", () => {
      render(<PublishStatusBadge status="publishing" />);
      const badge = screen.getByTestId("publish-status-publishing");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("bg-yellow-500");
      expect(badge).toHaveClass("animate-pulse");
    });

    it("renders published status with green color and checkmark", () => {
      render(<PublishStatusBadge status="published" />);
      const badge = screen.getByTestId("publish-status-published");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("bg-green-500");
      // Should have checkmark icon
      expect(badge.querySelector("svg")).toBeInTheDocument();
    });

    it("renders publish_failed status with red color and X icon", () => {
      render(<PublishStatusBadge status="publish_failed" />);
      const badge = screen.getByTestId("publish-status-publish_failed");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("bg-red-500");
      // Should have X icon
      expect(badge.querySelector("svg")).toBeInTheDocument();
    });
  });

  describe("Label display", () => {
    it("shows label by default", () => {
      render(<PublishStatusBadge status="published" />);
      expect(screen.getByText("Published")).toBeInTheDocument();
    });

    it("hides label when showLabel is false", () => {
      render(<PublishStatusBadge status="published" showLabel={false} />);
      expect(screen.queryByText("Published")).not.toBeInTheDocument();
    });

    it("shows correct label for publishing status", () => {
      render(<PublishStatusBadge status="publishing" />);
      expect(screen.getByText("Publishing...")).toBeInTheDocument();
    });

    it("shows correct label for failed status", () => {
      render(<PublishStatusBadge status="publish_failed" />);
      expect(screen.getByText("Failed")).toBeInTheDocument();
    });
  });

  describe("Custom styling", () => {
    it("applies custom className", () => {
      render(
        <PublishStatusBadge status="published" className="custom-class" />
      );
      const badge = screen.getByTestId("publish-status-published");
      expect(badge).toHaveClass("custom-class");
    });
  });
});
