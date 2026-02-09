/**
 * SchedulingCalendar component.
 *
 * Story 4-4, Task 1: Calendar view for scheduled posts with
 * week/month/day views, drag-and-drop, and conflict highlighting.
 *
 * Features:
 * - Week, month, and day view toggle
 * - Color-coded events by source type
 * - Conflict highlighting (red border for same-hour posts)
 * - Publishing soon lock indicator
 * - Mobile responsive (list view fallback)
 * - Post count badges per day
 */

import React, { useState, useMemo, useCallback } from "react";
import { Calendar, momentLocalizer, Views, View } from "react-big-calendar";
import moment from "moment";
import {
  ScheduledItem,
  CalendarEvent,
  CalendarView,
  getSourceTypeColor,
  CONFLICT_RULES,
} from "@/types/schedule";
import { SourcePriority } from "@/types/approval";
import { CalendarEventComponent } from "./CalendarEvent";
import { PublishingSoonBadge } from "./PublishingSoonBadge";
import { ConflictWarning } from "./ConflictWarning";
import { cn } from "@/lib/utils";

// Initialize moment localizer for react-big-calendar
const localizer = momentLocalizer(moment);

// Map CalendarView to react-big-calendar View
const VIEW_MAP: Record<CalendarView, View> = {
  day: Views.DAY,
  week: Views.WEEK,
  month: Views.MONTH,
};

// Reverse map for getting CalendarView from react-big-calendar View
const REVERSE_VIEW_MAP: Record<string, CalendarView> = {
  [Views.DAY]: "day",
  [Views.WEEK]: "week",
  [Views.MONTH]: "month",
};

// Source priority to color mapping
const PRIORITY_COLORS: Record<number, string> = {
  [SourcePriority.TRENDING]: "bg-red-500",
  [SourcePriority.SCHEDULED]: "bg-blue-500",
  [SourcePriority.EVERGREEN]: "bg-green-500",
  [SourcePriority.RESEARCH]: "bg-purple-500",
};

export interface SchedulingCalendarProps {
  /** Scheduled items to display on calendar */
  items: ScheduledItem[];
  /** Loading state for skeleton display */
  isLoading: boolean;
  /** Current calendar view */
  view?: CalendarView;
  /** Callback when view changes */
  onViewChange?: (view: CalendarView) => void;
  /** Current date for calendar navigation */
  date?: Date;
  /** Callback when date changes (navigation) */
  onNavigate?: (date: Date, view: CalendarView) => void;
  /** Callback when an event is clicked */
  onEventClick?: (item: ScheduledItem) => void;
  /** Callback when an event is dropped (rescheduled) */
  onEventDrop?: (item: ScheduledItem, newStart: Date) => void;
  /** Force mobile list view (for testing) */
  forceMobileView?: boolean;
}

/**
 * Calendar view for scheduled posts.
 *
 * Displays approved content scheduled for publishing with
 * drag-and-drop rescheduling, conflict detection, and
 * optimal time suggestions.
 */
