/**
 * useAgentTriggers hook.
 *
 * Story 7-7, Task 7.2: Data fetching hook for manual agent/team triggering.
 * Provides agent list, team list, and trigger/queue actions via SWR.
 */

import useSWR from "swr";
import { useCallback } from "react";
import {
  TriggerableAgent,
  TriggerableAgentListResponse,
  Team,
  TeamListResponse,
  TriggerResult,
  TeamTriggerResult,
} from "@/types/triggers";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
const REFRESH_INTERVAL = 15000; // 15s auto-refresh

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const error = new Error(`API error: ${response.status}`);
    throw error;
  }
  return response.json();
}

export interface UseAgentTriggersResult {
  agents: TriggerableAgent[];
  teams: Team[];
  isLoading: boolean;
  error: Error | null;
  triggerAgent: (
    agentName: string,
    overrides?: Record<string, unknown>
  ) => Promise<TriggerResult>;
  queueAgent: (agentName: string) => Promise<TriggerResult>;
  triggerTeam: (teamName: string) => Promise<TeamTriggerResult>;
  refresh: () => void;
}

/**
 * Hook for manual agent/team triggering with auto-refreshing agent status.
 */
export function useAgentTriggers(): UseAgentTriggersResult {
  // Fetch triggerable agents with auto-refresh
  const {
    data: agentsData,
    error: agentsError,
    isLoading: agentsLoading,
    mutate: mutateAgents,
  } = useSWR<TriggerableAgentListResponse>(
    `${API_BASE}/agents/triggerable`,
    fetcher,
    { refreshInterval: REFRESH_INTERVAL, revalidateOnFocus: true }
  );

  // Fetch teams (static, no auto-refresh needed)
  const {
    data: teamsData,
    error: teamsError,
    isLoading: teamsLoading,
  } = useSWR<TeamListResponse>(`${API_BASE}/teams/`, fetcher);

  // Trigger a single agent
  const triggerAgent = useCallback(
    async (
      agentName: string,
      overrides?: Record<string, unknown>
    ): Promise<TriggerResult> => {
      const response = await fetch(
        `${API_BASE}/agents/${agentName}/trigger`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            config_overrides: overrides || null,
            force: false,
          }),
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || `Failed to trigger agent: ${response.status}`);
      }

      const result: TriggerResult = await response.json();
      // Invalidate agent cache to show updated status
      mutateAgents();
      return result;
    },
    [mutateAgents]
  );

  // Queue agent for after current run
  const queueAgent = useCallback(
    async (agentName: string): Promise<TriggerResult> => {
      const response = await fetch(
        `${API_BASE}/agents/${agentName}/queue`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || `Failed to queue agent: ${response.status}`);
      }

      const result: TriggerResult = await response.json();
      mutateAgents();
      return result;
    },
    [mutateAgents]
  );

  // Trigger a team
  const triggerTeam = useCallback(
    async (teamName: string): Promise<TeamTriggerResult> => {
      const response = await fetch(
        `${API_BASE}/teams/${teamName}/trigger`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || `Failed to trigger team: ${response.status}`);
      }

      const result: TeamTriggerResult = await response.json();
      mutateAgents();
      return result;
    },
    [mutateAgents]
  );

  // Refresh all data
  const refresh = useCallback(() => {
    mutateAgents();
  }, [mutateAgents]);

  return {
    agents: agentsData?.agents ?? [],
    teams: teamsData?.teams ?? [],
    isLoading: agentsLoading || teamsLoading,
    error: agentsError || teamsError || null,
    triggerAgent,
    queueAgent,
    triggerTeam,
    refresh,
  };
}

export default useAgentTriggers;
