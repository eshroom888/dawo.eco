/**
 * Tests for PipelineSummaryCards component.
 *
 * Story 5-5, Task 12.1: Test metric card rendering.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { PipelineSummaryCards } from "../PipelineSummaryCards";
import { PipelineSummary } from "@/types/pipeline";

const mockSummary: PipelineSummary = {
  total_leads: 42,
  status_counts: { new: 10, contacted: 15, converted: 5, lost: 3 },
  conversion_rate: 11.9,
  avg_days_in_pipeline: 18,
  followup_count: 7,
};

describe("PipelineSummaryCards", () => {
  it("renders total leads value", () => {
    render(<PipelineSummaryCards summary={mockSummary} isLoading={false} />);
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders conversion rate with percentage", () => {
    render(<PipelineSummaryCards summary={mockSummary} isLoading={false} />);
    expect(screen.getByText("11.9%")).toBeInTheDocument();
  });

  it("renders follow-up count", () => {
    render(<PipelineSummaryCards summary={mockSummary} isLoading={false} />);
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("renders avg pipeline time", () => {
    render(<PipelineSummaryCards summary={mockSummary} isLoading={false} />);
    expect(screen.getByText("18d")).toBeInTheDocument();
  });

  it("shows skeletons when loading", () => {
    const { container } = render(
      <PipelineSummaryCards summary={null} isLoading={true} />
    );
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders zero values when summary is null and not loading", () => {
    render(<PipelineSummaryCards summary={null} isLoading={false} />);
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });
});
