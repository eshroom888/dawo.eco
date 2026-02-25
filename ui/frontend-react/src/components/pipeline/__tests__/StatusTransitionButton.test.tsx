/**
 * Tests for StatusTransitionButton component.
 *
 * Story 5-5, Task 12.3: Test valid next statuses display.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatusTransitionButton } from "../StatusTransitionButton";

describe("StatusTransitionButton", () => {
  it("shows Change Status button for status with transitions", () => {
    render(
      <StatusTransitionButton
        currentStatus="contacted"
        onTransition={jest.fn()}
      />
    );
    expect(screen.getByText("Change Status")).toBeInTheDocument();
  });

  it("shows valid next statuses in dropdown when clicked", () => {
    render(
      <StatusTransitionButton
        currentStatus="contacted"
        onTransition={jest.fn()}
      />
    );
    fireEvent.click(screen.getByText("Change Status"));
    // contacted -> replied, lost, nurture
    expect(screen.getByText("Replied")).toBeInTheDocument();
    expect(screen.getByText("Lost")).toBeInTheDocument();
    expect(screen.getByText("Nurture")).toBeInTheDocument();
  });

  it("shows no transitions message for converted status", () => {
    render(
      <StatusTransitionButton
        currentStatus="converted"
        onTransition={jest.fn()}
      />
    );
    expect(screen.getByText("No transitions available")).toBeInTheDocument();
  });

  it("calls onTransition when a status is selected", async () => {
    const onTransition = jest.fn().mockResolvedValue(undefined);
    render(
      <StatusTransitionButton
        currentStatus="contacted"
        onTransition={onTransition}
      />
    );
    fireEvent.click(screen.getByText("Change Status"));
    fireEvent.click(screen.getByText("Replied"));
    expect(onTransition).toHaveBeenCalledWith("replied");
  });

  it("shows reason input for Lost transition", () => {
    render(
      <StatusTransitionButton
        currentStatus="contacted"
        onTransition={jest.fn()}
      />
    );
    fireEvent.click(screen.getByText("Change Status"));
    fireEvent.click(screen.getByText("Lost"));
    expect(screen.getByPlaceholderText("Optional reason...")).toBeInTheDocument();
  });

  it("disables button when isLoading", () => {
    render(
      <StatusTransitionButton
        currentStatus="contacted"
        onTransition={jest.fn()}
        isLoading={true}
      />
    );
    expect(screen.getByText("Updating...")).toBeDisabled();
  });
});
