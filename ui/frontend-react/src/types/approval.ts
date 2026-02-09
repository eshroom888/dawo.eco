/**
 * TypeScript types for Approval Queue.
 *
 * Mirrors the backend Pydantic schemas for type-safe API communication.
 */

/**
 * Source-based priority for approval queue ordering.
 * Lower values indicate higher priority (more urgent).
 */
export enum SourcePriority {
  TRENDING = 1,
  SCHEDULED = 2,
  EVERGREEN = 3,
  RESEARCH = 4,
}

/**
 * Content compliance status.
 */
export enum ComplianceStatus {
  COMPLIANT = "COMPLIANT",
  WARNING = "WARNING",
  REJECTED = "REJECTED",
}

/**
 * Quality score color coding.
 */
export type QualityColor = "green" | "yellow" | "red";

/**
 * Calculate quality color from score.
 *
 * @param score - Quality score (0-10)
 * @returns Color based on score threshold
 */
export function getQualityColor(score: number): QualityColor {
  if (score >= 8) return "green";
  if (score >= 5) return "yellow";
  return "red";
}

/**
 * Individual compliance check result.
 */
export interface ComplianceCheck {
  phrase: string;
  status: "prohibited" | "borderline" | "permitted";
  explanation: string;
  regulation_reference?: string;
}

/**
 * Quality score breakdown by factor.
 */
export interface QualityBreakdown {
  compliance_score: number;
  brand_voice_score: number;
  visual_quality_score: number;
  platform_optimization_score: number;
  engagement_prediction_score: number;
  authenticity_score: number;
}

/**
 * Quality breakdown factor with weight information.
 */
export interface QualityFactor {
  key: keyof QualityBreakdown;
  label: string;
  weight: number;
  score: number;
}

/**
 * Quality factors with their weights.
 */
export const QUALITY_FACTORS: Array<{ key: keyof QualityBreakdown; label: string; weight: number }> = [
  { key: "compliance_score", label: "Compliance", weight: 0.25 },
  { key: "brand_voice_score", label: "Brand Voice", weight: 0.20 },
  { key: "visual_quality_score", label: "Visual Quality", weight: 0.15 },
  { key: "platform_optimization_score", label: "Platform", weight: 0.15 },
  { key: "engagement_prediction_score", label: "Engagement", weight: 0.15 },
  { key: "authenticity_score", label: "Authenticity", weight: 0.10 },
];

/**
 * Approval queue item from API.
 */
export interface ApprovalQueueItem {
  id: string;
  thumbnail_url: string;
  caption_excerpt: string;
  full_caption: string;
  quality_score: number;
  quality_color: QualityColor;
  compliance_status: ComplianceStatus;
  would_auto_publish: boolean;
  suggested_publish_time: string | null;
  source_type: string;
  source_priority: SourcePriority;
  hashtags: string[];
  compliance_details?: ComplianceCheck[];
  quality_breakdown?: QualityBreakdown;
  created_at: string;
  // Story 4-2: Edit/revert support
  original_caption?: string | null;
  rewrite_suggestions?: RewriteSuggestion[];
  // Approval/rejection tracking
  status?: ApprovalStatus;
  approved_at?: string | null;
  approved_by?: string | null;
  rejection_reason?: RejectReason | null;
  rejection_text?: string | null;
}

/**
 * Paginated response from approval queue API.
 */
export interface ApprovalQueueResponse {
  items: ApprovalQueueItem[];
  total_count: number;
  next_cursor: string | null;
  has_more: boolean;
}

/**
 * Source type display configuration.
 */
export interface SourceTypeConfig {
  label: string;
  icon: string;
  color: string;
}

/**
 * Source type configurations.
 */
export const SOURCE_TYPES: Record<string, SourceTypeConfig> = {
  instagram_post: {
    label: "Instagram Post",
    icon: "instagram",
    color: "bg-pink-100 text-pink-800",
  },
  b2b_email: {
    label: "B2B Email",
    icon: "mail",
    color: "bg-blue-100 text-blue-800",
  },
  story: {
    label: "Story",
    icon: "clock",
    color: "bg-purple-100 text-purple-800",
  },
  reel: {
    label: "Reel",
    icon: "video",
    color: "bg-orange-100 text-orange-800",
  },
};

/**
 * Approval item status for workflow states.
 */
export enum ApprovalStatus {
  PENDING = "pending",
  APPROVED = "approved",
  REJECTED = "rejected",
  SCHEDULED = "scheduled",
  PUBLISHED = "published",
  PUBLISH_FAILED = "publish_failed",
}

/**
 * Rejection reason enum for predefined options.
 */
export enum RejectReason {
  COMPLIANCE_ISSUE = "compliance_issue",
  BRAND_VOICE_MISMATCH = "brand_voice_mismatch",
  LOW_QUALITY = "low_quality",
  IRRELEVANT_CONTENT = "irrelevant_content",
  DUPLICATE_CONTENT = "duplicate_content",
  OTHER = "other",
}

/**
 * Rejection reason labels for UI display.
 */
export const REJECT_REASON_LABELS: Record<RejectReason, string> = {
  [RejectReason.COMPLIANCE_ISSUE]: "Contains prohibited claims",
  [RejectReason.BRAND_VOICE_MISMATCH]: "Doesn't match DAWO tone",
  [RejectReason.LOW_QUALITY]: "Quality score too low",
  [RejectReason.IRRELEVANT_CONTENT]: "Topic not suitable",
  [RejectReason.DUPLICATE_CONTENT]: "Similar post already exists",
  [RejectReason.OTHER]: "Other reason",
};

/**
 * Schema for approve action request.
 */
export interface ApproveActionRequest {
  scheduled_publish_time?: string | null;
}

/**
 * Schema for reject action request.
 */
export interface RejectActionRequest {
  reason: RejectReason;
  reason_text?: string | null;
}

/**
 * Schema for edit action request.
 */
export interface EditActionRequest {
  caption: string;
  hashtags?: string[] | null;
}

/**
 * Revalidation result from compliance/quality checks.
 */
export interface RevalidationResult {
  compliance_status: ComplianceStatus;
  compliance_details?: ComplianceCheck[] | null;
  quality_score: number;
  quality_breakdown?: QualityBreakdown | null;
  rewrite_suggestions?: RewriteSuggestion[] | null;
}

/**
 * AI rewrite suggestion.
 */
export interface RewriteSuggestion {
  id: string;
  original_text: string;
  suggested_text: string;
  reason: string;
  type: "compliance" | "brand_voice" | "quality";
}

/**
 * Standard response for approval actions.
 */
export interface ApprovalActionResponse {
  success: boolean;
  message: string;
  item_id: string;
  new_status: ApprovalStatus;
  revalidation?: RevalidationResult | null;
}

/**
 * Edit history entry.
 */
export interface EditHistoryEntry {
  id: string;
  previous_caption: string;
  new_caption: string;
  edited_at: string;
  editor: string;
}

/**
 * Action type for approval actions hook.
 */
export type ApprovalActionType = "approve" | "reject" | "edit" | "revalidate";
