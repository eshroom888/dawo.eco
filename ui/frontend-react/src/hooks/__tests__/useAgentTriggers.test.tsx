/**
 * Tests for useAgentTriggers hook.
 *
 * Story 7-7, Task 7.3: Test data fetching, trigger actions, and error handling.
 * Target: 12+ tests.
 */

import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import { useAgentTriggers } from "../useAgentTriggers";

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
    {children}
  </SWRConfig>
);

const mockAgentsResponse = {
  agents: [
    {
      agent_name: "health_claims_monitor",
      display_name: "Health Claims Monitor",
      description: "Monitors EU health claims register",
      last_run_status: "completed",
      last_run_at: "2026-02-24T10:00:00Z",
      last_run_duration_seconds: 45.2,
      is_running: false,
      schedule_cron: "0 */6 * * *",
      next_scheduled_run: "2026-02-24T16:00:00Z",
    },
    {
      agent_name: "novel_food_monitor",
      display_name: "Novel Food Monitor",
      description: "Monitors novel food catalogue",
      last_run_status: "failed",
      last_run_at: "2026-02-24T09:00:00Z",
      last_run_duration_seconds: 12.1,
      is_running: true,
      schedule_cron: "0 */12 * * *",
      next_scheduled_run: null,
    },
  ],
  total_count: 2,
};

const mockTeamsResponse = {
  teams: [
    {
      team_name: "regulatory_monitors",
      display_name: "Regulatory Monitors",
      agents: ["health_claims_monitor", "novel_food_monitor"],
      description: "All regulatory monitoring agents",
    },
    {
      team_name: "all_scanners",
      display_name: "All Scanners",
      agents: ["health_claims_monitor", "novel_food_monitor"],
      description: "All scanner agents",
    },
  ],
};

const mockTriggerResult = {
  agent_name: "health_claims_monitor",
  status: "queued",
  job_id: "job-abc-123",
  triggered_at: "2026-02-24T12:00:00Z",
  message: "Agent queued for immediate execution",
};

const mockTeamTriggerResult = {
  team_name: "regulatory_monitors",
  agent_results: [
    {
      agent_name: "health_claims_monitor",
      status: "queued",
      job_id: "job-abc-123",
      triggered_at: "2026-02-24T12:00:00Z",
      message: "Agent queued",
    },
    {
      agent_name: "novel_food_monitor",
      status: "already_running",
      job_id: null,
      triggered_at: "2026-02-24T12:00:00Z",
      message: "Agent is already running",
    },
  ],
  total: 2,
  queued: 1,
  skipped_running: 1,
  failed: 0,
};

function setupFetchSuccess() {
  mockFetch.mockImplementation((url: string, options?: RequestInit) => {
    if (options?.method === "POST") {
      if (url.includes("/teams/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTeamTriggerResult),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockTriggerResult),
      });
    }
    if (url.includes("/agents/triggerable")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAgentsResponse),
      });
    }
    if (url.includes("/teams/")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockTeamsResponse),
      });
    }
    return Promise.resolve({ ok: false, status: 404 });
  });
}

