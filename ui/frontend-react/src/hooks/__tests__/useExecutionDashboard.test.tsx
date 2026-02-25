/**
 * Tests for useExecutionDashboard hook.
 *
 * Story 7-8, Task 8.3: Test data fetching, filtering, pagination, retry.
 * Target: 12+ tests.
 */

import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import { useExecutionDashboard } from "../useExecutionDashboard";

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
    {children}
  </SWRConfig>
);

const mockDashboard = {
  running: [
    {
      id: "log-1",
      agent_name: "health_claims_monitor",
      display_name: "Health Claims Monitor",
      started_at: "2026-02-25T10:00:00Z",
      completed_at: null,
      duration_seconds: null,
      status: "running",
      trigger_type: "scheduled",
      triggered_by: "scheduler",
      summary: null,
      error_message: null,
      items_processed: 0,
      has_log_output: false,
    },
  ],
  recent_completions: [
    {
      id: "log-2",
      agent_name: "novel_food_monitor",
      display_name: "Novel Food Monitor",
      started_at: "2026-02-25T09:00:00Z",
      completed_at: "2026-02-25T09:01:00Z",
      duration_seconds: 60,
      status: "success",
      trigger_type: "scheduled",
      triggered_by: "scheduler",
      summary: { items_processed: 42 },
      error_message: null,
      items_processed: 42,
      has_log_output: true,
    },
  ],
  recent_failures: [],
  total_executions_24h: 5,
  success_rate_24h: 80.0,
  avg_duration_24h: 45.0,
};

const mockExecutionList = {
  executions: [
    {
      id: "log-3",
      agent_name: "competitor_scanner",
      display_name: "Competitor Scanner",
      started_at: "2026-02-25T08:00:00Z",
      completed_at: "2026-02-25T08:02:00Z",
      duration_seconds: 120,
      status: "success",
      trigger_type: "manual",
      triggered_by: "operator",
      summary: { items_processed: 10 },
      error_message: null,
      items_processed: 10,
      has_log_output: true,
    },
  ],
  total_count: 1,
  has_more: false,
};

const mockDetail = {
  ...mockExecutionList.executions[0],
  log_output: "Processing...\nDone.",
  error_traceback: null,
};

const mockRetryResult = {
  agent_name: "competitor_scanner",
  status: "queued",
  message: "Triggered",
  triggered_at: "2026-02-25T12:00:00Z",
};

function setupFetchSuccess() {
  mockFetch.mockImplementation((url: string, options?: RequestInit) => {
    if (options?.method === "POST") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockRetryResult),
      });
    }
    if (url.includes("/executions/dashboard")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockDashboard),
      });
    }
    if (url.includes("/executions/") && !url.includes("?")) {
      // Detail fetch
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockDetail),
      });
    }
    if (url.includes("/executions/")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockExecutionList),
      });
    }
    return Promise.resolve({ ok: false, status: 404 });
  });
}