export function SchedulingCalendar({
  items,
  isLoading,
  view: controlledView,
  onViewChange,
  date: controlledDate,
  onNavigate,
  onEventClick,
  onEventDrop,
  forceMobileView = false,
}: SchedulingCalendarProps): React.ReactElement {
  // Internal state for uncontrolled mode
  const [internalView, setInternalView] = useState<CalendarView>("week");
  const [internalDate, setInternalDate] = useState<Date>(new Date());

  // Use controlled or internal state
  const currentView = controlledView ?? internalView;
  const currentDate = controlledDate ?? internalDate;

  // Check for mobile viewport
  const [isMobile, setIsMobile] = useState(false);

  React.useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 768px)");
    setIsMobile(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  const showMobileView = forceMobileView || isMobile;

  // Convert ScheduledItem[] to CalendarEvent[]
  const events: CalendarEvent[] = useMemo(() => {
    return items.map((item) => {
      const start = new Date(item.scheduled_publish_time);
      const end = new Date(start.getTime() + 30 * 60 * 1000); // 30 min duration

      return {
        id: item.id,
        title: item.title,
        start,
        end,
        resource: item,
      };
    });
  }, [items]);

  // Calculate conflicts per hour
  const conflictsByHour = useMemo(() => {
    const hourCounts: Record<string, string[]> = {};

    items.forEach((item) => {
      const date = new Date(item.scheduled_publish_time);
      const hourKey = `${date.toISOString().slice(0, 13)}:00:00.000Z`;

      if (!hourCounts[hourKey]) {
        hourCounts[hourKey] = [];
      }
      hourCounts[hourKey].push(item.id);
    });

    return hourCounts;
  }, [items]);

  // Calculate post counts per day
  const postCountsByDay = useMemo(() => {
    const dayCounts: Record<string, number> = {};

    items.forEach((item) => {
      const date = new Date(item.scheduled_publish_time);
      const dayKey = date.toISOString().slice(0, 10); // YYYY-MM-DD

      dayCounts[dayKey] = (dayCounts[dayKey] || 0) + 1;
    });

    return dayCounts;
  }, [items]);

  // Check if a day has conflicts
  const hasConflicts = useCallback(
    (date: Date): boolean => {
      const dayKey = date.toISOString().slice(0, 10);
      const dayItems = items.filter(
        (item) =>
          new Date(item.scheduled_publish_time).toISOString().slice(0, 10) ===
          dayKey
      );

      // Check each hour for conflicts
      const hourCounts: Record<number, number> = {};
      dayItems.forEach((item) => {
        const hour = new Date(item.scheduled_publish_time).getHours();
        hourCounts[hour] = (hourCounts[hour] || 0) + 1;
      });

      return Object.values(hourCounts).some(
        (count) => count >= CONFLICT_RULES.WARNING_THRESHOLD
      );
    },
    [items]
  );

  // Handle view change
  const handleViewChange = useCallback(
    (newView: View) => {
      const calendarView = REVERSE_VIEW_MAP[newView];
      if (onViewChange) {
        onViewChange(calendarView);
      } else {
        setInternalView(calendarView);
      }
    },
    [onViewChange]
  );

  // Handle navigation
  const handleNavigate = useCallback(
    (newDate: Date) => {
      if (onNavigate) {
        onNavigate(newDate, currentView);
      } else {
        setInternalDate(newDate);
      }
    },
    [onNavigate, currentView]
  );

  // Handle event click
  const handleSelectEvent = useCallback(
    (event: CalendarEvent) => {
      if (onEventClick) {
        onEventClick(event.resource);
      }
    },
    [onEventClick]
  );

  // Handle event drop (drag-and-drop reschedule)
  const handleEventDrop = useCallback(
    ({
      event,
      start,
    }: {
      event: CalendarEvent;
      start: Date;
      end: Date;
    }) => {
      // Don't allow dropping imminent posts
      if (event.resource.is_imminent) {
        return;
      }

      if (onEventDrop) {
        onEventDrop(event.resource, start);
      }
    },
    [onEventDrop]
  );

  // Custom event styling
  const eventStyleGetter = useCallback(
    (event: CalendarEvent) => {
      const item = event.resource;
      const colorClass = PRIORITY_COLORS[item.source_priority] || "bg-gray-500";
      const hasItemConflicts = item.conflicts.length > 0;

      return {
        className: cn(
          colorClass,
          "text-white rounded px-1",
          hasItemConflicts && "ring-2 ring-red-600",
          item.is_imminent && "opacity-75"
        ),
      };
    },
    []
  );

  // Custom day cell wrapper for post count badge
  const DayCellWrapper = useCallback(
    ({ children, value }: { children: React.ReactNode; value: Date }) => {
      const dayKey = value.toISOString().slice(0, 10);
      const count = postCountsByDay[dayKey] || 0;
      const dayHasConflicts = hasConflicts(value);

      return (
        <div
          className="relative h-full"
          data-testid={`day-cell-${dayKey}`}
        >
          {children}
          {count > 0 && currentView === "month" && (
            <span className="absolute top-1 right-1 bg-gray-700 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {count}
            </span>
          )}
          {dayHasConflicts && (
            <span
              className="absolute top-1 left-1 bg-red-500 w-2 h-2 rounded-full"
              data-testid="day-conflict-badge"
            />
          )}
        </div>
      );
    },
    [postCountsByDay, hasConflicts, currentView]
  );

  // Custom event component
  const CustomEvent = useCallback(
    ({ event }: { event: CalendarEvent }) => {
      const item = event.resource;

      return (
        <div
          className={cn(
            "flex items-center gap-1 overflow-hidden",
            PRIORITY_COLORS[item.source_priority] || "bg-gray-500"
          )}
          data-testid={`calendar-event-${item.id}`}
          draggable={!item.is_imminent}
        >
          {item.is_imminent && (
            <PublishingSoonBadge data-testid="publishing-soon-badge" />
          )}
          {item.conflicts.length > 0 && (
            <span
              className="w-2 h-2 bg-red-600 rounded-full"
              data-testid="conflict-indicator"
            />
          )}
          <span className="truncate text-white text-xs">{item.title}</span>
        </div>
      );
    },
    []
  );

  // Loading skeleton
  if (isLoading) {
    return (
      <div
        className="h-[600px] bg-gray-100 animate-pulse rounded-lg"
        data-testid="calendar-skeleton"
      >
        <div className="flex items-center justify-center h-full text-gray-400">
          Loading calendar...
        </div>
      </div>
    );
  }

  // Empty state
  if (items.length === 0) {
    return (
      <div
        className="h-[600px] bg-gray-50 rounded-lg flex flex-col items-center justify-center"
        data-testid="scheduling-calendar"
      >
        <div className="text-gray-500 text-lg mb-2">No posts scheduled</div>
        <div className="text-gray-400 text-sm">
          Approve content to see it on the calendar
        </div>
      </div>
    );
  }

  // Mobile list view
  if (showMobileView) {
    return (
      <div
        className="space-y-2"
        data-testid="scheduling-calendar"
      >
        <div data-testid="mobile-list-view" className="space-y-2">
          {items
            .sort(
              (a, b) =>
                new Date(a.scheduled_publish_time).getTime() -
                new Date(b.scheduled_publish_time).getTime()
            )
            .map((item) => (
              <div
                key={item.id}
                className={cn(
                  "p-3 rounded-lg cursor-pointer",
                  PRIORITY_COLORS[item.source_priority] || "bg-gray-500",
                  "text-white"
                )}
                onClick={() => onEventClick?.(item)}
                data-testid={`calendar-event-${item.id}`}
                draggable={!item.is_imminent}
              >
                <div className="flex items-center gap-2">
                  {item.is_imminent && (
                    <PublishingSoonBadge data-testid="publishing-soon-badge" />
                  )}
                  {item.conflicts.length > 0 && (
                    <span
                      className="w-2 h-2 bg-red-600 rounded-full"
                      data-testid="conflict-indicator"
                    />
                  )}
                  <span className="font-medium">{item.title}</span>
                </div>
                <div className="text-sm opacity-80 mt-1">
                  {moment(item.scheduled_publish_time).format(
                    "MMM D, YYYY h:mm A"
                  )}
                </div>
              </div>
            ))}
        </div>
      </div>
    );
  }

  // Desktop calendar view
  return (
    <div
      className="h-[600px]"
      data-testid="scheduling-calendar"
    >
      {/* View toggle toolbar */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-2">
          <button
            className="px-3 py-1 rounded"
            onClick={() => handleNavigate(new Date())}
            aria-label="Today"
          >
            Today
          </button>
          <button
            className="px-3 py-1 rounded"
            onClick={() => {
              const newDate = moment(currentDate).subtract(1, currentView === "day" ? "day" : currentView === "week" ? "week" : "month").toDate();
              handleNavigate(newDate);
            }}
            aria-label="Previous"
          >
            ←
          </button>
          <button
            className="px-3 py-1 rounded"
            onClick={() => {
              const newDate = moment(currentDate).add(1, currentView === "day" ? "day" : currentView === "week" ? "week" : "month").toDate();
              handleNavigate(newDate);
            }}
            aria-label="Next"
          >
            →
          </button>
        </div>

        <div className="text-lg font-semibold">
          {moment(currentDate).format(
            currentView === "day"
              ? "MMMM D, YYYY"
              : currentView === "week"
              ? "MMMM YYYY"
              : "MMMM YYYY"
          )}
        </div>

        <div className="flex gap-1 bg-gray-100 rounded p-1">
          <button
            className={cn(
              "px-3 py-1 rounded",
              currentView === "day" && "bg-white shadow"
            )}
            onClick={() => handleViewChange(Views.DAY)}
            aria-pressed={currentView === "day"}
            aria-label="Day view"
          >
            Day
          </button>
          <button
            className={cn(
              "px-3 py-1 rounded",
              currentView === "week" && "bg-white shadow"
            )}
            onClick={() => handleViewChange(Views.WEEK)}
            aria-pressed={currentView === "week"}
            aria-label="Week view"
          >
            Week
          </button>
          <button
            className={cn(
              "px-3 py-1 rounded",
              currentView === "month" && "bg-white shadow"
            )}
            onClick={() => handleViewChange(Views.MONTH)}
            aria-pressed={currentView === "month"}
            aria-label="Month view"
          >
            Month
          </button>
        </div>
      </div>

      {/* Calendar */}
      <Calendar
        localizer={localizer}
        events={events}
        startAccessor="start"
        endAccessor="end"
        view={VIEW_MAP[currentView]}
        onView={handleViewChange}
        date={currentDate}
        onNavigate={handleNavigate}
        onSelectEvent={handleSelectEvent}
        onEventDrop={handleEventDrop}
        eventPropGetter={eventStyleGetter}
        components={{
          event: CustomEvent,
          dateCellWrapper: DayCellWrapper,
        }}
        draggableAccessor={(event) => !event.resource.is_imminent}
        style={{ height: "calc(100% - 60px)" }}
      />
    </div>
  );
}

export default SchedulingCalendar;