describe("useAgentTriggers", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupFetchSuccess();
  });

  // --- Data fetching tests ---

  it("fetches triggerable agents", async () => {
    const { result } = renderHook(() => useAgentTriggers(), { wrapper });

    await waitFor(() => {
      expect(result.current.agents.length).toBe(2);
    });

    expect(result.current.agents[0].agent_name).toBe("health_claims_monitor");
    expect(result.current.agents[1].agent_name).toBe("novel_food_monitor");
  });

  it("fetches team definitions", async () => {
    const { result } = renderHook(() => useAgentTriggers(), { wrapper });

    await waitFor(() => {
      expect(result.current.teams.length).toBe(2);
    });

    expect(result.current.teams[0].team_name).toBe("regulatory_monitors");
    expect(result.current.teams[1].team_name).toBe("all_scanners");
  });

  it("returns empty arrays before data loads", () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves
    const { result } = renderHook(() => useAgentTriggers(), { wrapper });

    expect(result.current.agents).toEqual([]);
    expect(result.current.teams).toEqual([]);
  });

  it("reports loading state", () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useAgentTriggers(), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });

  it("reports error on fetch failure", async () => {
    mockFetch.mockImplementation(() =>
      Promise.resolve({ ok: false, status: 500 })
    );

    const { result } = renderHook(() => useAgentTriggers(), { wrapper });

    await waitFor(() => {
      expect(result.current.error).not.toBeNull();
    });
  });

  // --- triggerAgent tests ---

  it("triggerAgent POSTs to correct endpoint", async () => {
    const { result } = renderHook(() => useAgentTriggers(), { wrapper });
    await waitFor(() => expect(result.current.agents.length).toBe(2));

    let triggerResult: any;
    await act(async () => {
      triggerResult = await result.current.triggerAgent("health_claims_monitor");
    });

    expect(triggerResult.status).toBe("queued");
    expect(triggerResult.job_id).toBe("job-abc-123");

    // Verify POST call
    const postCall = mockFetch.mock.calls.find(
      ([url, opts]: [string, RequestInit]) =>
        url.includes("/agents/health_claims_monitor/trigger") &&
        opts?.method === "POST"
    );
    expect(postCall).toBeDefined();
  });

  it("triggerAgent sends config_overrides", async () => {
    const { result } = renderHook(() => useAgentTriggers(), { wrapper });
    await waitFor(() => expect(result.current.agents.length).toBe(2));

    await act(async () => {
      await result.current.triggerAgent("health_claims_monitor", {
        keywords: ["mushroom"],
      });
    });

    const postCall = mockFetch.mock.calls.find(
      ([url, opts]: [string, RequestInit]) =>
        url.includes("/agents/health_claims_monitor/trigger") &&
        opts?.method === "POST"
    );
    const body = JSON.parse(postCall![1].body as string);
    expect(body.config_overrides).toEqual({ keywords: ["mushroom"] });
  });

  it("triggerAgent throws on 409 conflict", async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === "POST") {
        return Promise.resolve({
          ok: false,
          status: 409,
          json: () =>
            Promise.resolve({ detail: "Agent is already running" }),
        });
      }
      // Default GET responses
      if (url.includes("/agents/triggerable")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAgentsResponse),
        });
      }
      if (url.includes("/teams/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTeamsResponse),
        });
      }
      return Promise.resolve({ ok: false, status: 404 });
    });

    const { result } = renderHook(() => useAgentTriggers(), { wrapper });
    await waitFor(() => expect(result.current.agents.length).toBe(2));

    await expect(
      act(async () => {
        await result.current.triggerAgent("novel_food_monitor");
      })
    ).rejects.toThrow("Agent is already running");
  });

  // --- queueAgent tests ---

  it("queueAgent POSTs to queue endpoint", async () => {
    const { result } = renderHook(() => useAgentTriggers(), { wrapper });
    await waitFor(() => expect(result.current.agents.length).toBe(2));

    let queueResult: any;
    await act(async () => {
      queueResult = await result.current.queueAgent("health_claims_monitor");
    });

    expect(queueResult.status).toBe("queued");

    const postCall = mockFetch.mock.calls.find(
      ([url, opts]: [string, RequestInit]) =>
        url.includes("/agents/health_claims_monitor/queue") &&
        opts?.method === "POST"
    );
    expect(postCall).toBeDefined();
  });

  it("queueAgent throws on 404", async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === "POST") {
        return Promise.resolve({
          ok: false,
          status: 404,
          json: () =>
            Promise.resolve({ detail: "Agent not found" }),
        });
      }
      if (url.includes("/agents/triggerable")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAgentsResponse),
        });
      }
      if (url.includes("/teams/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTeamsResponse),
        });
      }
      return Promise.resolve({ ok: false, status: 404 });
    });

    const { result } = renderHook(() => useAgentTriggers(), { wrapper });
    await waitFor(() => expect(result.current.agents.length).toBe(2));

    await expect(
      act(async () => {
        await result.current.queueAgent("nonexistent_agent");
      })
    ).rejects.toThrow("Agent not found");
  });

  // --- triggerTeam tests ---

  it("triggerTeam POSTs to team endpoint", async () => {
    const { result } = renderHook(() => useAgentTriggers(), { wrapper });
    await waitFor(() => expect(result.current.teams.length).toBe(2));

    let teamResult: any;
    await act(async () => {
      teamResult = await result.current.triggerTeam("regulatory_monitors");
    });

    expect(teamResult.team_name).toBe("regulatory_monitors");
    expect(teamResult.queued).toBe(1);
    expect(teamResult.skipped_running).toBe(1);

    const postCall = mockFetch.mock.calls.find(
      ([url, opts]: [string, RequestInit]) =>
        url.includes("/teams/regulatory_monitors/trigger") &&
        opts?.method === "POST"
    );
    expect(postCall).toBeDefined();
  });

  it("triggerTeam throws on 503 service unavailable", async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === "POST") {
        return Promise.resolve({
          ok: false,
          status: 503,
          json: () =>
            Promise.resolve({ detail: "Job queue unavailable" }),
        });
      }
      if (url.includes("/agents/triggerable")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAgentsResponse),
        });
      }
      if (url.includes("/teams/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTeamsResponse),
        });
      }
      return Promise.resolve({ ok: false, status: 404 });
    });

    const { result } = renderHook(() => useAgentTriggers(), { wrapper });
    await waitFor(() => expect(result.current.agents.length).toBe(2));

    await expect(
      act(async () => {
        await result.current.triggerTeam("regulatory_monitors");
      })
    ).rejects.toThrow("Job queue unavailable");
  });

  // --- refresh + cache invalidation tests ---

  it("refresh function is callable", async () => {
    const { result } = renderHook(() => useAgentTriggers(), { wrapper });
    await waitFor(() => expect(result.current.agents.length).toBe(2));

    expect(typeof result.current.refresh).toBe("function");
    act(() => {
      result.current.refresh();
    });
    // No error thrown = success
  });

  it("triggerAgent invalidates agent cache", async () => {
    const { result } = renderHook(() => useAgentTriggers(), { wrapper });
    await waitFor(() => expect(result.current.agents.length).toBe(2));

    const fetchCountBefore = mockFetch.mock.calls.length;

    await act(async () => {
      await result.current.triggerAgent("health_claims_monitor");
    });

    // After trigger, SWR revalidation should cause additional GET call
    await waitFor(() => {
      const agentGets = mockFetch.mock.calls
        .slice(fetchCountBefore)
        .filter(
          ([url, opts]: [string, RequestInit?]) =>
            url.includes("/agents/triggerable") && !opts?.method
        );
      expect(agentGets.length).toBeGreaterThanOrEqual(1);
    });
  });
});
