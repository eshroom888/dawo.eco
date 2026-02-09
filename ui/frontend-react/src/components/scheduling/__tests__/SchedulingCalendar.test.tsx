/**
 * Tests for SchedulingCalendar component.
 *
 * Story 4-4, Task 10: Test calendar renders with scheduled posts,
 * view toggle, conflict highlighting, and responsive layout.
 */

import React from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { SchedulingCalendar } from "../SchedulingCalendar";
import { ScheduledItem, CalendarView } from "@/types/schedule";
import { SourcePriority, ComplianceStatus } from "@/types/approval";

// Mock scheduled items for testing
const mockScheduledItems: ScheduledItem[] = [
  {
    id: "1",
    title: "Test post about mushrooms",
    thumbnail_url: "https://example.com/thumb1.jpg",
    scheduled_publish_time: new Date(2026, 1, 10, 9, 0).toISOString(), // Feb 10, 9am
    source_type: "instagram_post",
    source_priority: SourcePriority.TRENDING,
    quality_score: 8.5,
    quality_color: "green",
    compliance_status: ComplianceStatus.COMPLIANT,
    conflicts: [],
    is_imminent: false,
  },
  {
    id: "2",
    title: "Evergreen wellness content",
    thumbnail_url: "https://example.com/thumb2.jpg",
    scheduled_publish_time: new Date(2026, 1, 10, 14, 0).toISOString(), // Feb 10, 2pm
    source_type: "instagram_post",
    source_priority: SourcePriority.EVERGREEN,
    quality_score: 7.2,
    quality_color: "yellow",
    compliance_status: ComplianceStatus.COMPLIANT,
    conflicts: [],
    is_imminent: false,
  },
  {
    id: "3",
    title: "Research based post",
    thumbnail_url: "https://example.com/thumb3.jpg",
    scheduled_publish_time: new Date(2026, 1, 11, 10, 0).toISOString(), // Feb 11, 10am
    source_type: "instagram_post",
    source_priority: SourcePriority.RESEARCH,
    quality_score: 6.0,
    quality_color: "yellow",
    compliance_status: ComplianceStatus.WARNING,
    conflicts: [],
    is_imminent: false,
  },
];

// Mock items with conflicts for conflict testing
const mockConflictingItems: ScheduledItem[] = [
  {
    id: "4",
    title: "Post 1 at 9am",
    thumbnail_url: "https://example.com/thumb4.jpg",
    scheduled_publish_time: new Date(2026, 1, 10, 9, 0).toISOString(),
    source_type: "instagram_post",
    source_priority: SourcePriority.TRENDING,
    quality_score: 8.0,
    quality_color: "green",
    compliance_status: ComplianceStatus.COMPLIANT,
    conflicts: ["5", "6"],
    is_imminent: false,
  },
  {
    id: "5",
    title: "Post 2 at 9am (conflict)",
    thumbnail_url: "https://example.com/thumb5.jpg",
    scheduled_publish_time: new Date(2026, 1, 10, 9, 0).toISOString(),
    source_type: "instagram_post",
    source_priority: SourcePriority.SCHEDULED,
    quality_score: 7.5,
    quality_color: "yellow",
    compliance_status: ComplianceStatus.COMPLIANT,
    conflicts: ["4", "6"],
    is_imminent: false,
  },
  {
    id: "6",
    title: "Post 3 at 9am (conflict)",
    thumbnail_url: "https://example.com/thumb6.jpg",
    scheduled_publish_time: new Date(2026, 1, 10, 9, 15).toISOString(),
    source_type: "instagram_post",
    source_priority: SourcePriority.EVERGREEN,
    quality_score: 7.0,
    quality_color: "yellow",
    compliance_status: ComplianceStatus.COMPLIANT,
    conflicts: ["4", "5"],
    is_imminent: false,
  },
];

// Mock imminent item for lock testing
const mockImminentItem: ScheduledItem = {
  id: "7",
  title: "Publishing soon post",
  thumbnail_url: "https://example.com/thumb7.jpg",
  scheduled_publish_time: new Date(Date.now() + 30 * 60 * 1000).toISOString(), // 30 min from now
  source_type: "instagram_post",
  source_priority: SourcePriority.TRENDING,
  quality_score: 9.0,
  quality_color: "green",
  compliance_status: ComplianceStatus.COMPLIANT,
  conflicts: [],
  is_imminent: true,
};

