/**
 * Tests for LeadHistoryTimeline component.
 *
 * Story 5-5, Task 12.4: Test activity entry rendering.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { LeadHistoryTimeline } from "../LeadHistoryTimeline";
import { LeadHistoryEntry } from "@/types/pipeline";

const mockEntries: LeadHistoryEntry[] = [
  {
    id: "act-1",
    lead_id: "lead-1",
    activity_type: "status_change",
    description: "Status changed from new to contacted",
    timestamp: new Date().toISOString(),
    actor: "system",
    metadata: { old_status: "new", new_status: "contacted" },
  },
  {
    id: "act-2",
    lead_id: "lead-1",
    activity_type: "note_added",
    description: "Follow up next week",
    timestamp: new Date().toISOString(),
    actor: "operator",
    metadata: null,
  },
  {
    id: "act-3",
    lead_id: "lead-1",
    activity_type: "email_sent",
    description: "Outreach email sent",
    timestamp: new Date().toISOString(),
    actor: "system",
    metadata: {},
  },
];

describe("LeadHistoryTimeline", () => {
  it("renders all activity entries", () => {
    render(<LeadHistoryTimeline entries={mockEntries} />);
    expect(screen.getByText("Status changed from new to contacted")).toBeInTheDocument();
    expect(screen.getByText("Follow up next week")).toBeInTheDocument();
    expect(screen.getByText("Outreach email sent")).toBeInTheDocument();
  });

  it("shows actor for each entry", () => {
    render(<LeadHistoryTimeline entries={mockEntries} />);
    expect(screen.getAllByText(/by system/).length).toBe(2);
    expect(screen.getByText(/by operator/)).toBeInTheDocument();
  });

  it("shows metadata for status changes", () => {
    render(<LeadHistoryTimeline entries={mockEntries} />);
    expect(screen.getByText(/new/)).toBeInTheDocument();
    expect(screen.getByText(/contacted/)).toBeInTheDocument();
  });

  it("shows empty message when no entries", () => {
    render(<LeadHistoryTimeline entries={[]} />);
    expect(screen.getByText("No activity history")).toBeInTheDocument();
  });
});
