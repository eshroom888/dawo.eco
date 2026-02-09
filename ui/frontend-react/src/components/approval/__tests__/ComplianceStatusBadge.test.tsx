/**
 * Tests for ComplianceStatusBadge component.
 *
 * Task 9.3: Test ComplianceStatusBadge displays correct status
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { ComplianceStatusBadge } from "../ComplianceStatusBadge";
import { ComplianceStatus } from "@/types/approval";

describe("ComplianceStatusBadge", () => {
  describe("status display (AC #1)", () => {
    it("displays COMPLIANT status with green styling", () => {
      render(<ComplianceStatusBadge status={ComplianceStatus.COMPLIANT} />);
      const badge = screen.getByText("COMPLIANT");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("bg-green-100");
      expect(badge).toHaveClass("text-green-800");
    });

    it("displays WARNING status with yellow styling", () => {
      render(<ComplianceStatusBadge status={ComplianceStatus.WARNING} />);
      const badge = screen.getByText("WARNING");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("bg-yellow-100");
      expect(badge).toHaveClass("text-yellow-800");
    });

    it("displays REJECTED status with red styling", () => {
      render(<ComplianceStatusBadge status={ComplianceStatus.REJECTED} />);
      const badge = screen.getByText("REJECTED");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("bg-red-100");
      expect(badge).toHaveClass("text-red-800");
    });
  });

  describe("size variants", () => {
    it("applies small size classes", () => {
      render(<ComplianceStatusBadge status={ComplianceStatus.COMPLIANT} size="sm" />);
      const badge = screen.getByText("COMPLIANT");
      expect(badge).toHaveClass("text-xs");
    });

    it("applies medium size classes by default", () => {
      render(<ComplianceStatusBadge status={ComplianceStatus.COMPLIANT} />);
      const badge = screen.getByText("COMPLIANT");
      expect(badge).toHaveClass("text-sm");
    });

    it("applies large size classes", () => {
      render(<ComplianceStatusBadge status={ComplianceStatus.COMPLIANT} size="lg" />);
      const badge = screen.getByText("COMPLIANT");
      expect(badge).toHaveClass("text-base");
    });
  });

  describe("custom className", () => {
    it("accepts custom className", () => {
      render(
        <ComplianceStatusBadge
          status={ComplianceStatus.COMPLIANT}
          className="custom-class"
        />
      );
      const badge = screen.getByText("COMPLIANT");
      expect(badge).toHaveClass("custom-class");
    });
  });
});
