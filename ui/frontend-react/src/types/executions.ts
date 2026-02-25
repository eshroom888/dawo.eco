/**
 * TypeScript types for Execution Dashboard.
 *
 * Story 7-8, Task 8.1: Mirrors backend Pydantic schemas for type-safe API communication.
 */

/**
 * Execution log entry for list views.
 */
export interface ExecutionLog {
  id: string;
  agent_name: string;
  display_name: string;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  status: "running" | "success" | "failed" | "incomplete";
  trigger_type: "scheduled" | "manual";
  triggered_by: string;
  summary: Record<string, unknown> | null;
  error_message: string | null;
  items_processed: number;
  has_log_output: boolean;
}

/**
 * Execution log detail with full log output.
 */
export interface ExecutionLogDetail extends ExecutionLog {
  log_output: string | null;
  error_traceback: string | null;
}

/**
 * Dashboard overview summary.
 */
export interface DashboardSummary {
  running: ExecutionLog[];
  recent_completions: ExecutionLog[];
  recent_failures: ExecutionLog[];
  total_executions_24h: number;
  success_rate_24h: number;
  avg_duration_24h: number | null;
}

/**
 * Filters for execution list.
 */
export interface ExecutionFilters {
  agent_name?: string;
  status?: string;
  trigger_type?: string;
  date_from?: string;
  date_to?: string;
}

/**
 * Paginated execution list API response.
 */
export interface ExecutionListResponse {
  executions: ExecutionLog[];
  total_count: number;
  has_more: boolean;
}