describe("SchedulingCalendar", () => {
  describe("Task 10.1: Calendar renders with scheduled posts", () => {
    it("renders calendar container", () => {
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
        />
      );
      expect(screen.getByTestId("scheduling-calendar")).toBeInTheDocument();
    });

    it("displays scheduled posts as events", () => {
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
        />
      );
      expect(screen.getByText("Test post about mushrooms")).toBeInTheDocument();
      expect(screen.getByText("Evergreen wellness content")).toBeInTheDocument();
    });

    it("shows loading skeleton when isLoading is true", () => {
      render(
        <SchedulingCalendar
          items={[]}
          isLoading={true}
        />
      );
      expect(screen.getByTestId("calendar-skeleton")).toBeInTheDocument();
    });

    it("shows empty state when no items", () => {
      render(
        <SchedulingCalendar
          items={[]}
          isLoading={false}
        />
      );
      expect(screen.getByText(/no posts scheduled/i)).toBeInTheDocument();
    });
  });

  describe("Task 10.6: View toggle (week/month/day)", () => {
    it("defaults to week view", () => {
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
        />
      );
      const weekButton = screen.getByRole("button", { name: /week/i });
      expect(weekButton).toHaveAttribute("aria-pressed", "true");
    });

    it("switches to month view when month button clicked", () => {
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
        />
      );
      const monthButton = screen.getByRole("button", { name: /month/i });
      fireEvent.click(monthButton);
      expect(monthButton).toHaveAttribute("aria-pressed", "true");
    });

    it("switches to day view when day button clicked", () => {
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
        />
      );
      const dayButton = screen.getByRole("button", { name: /day/i });
      fireEvent.click(dayButton);
      expect(dayButton).toHaveAttribute("aria-pressed", "true");
    });

    it("calls onViewChange when view changes", () => {
      const onViewChange = jest.fn();
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
          onViewChange={onViewChange}
        />
      );
      const monthButton = screen.getByRole("button", { name: /month/i });
      fireEvent.click(monthButton);
      expect(onViewChange).toHaveBeenCalledWith("month");
    });
  });

  describe("Task 10.3: Conflict highlighting", () => {
    it("highlights items with conflicts", () => {
      render(
        <SchedulingCalendar
          items={mockConflictingItems}
          isLoading={false}
        />
      );
      // Find events with conflict indicator
      const conflictIndicators = screen.getAllByTestId("conflict-indicator");
      expect(conflictIndicators.length).toBeGreaterThan(0);
    });

    it("shows conflict badge on day header when conflicts exist", () => {
      render(
        <SchedulingCalendar
          items={mockConflictingItems}
          isLoading={false}
        />
      );
      // Should show conflict badge for Feb 10 (3 posts at 9am)
      expect(screen.getByTestId("day-conflict-badge")).toBeInTheDocument();
    });
  });

  describe("Task 10.4: Publishing soon lock prevents editing", () => {
    it("shows 'Publishing soon' indicator for imminent posts", () => {
      render(
        <SchedulingCalendar
          items={[mockImminentItem]}
          isLoading={false}
        />
      );
      expect(screen.getByTestId("publishing-soon-badge")).toBeInTheDocument();
    });

    it("disables drag for imminent posts", () => {
      render(
        <SchedulingCalendar
          items={[mockImminentItem]}
          isLoading={false}
        />
      );
      const event = screen.getByTestId(`calendar-event-${mockImminentItem.id}`);
      expect(event).toHaveAttribute("draggable", "false");
    });
  });

  describe("Task 10.7: Mobile responsive layout", () => {
    beforeEach(() => {
      // Mock window.matchMedia for mobile viewport
      Object.defineProperty(window, "matchMedia", {
        writable: true,
        value: jest.fn().mockImplementation((query) => ({
          matches: query.includes("max-width: 768px"),
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });
    });

    it("shows list view on mobile", () => {
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
          forceMobileView={true}
        />
      );
      expect(screen.getByTestId("mobile-list-view")).toBeInTheDocument();
    });
  });

  describe("post count per day", () => {
    it("shows post count badge on day cells", () => {
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
          view="month"
        />
      );
      // Feb 10 has 2 posts
      const dayCell = screen.getByTestId("day-cell-2026-02-10");
      expect(within(dayCell).getByText("2")).toBeInTheDocument();
    });
  });

  describe("color-coding by content type", () => {
    it("applies color classes based on source priority", () => {
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
        />
      );
      const trendingEvent = screen.getByTestId("calendar-event-1");
      const evergreenEvent = screen.getByTestId("calendar-event-2");

      expect(trendingEvent).toHaveClass("bg-red-500"); // Trending
      expect(evergreenEvent).toHaveClass("bg-green-500"); // Evergreen
    });
  });

  describe("event click handling", () => {
    it("calls onEventClick when event is clicked", () => {
      const onEventClick = jest.fn();
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
          onEventClick={onEventClick}
        />
      );

      const event = screen.getByTestId("calendar-event-1");
      fireEvent.click(event);

      expect(onEventClick).toHaveBeenCalledWith(mockScheduledItems[0]);
    });
  });

  describe("navigation", () => {
    it("shows navigation buttons", () => {
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
        />
      );
      expect(screen.getByRole("button", { name: /previous/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /today/i })).toBeInTheDocument();
    });

    it("calls onNavigate when navigation buttons clicked", () => {
      const onNavigate = jest.fn();
      render(
        <SchedulingCalendar
          items={mockScheduledItems}
          isLoading={false}
          onNavigate={onNavigate}
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      expect(onNavigate).toHaveBeenCalled();
    });
  });
});
