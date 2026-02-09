/**
 * Tests for QualityScoreBadge component.
 *
 * Task 9.2: Test QualityScoreBadge color logic (green/yellow/red)
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { QualityScoreBadge } from "../QualityScoreBadge";

describe("QualityScoreBadge", () => {
  describe("color coding logic (AC #1)", () => {
    it("displays green for score >= 8", () => {
      render(<QualityScoreBadge score={8.0} />);
      const badge = screen.getByText("8.0");
      expect(badge).toHaveClass("bg-green-100");
      expect(badge).toHaveClass("text-green-800");
    });

    it("displays green for score = 10", () => {
      render(<QualityScoreBadge score={10.0} />);
      const badge = screen.getByText("10.0");
      expect(badge).toHaveClass("bg-green-100");
    });

    it("displays green for score = 9.5", () => {
      render(<QualityScoreBadge score={9.5} />);
      const badge = screen.getByText("9.5");
      expect(badge).toHaveClass("bg-green-100");
    });

    it("displays yellow for score >= 5 and < 8", () => {
      render(<QualityScoreBadge score={6.0} />);
      const badge = screen.getByText("6.0");
      expect(badge).toHaveClass("bg-yellow-100");
      expect(badge).toHaveClass("text-yellow-800");
    });

    it("displays yellow for score = 5 (boundary)", () => {
      render(<QualityScoreBadge score={5.0} />);
      const badge = screen.getByText("5.0");
      expect(badge).toHaveClass("bg-yellow-100");
    });

    it("displays yellow for score = 7.9 (just below green)", () => {
      render(<QualityScoreBadge score={7.9} />);
      const badge = screen.getByText("7.9");
      expect(badge).toHaveClass("bg-yellow-100");
    });

    it("displays red for score < 5", () => {
      render(<QualityScoreBadge score={3.0} />);
      const badge = screen.getByText("3.0");
      expect(badge).toHaveClass("bg-red-100");
      expect(badge).toHaveClass("text-red-800");
    });

    it("displays red for score = 4.9 (just below yellow)", () => {
      render(<QualityScoreBadge score={4.9} />);
      const badge = screen.getByText("4.9");
      expect(badge).toHaveClass("bg-red-100");
    });

    it("displays red for score = 0", () => {
      render(<QualityScoreBadge score={0} />);
      const badge = screen.getByText("0.0");
      expect(badge).toHaveClass("bg-red-100");
    });
  });

  describe("score display", () => {
    it("shows score by default", () => {
      render(<QualityScoreBadge score={7.5} />);
      expect(screen.getByText("7.5")).toBeInTheDocument();
    });

    it("shows color name when showScore is false", () => {
      render(<QualityScoreBadge score={8.5} showScore={false} />);
      expect(screen.getByText("green")).toBeInTheDocument();
    });

    it("rounds score to one decimal place", () => {
      render(<QualityScoreBadge score={7.567} />);
      expect(screen.getByText("7.6")).toBeInTheDocument();
    });
  });

  describe("size variants", () => {
    it("applies small size classes", () => {
      render(<QualityScoreBadge score={8.0} size="sm" />);
      const badge = screen.getByText("8.0");
      expect(badge).toHaveClass("text-xs");
    });

    it("applies large size classes", () => {
      render(<QualityScoreBadge score={8.0} size="lg" />);
      const badge = screen.getByText("8.0");
      expect(badge).toHaveClass("text-base");
    });
  });

  describe("accessibility", () => {
    it("has aria-label with score information", () => {
      render(<QualityScoreBadge score={8.5} />);
      const badge = screen.getByLabelText("Quality score: 8.5 out of 10");
      expect(badge).toBeInTheDocument();
    });
  });
});
