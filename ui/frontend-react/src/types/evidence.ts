/**
 * TypeScript types for Evidence Search & Filter UI.
 *
 * Story 6-9: Mirrors backend Pydantic schemas for type-safe API communication.
 */

/**
 * Evidence list item (compact for grid view).
 */
export interface Evidence {
  id: string;
  competitor_name: string;
  violation_type: string;
  severity: string;
  claim_text: string;
  claim_category: string;
  source_type: string;
  source_url: string;
  captured_at: string;
  screenshot_path: string;
  screenshot_hash: string;
}

/**
 * Audit log entry for evidence operations.
 */
export interface AuditLogEntry {
  id: string;
  action: string;
  actor: string;
  details: Record<string, unknown> | null;
  hash_verified: boolean | null;
  created_at: string;
}

/**
 * Full evidence detail with relations.
 */
export interface EvidenceDetail {
  id: string;
  competitor_name: string;
  violation_type: string;
  severity: string;
  claim_text: string;
  claim_category: string;
  source_type: string;
  source_url: string;
  captured_at: string;
  screenshot_path: string;
  screenshot_hash: string;
  screenshot_size_bytes: number;
  regulation_violated: string | null;
  detection_reasoning: string | null;
  confidence: number;
  evidence_metadata: Record<string, unknown> | null;
  created_at: string;
  audit_logs: AuditLogEntry[];
}

/**
 * Paginated evidence list response.
 */
export interface EvidenceListResponse {
  items: Evidence[];
  total_count: number;
  has_more: boolean;
}

/**
 * Evidence summary statistics.
 */
export interface EvidenceSummary {
  total_evidence: number;
  by_severity: Record<string, number>;
  by_competitor: Record<string, number>;
  by_violation_type: Record<string, number>;
}

/**
 * Filter parameters for evidence search.
 */
export interface EvidenceFilters {
  competitor?: string;
  violationType?: string;
  severity?: string;
  dateFrom?: string;
  dateTo?: string;
  keywords?: string;
  sourceType?: string;
}

/**
 * Monthly violation count for competitor trend chart.
 */
export interface CompetitorTimelineEntry {
  month: string;
  count: number;
}

/**
 * Severity level display colors (Tailwind classes).
 */
export const SEVERITY_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
};

/**
 * Violation type display labels.
 */
export const VIOLATION_TYPE_LABELS: Record<string, string> = {
  unauthorized_treatment_claim: "Treatment Claim",
  unauthorized_prevention_claim: "Prevention Claim",
  unauthorized_enhancement_claim: "Enhancement Claim",
  unauthorized_wellness_claim: "Wellness Claim",
  violation: "Violation",
  suspect: "Suspect",
};

/**
 * Source type display labels.
 */
export const SOURCE_TYPE_LABELS: Record<string, string> = {
  instagram_post: "Instagram",
  website_page: "Website",
};
