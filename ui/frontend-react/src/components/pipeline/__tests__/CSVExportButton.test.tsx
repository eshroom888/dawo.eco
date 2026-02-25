/**
 * Tests for CSVExportButton component.
 *
 * Story 5-5, Task 12.6: Test export trigger.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { CSVExportButton } from "../CSVExportButton";

describe("CSVExportButton", () => {
  it("renders Export CSV button", () => {
    render(<CSVExportButton onExport={jest.fn()} />);
    expect(screen.getByText("Export CSV")).toBeInTheDocument();
  });

  it("calls onExport when clicked", () => {
    const onExport = jest.fn();
    render(<CSVExportButton onExport={onExport} />);
    fireEvent.click(screen.getByText("Export CSV"));
    expect(onExport).toHaveBeenCalledTimes(1);
  });

  it("passes current status filter to onExport", () => {
    const onExport = jest.fn();
    render(<CSVExportButton onExport={onExport} currentStatus="contacted" />);
    fireEvent.click(screen.getByText("Export CSV"));
    expect(onExport).toHaveBeenCalledWith("contacted");
  });

  it("passes undefined when no status filter", () => {
    const onExport = jest.fn();
    render(<CSVExportButton onExport={onExport} currentStatus={null} />);
    fireEvent.click(screen.getByText("Export CSV"));
    expect(onExport).toHaveBeenCalledWith(undefined);
  });

  it("has correct aria-label", () => {
    render(<CSVExportButton onExport={jest.fn()} />);
    expect(screen.getByLabelText("Export leads as CSV")).toBeInTheDocument();
  });
});
