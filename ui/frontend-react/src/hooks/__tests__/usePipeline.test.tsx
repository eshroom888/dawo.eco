/**
 * Tests for usePipeline hook.
 *
 * Story 5-5, Task 12.7: Test data fetching and state management.
 */

import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import { usePipeline } from "../usePipeline";

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
    {children}
  </SWRConfig>
);

const mockSummary = {
  total_leads: 25,
  status_counts: { new: 5, contacted: 10, converted: 3 },
  conversion_rate: 12.0,
  avg_days_in_pipeline: 14,
  followup_count: 3,
};

const mockMetrics = {
  conversion_rate: 12.0,
  total_leads: 25,
  converted_count: 3,
  avg_time_per_stage: { new: 2.5, contacted: 5.0 },
  weekly_trend: [{ week: "2026-W06", new_leads: 5, converted: 1 }],
};

const mockLeadsResponse = {
  leads: [
    {
      id: "lead-1",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
      company: "TestCo",
      job_title: "Manager",
      status: "contacted",
      source: "linkedin",
      score: 75,
      last_contacted_at: null,
      days_since_contact: null,
      needs_followup: false,
      contact_count: 1,
      created_at: "2026-01-15T00:00:00Z",
    },
  ],
  total_count: 1,
  has_more: false,
  next_cursor: null,
};

const mockFollowups: never[] = [];

describe("usePipeline", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/pipeline/summary")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes("/pipeline/metrics")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockMetrics),
        });
      }
      if (url.includes("/pipeline/followups")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockFollowups),
        });
      }
      if (url.includes("/pipeline/leads")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockLeadsResponse),
        });
      }
      return Promise.resolve({ ok: false, status: 404 });
    });
  });

  it("fetches summary data", async () => {
    const { result } = renderHook(() => usePipeline(), { wrapper });

    await waitFor(() => {
      expect(result.current.summary).not.toBeNull();
    });

    expect(result.current.summary?.total_leads).toBe(25);
    expect(result.current.summary?.conversion_rate).toBe(12.0);
  });

  it("fetches metrics data", async () => {
    const { result } = renderHook(() => usePipeline(), { wrapper });

    await waitFor(() => {
      expect(result.current.metrics).not.toBeNull();
    });

    expect(result.current.metrics?.conversion_rate).toBe(12.0);
    expect(result.current.metrics?.total_leads).toBe(25);
  });

  it("fetches lead list", async () => {
    const { result } = renderHook(() => usePipeline(), { wrapper });

    await waitFor(() => {
      expect(result.current.leads.length).toBe(1);
    });

    expect(result.current.leads[0].email).toBe("test@example.com");
    expect(result.current.totalCount).toBe(1);
    expect(result.current.hasMore).toBe(false);
  });

  it("provides default filter state", () => {
    const { result } = renderHook(() => usePipeline(), { wrapper });

    expect(result.current.filters.status).toBeNull();
    expect(result.current.filters.search).toBe("");
    expect(result.current.filters.sort).toBe("score");
    expect(result.current.filters.limit).toBe(25);
    expect(result.current.filters.offset).toBe(0);
  });

  it("resets offset when changing filters", () => {
    const { result } = renderHook(() => usePipeline(), { wrapper });

    act(() => {
      result.current.setFilters({ offset: 25 });
    });
    expect(result.current.filters.offset).toBe(25);

    act(() => {
      result.current.setFilters({ status: "contacted" });
    });
    // Offset resets when non-offset filter changes
    expect(result.current.filters.offset).toBe(0);
  });

  it("provides exportCSV function", () => {
    const { result } = renderHook(() => usePipeline(), { wrapper });
    expect(typeof result.current.exportCSV).toBe("function");
  });

  it("provides updateLeadStatus function", () => {
    const { result } = renderHook(() => usePipeline(), { wrapper });
    expect(typeof result.current.updateLeadStatus).toBe("function");
  });

  it("provides addNote function", () => {
    const { result } = renderHook(() => usePipeline(), { wrapper });
    expect(typeof result.current.addNote).toBe("function");
  });
});
