/**
 * TypeScript types for Manual Agent/Team Triggers.
 *
 * Story 7-7, Task 7.1: Mirrors backend Pydantic schemas for type-safe API communication.
 */

/**
 * Agent available for manual triggering with current status.
 */
export interface TriggerableAgent {
  agent_name: string;
  display_name: string;
  description: string | null;
  last_run_status: string | null;
  last_run_at: string | null;
  last_run_duration_seconds: number | null;
  is_running: boolean;
  schedule_cron: string | null;
  next_scheduled_run: string | null;
}

/**
 * Team definition for manual triggering.
 */
export interface Team {
  team_name: string;
  display_name: string;
  agents: string[];
  description: string;
}

/**
 * Result of triggering a single agent.
 */
export interface TriggerResult {
  agent_name: string;
  status: "queued" | "already_running" | "failed" | "not_found";
  job_id: string | null;
  triggered_at: string;
  message: string;
}

/**
 * Result of triggering a team.
 */
export interface TeamTriggerResult {
  team_name: string;
  agent_results: TriggerResult[];
  total: number;
  queued: number;
  skipped_running: number;
  failed: number;
}

/**
 * Filters for agent trigger list (future extension).
 */
export interface AgentTriggerFilters {
  search: string;
  status: string | null;
}

/**
 * API response for triggerable agents list.
 */
export interface TriggerableAgentListResponse {
  agents: TriggerableAgent[];
  total_count: number;
}

/**
 * API response for teams list.
 */
export interface TeamListResponse {
  teams: Team[];
}