describe("useExecutionDashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupFetchSuccess();
  });

  // --- Dashboard data fetching ---

  it("fetches dashboard summary", async () => {
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });

    await waitFor(() => {
      expect(result.current.dashboard).not.toBeNull();
    });

    expect(result.current.dashboard!.running.length).toBe(1);
    expect(result.current.dashboard!.recent_completions.length).toBe(1);
    expect(result.current.dashboard!.total_executions_24h).toBe(5);
    expect(result.current.dashboard!.success_rate_24h).toBe(80.0);
  });

  it("fetches execution list", async () => {
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });

    await waitFor(() => {
      expect(result.current.executions).not.toBeNull();
    });

    expect(result.current.executions!.executions.length).toBe(1);
    expect(result.current.executions!.total_count).toBe(1);
    expect(result.current.executions!.has_more).toBe(false);
  });

  it("returns null before data loads", () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });

    expect(result.current.dashboard).toBeNull();
    expect(result.current.executions).toBeNull();
  });

  it("reports loading state", () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });

  it("reports error on fetch failure", async () => {
    mockFetch.mockImplementation(() =>
      Promise.resolve({ ok: false, status: 500 })
    );

    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });

    await waitFor(() => {
      expect(result.current.error).not.toBeNull();
    });
  });

  // --- Filter changes ---

  it("filter changes update SWR key", async () => {
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });
    await waitFor(() => expect(result.current.dashboard).not.toBeNull());

    act(() => {
      result.current.setFilters({ agent_name: "health_claims_monitor" });
    });

    // SWR should make a new request with updated filter query
    await waitFor(() => {
      const filterCalls = mockFetch.mock.calls.filter(
        ([url]: [string]) =>
          url.includes("agent_name=health_claims_monitor")
      );
      expect(filterCalls.length).toBeGreaterThanOrEqual(1);
    });
  });

  // --- Pagination ---

  it("page state defaults to 0", () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });
    expect(result.current.page).toBe(0);
  });

  it("setPage updates pagination offset", async () => {
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });
    await waitFor(() => expect(result.current.executions).not.toBeNull());

    act(() => {
      result.current.setPage(2);
    });

    await waitFor(() => {
      const pageCalls = mockFetch.mock.calls.filter(
        ([url]: [string]) => url.includes("offset=50")
      );
      expect(pageCalls.length).toBeGreaterThanOrEqual(1);
    });
  });

  // --- Detail fetch ---

  it("getExecutionDetail fetches from correct endpoint", async () => {
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });
    await waitFor(() => expect(result.current.dashboard).not.toBeNull());

    let detail: any;
    await act(async () => {
      detail = await result.current.getExecutionDetail("log-3");
    });

    expect(detail.log_output).toBe("Processing...\nDone.");
  });

  it("getExecutionDetail throws on 404", async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (!options?.method && url.includes("/executions/") && !url.includes("dashboard") && !url.includes("?")) {
        return Promise.resolve({ ok: false, status: 404 });
      }
      // Default success for dashboard/list
      if (url.includes("/executions/dashboard")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockDashboard) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockExecutionList) });
    });

    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });
    await waitFor(() => expect(result.current.dashboard).not.toBeNull());

    await expect(
      act(async () => {
        await result.current.getExecutionDetail("nonexistent");
      })
    ).rejects.toThrow("Execution not found");
  });

  // --- Retry ---

  it("retryExecution POSTs to retry endpoint", async () => {
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });
    await waitFor(() => expect(result.current.dashboard).not.toBeNull());

    let retryResult: any;
    await act(async () => {
      retryResult = await result.current.retryExecution("log-3");
    });

    expect(retryResult.status).toBe("queued");

    const postCall = mockFetch.mock.calls.find(
      ([url, opts]: [string, RequestInit]) =>
        url.includes("/executions/log-3/retry") && opts?.method === "POST"
    );
    expect(postCall).toBeDefined();
  });

  it("retryExecution invalidates dashboard cache", async () => {
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });
    await waitFor(() => expect(result.current.dashboard).not.toBeNull());

    const fetchCountBefore = mockFetch.mock.calls.length;

    await act(async () => {
      await result.current.retryExecution("log-3");
    });

    // After retry, SWR revalidation should cause additional dashboard GET
    await waitFor(() => {
      const dashboardGets = mockFetch.mock.calls
        .slice(fetchCountBefore)
        .filter(
          ([url, opts]: [string, RequestInit?]) =>
            url.includes("/executions/dashboard") && !opts?.method
        );
      expect(dashboardGets.length).toBeGreaterThanOrEqual(1);
    });
  });

  // --- Refresh ---

  it("refresh function is callable", async () => {
    const { result } = renderHook(() => useExecutionDashboard(), { wrapper });
    await waitFor(() => expect(result.current.dashboard).not.toBeNull());

    expect(typeof result.current.refresh).toBe("function");
    act(() => {
      result.current.refresh();
    });
  });
});
