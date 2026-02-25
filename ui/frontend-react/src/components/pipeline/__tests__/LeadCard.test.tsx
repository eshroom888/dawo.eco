/**
 * Tests for LeadCard component.
 *
 * Story 5-5, Task 12.2: Test lead info display and follow-up badge.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { LeadCard } from "../LeadCard";
import { PipelineLead } from "@/types/pipeline";

const mockLead: PipelineLead = {
  id: "abc-123",
  email: "jane@ecocorp.com",
  first_name: "Jane",
  last_name: "Doe",
  company: "EcoCorp",
  job_title: "Marketing Director",
  status: "contacted",
  source: "linkedin",
  score: 85,
  last_contacted_at: "2026-02-01T00:00:00Z",
  days_since_contact: 11,
  needs_followup: true,
  contact_count: 2,
  created_at: "2026-01-15T00:00:00Z",
};

describe("LeadCard", () => {
  it("displays company name", () => {
    render(<LeadCard lead={mockLead} />);
    expect(screen.getByText("EcoCorp")).toBeInTheDocument();
  });

  it("displays contact name and title", () => {
    render(<LeadCard lead={mockLead} />);
    expect(screen.getByText(/Jane Doe/)).toBeInTheDocument();
    expect(screen.getByText(/Marketing Director/)).toBeInTheDocument();
  });

  it("displays score badge", () => {
    render(<LeadCard lead={mockLead} />);
    expect(screen.getByText("85")).toBeInTheDocument();
  });

  it("displays status badge", () => {
    render(<LeadCard lead={mockLead} />);
    expect(screen.getByText("Contacted")).toBeInTheDocument();
  });

  it("displays follow-up badge when needs_followup is true", () => {
    render(<LeadCard lead={mockLead} />);
    expect(screen.getByText(/11d/)).toBeInTheDocument();
  });

  it("does not display follow-up badge when needs_followup is false", () => {
    const lead = { ...mockLead, needs_followup: false, days_since_contact: null };
    render(<LeadCard lead={lead} />);
    expect(screen.queryByText(/11d/)).not.toBeInTheDocument();
  });

  it("displays contact count", () => {
    render(<LeadCard lead={mockLead} />);
    expect(screen.getByText("2x contacted")).toBeInTheDocument();
  });

  it("calls onClick when clicked", () => {
    const handleClick = jest.fn();
    render(<LeadCard lead={mockLead} onClick={handleClick} />);
    fireEvent.click(screen.getByText("EcoCorp"));
    expect(handleClick).toHaveBeenCalledWith(mockLead);
  });

  it("has follow-up border highlight when needs_followup", () => {
    const { container } = render(<LeadCard lead={mockLead} />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("border-l-amber-400");
  });
});
