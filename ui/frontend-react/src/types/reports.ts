/**
 * TypeScript types for Violation Reports API.
 *
 * Story 6-10: Mirrors backend Pydantic schemas for type-safe API communication.
 */

/**
 * Request body for generating a violation report.
 */
export interface ReportGenerateRequest {
  evidence_ids?: string[];
  competitor_name?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  template_type?: string;
  report_title?: string | null;
}

/**
 * Response after report generation.
 */
export interface ReportGenerateResponse {
  report_id: string;
  filename: string;
  evidence_count: number;
  page_count: number;
  generated_at: string;
  sha256_hash: string;
  download_url: string;
}

/**
 * Report listing entry.
 */
export interface ReportListItem {
  report_id: string;
  filename: string;
  evidence_count: number;
  competitor_name: string | null;
  template_type: string;
  generated_at: string;
  sha256_hash: string;
  page_count: number;
  file_size_bytes: number;
}

/**
 * Paginated report list response.
 */
export interface ReportListResponse {
  items: ReportListItem[];
  total_count: number;
  has_more: boolean;
}

/**
 * Display labels for report template types.
 */
export const TEMPLATE_LABELS: Record<string, string> = {
  standard: "Standard Report",
  mattilsynet: "Mattilsynet (Norwegian)",
  eu_authority: "EU Authority",
  legal: "Legal Counsel",
};
