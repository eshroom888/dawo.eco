/**
 * Tests for PipelineFilters component.
 *
 * Story 5-5, Task 12.5: Test filter event emissions.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { PipelineFilters } from "../PipelineFilters";

describe("PipelineFilters", () => {
  const defaultProps = {
    status: null,
    search: "",
    sort: "score",
    onStatusChange: jest.fn(),
    onSearchChange: jest.fn(),
    onSortChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders search input", () => {
    render(<PipelineFilters {...defaultProps} />);
    expect(screen.getByPlaceholderText("Search leads...")).toBeInTheDocument();
  });

  it("renders status filter dropdown", () => {
    render(<PipelineFilters {...defaultProps} />);
    expect(screen.getByLabelText("Filter by status")).toBeInTheDocument();
  });

  it("renders sort dropdown", () => {
    render(<PipelineFilters {...defaultProps} />);
    expect(screen.getByLabelText("Sort by")).toBeInTheDocument();
  });

  it("emits search change on input", () => {
    render(<PipelineFilters {...defaultProps} />);
    const input = screen.getByPlaceholderText("Search leads...");
    fireEvent.change(input, { target: { value: "EcoCorp" } });
    expect(defaultProps.onSearchChange).toHaveBeenCalledWith("EcoCorp");
  });

  it("emits status change on select", () => {
    render(<PipelineFilters {...defaultProps} />);
    const select = screen.getByLabelText("Filter by status");
    fireEvent.change(select, { target: { value: "contacted" } });
    expect(defaultProps.onStatusChange).toHaveBeenCalledWith("contacted");
  });

  it("emits null when All Statuses selected", () => {
    render(<PipelineFilters {...defaultProps} status="contacted" />);
    const select = screen.getByLabelText("Filter by status");
    fireEvent.change(select, { target: { value: "" } });
    expect(defaultProps.onStatusChange).toHaveBeenCalledWith(null);
  });

  it("shows Clear button when filters are active", () => {
    render(<PipelineFilters {...defaultProps} status="contacted" />);
    expect(screen.getByText("Clear")).toBeInTheDocument();
  });

  it("does not show Clear button when no filters active", () => {
    render(<PipelineFilters {...defaultProps} />);
    expect(screen.queryByText("Clear")).not.toBeInTheDocument();
  });
});
