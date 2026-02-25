/**
 * TypeScript types for Lead Pipeline Dashboard.
 *
 * Story 5-5: Mirrors backend Pydantic schemas for type-safe API communication.
 */

/**
 * Lead status enum matching backend LeadStatus.
 */
export enum LeadStatus {
  NEW = "new",
  RESEARCHING = "researching",
  QUALIFIED = "qualified",
  OUTREACH_PENDING = "outreach_pending",
  CONTACTED = "contacted",
  REPLIED = "replied",
  MEETING_SCHEDULED = "meeting_scheduled",
  NEGOTIATING = "negotiating",
  CONVERTED = "converted",
  LOST = "lost",
  NURTURE = "nurture",
}

/**
 * Status display configuration for UI.
 */
export interface StatusConfig {
  label: string;
  color: string;
  bgColor: string;
}

/**
 * Status display configurations.
 */
export const STATUS_CONFIGS: Record<LeadStatus, StatusConfig> = {
  [LeadStatus.NEW]: { label: "New", color: "text-blue-700", bgColor: "bg-blue-100" },
  [LeadStatus.RESEARCHING]: { label: "Researching", color: "text-indigo-700", bgColor: "bg-indigo-100" },
  [LeadStatus.QUALIFIED]: { label: "Qualified", color: "text-cyan-700", bgColor: "bg-cyan-100" },
  [LeadStatus.OUTREACH_PENDING]: { label: "Outreach Pending", color: "text-amber-700", bgColor: "bg-amber-100" },
  [LeadStatus.CONTACTED]: { label: "Contacted", color: "text-orange-700", bgColor: "bg-orange-100" },
  [LeadStatus.REPLIED]: { label: "Replied", color: "text-teal-700", bgColor: "bg-teal-100" },
  [LeadStatus.MEETING_SCHEDULED]: { label: "Meeting", color: "text-purple-700", bgColor: "bg-purple-100" },
  [LeadStatus.NEGOTIATING]: { label: "Negotiating", color: "text-pink-700", bgColor: "bg-pink-100" },
  [LeadStatus.CONVERTED]: { label: "Converted", color: "text-green-700", bgColor: "bg-green-100" },
  [LeadStatus.LOST]: { label: "Lost", color: "text-red-700", bgColor: "bg-red-100" },
  [LeadStatus.NURTURE]: { label: "Nurture", color: "text-yellow-700", bgColor: "bg-yellow-100" },
};

/**
 * Pipeline lead summary for list views.
 */
export interface PipelineLead {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  company: string;
  job_title: string | null;
  status: string;
  source: string;
  score: number;
  last_contacted_at: string | null;
  days_since_contact: number | null;
  needs_followup: boolean;
  contact_count: number;
  created_at: string;
}

/**
 * Full lead detail with all fields.
 */
export interface LeadDetail extends PipelineLead {
  linkedin_url: string | null;
  website_url: string | null;
  phone: string | null;
  country: string | null;
  industry: string | null;
  company_size: string | null;
  enrichment_data: Record<string, unknown> | null;
  outreach_data: Record<string, unknown> | null;
  tags: string[];
  notes: string | null;
  assigned_to: string | null;
  next_followup_at: string | null;
  converted_at: string | null;
  lost_reason: string | null;
  updated_at: string;
  activities: LeadHistoryEntry[];
}

/**
 * Pipeline summary for dashboard header.
 */
export interface PipelineSummary {
  total_leads: number;
  status_counts: Record<string, number>;
  conversion_rate: number;
  avg_days_in_pipeline: number;
  followup_count: number;
}

/**
 * Paginated lead list response.
 */
export interface PipelineLeadListResponse {
  leads: PipelineLead[];
  total_count: number;
  has_more: boolean;
  next_cursor: string | null;
}

/**
 * Lead activity history entry.
 */
export interface LeadHistoryEntry {
  id: string;
  lead_id: string;
  activity_type: string;
  description: string;
  timestamp: string;
  actor: string;
  metadata: Record<string, unknown> | null;
}

/**
 * Lead history response.
 */
export interface LeadHistoryResponse {
  entries: LeadHistoryEntry[];
}

/**
 * Status update request.
 */
export interface StatusUpdateRequest {
  new_status: string;
  reason?: string | null;
  note?: string | null;
}

/**
 * Status update response.
 */
export interface StatusUpdateResponse {
  success: boolean;
  lead: PipelineLead;
  message: string;
}

/**
 * Pipeline conversion metrics.
 */
export interface PipelineMetrics {
  conversion_rate: number;
  total_leads: number;
  converted_count: number;
  avg_time_per_stage: Record<string, number>;
  weekly_trend: WeeklyTrend[];
}

/**
 * Weekly trend data point.
 */
export interface WeeklyTrend {
  week: string;
  new_leads: number;
  converted: number;
}

/**
 * Follow-up candidate (from /followups endpoint).
 */
export interface FollowUpCandidate extends PipelineLead {
  needs_followup: true;
  days_since_contact: number;
}

/**
 * Add note request.
 */
export interface AddNoteRequest {
  note: string;
}

/**
 * Valid manual transitions mapping.
 * Maps current status to allowed next statuses.
 */
export const VALID_TRANSITIONS: Record<string, string[]> = {
  [LeadStatus.NEW]: [LeadStatus.RESEARCHING, LeadStatus.LOST],
  [LeadStatus.RESEARCHING]: [LeadStatus.QUALIFIED, LeadStatus.LOST],
  [LeadStatus.QUALIFIED]: [LeadStatus.OUTREACH_PENDING, LeadStatus.LOST],
  [LeadStatus.OUTREACH_PENDING]: [LeadStatus.CONTACTED, LeadStatus.LOST],
  [LeadStatus.CONTACTED]: [LeadStatus.REPLIED, LeadStatus.LOST, LeadStatus.NURTURE],
  [LeadStatus.REPLIED]: [LeadStatus.MEETING_SCHEDULED, LeadStatus.LOST, LeadStatus.NURTURE],
  [LeadStatus.MEETING_SCHEDULED]: [LeadStatus.NEGOTIATING, LeadStatus.LOST, LeadStatus.NURTURE],
  [LeadStatus.NEGOTIATING]: [LeadStatus.CONVERTED, LeadStatus.LOST, LeadStatus.NURTURE],
  [LeadStatus.CONVERTED]: [],
  [LeadStatus.LOST]: [LeadStatus.NURTURE],
  [LeadStatus.NURTURE]: [LeadStatus.CONTACTED],
};
