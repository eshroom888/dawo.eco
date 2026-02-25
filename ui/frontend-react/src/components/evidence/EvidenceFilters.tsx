/**
 * EvidenceFilters component.
 *
 * Story 6-9, Task 8.3: Filter controls for evidence search including
 * competitor dropdown, violation type, severity, date range, and keywords.
 */

import { EvidenceFilters as EvidenceFiltersType } from "@/types/evidence";

interface EvidenceFiltersProps {
  filters: EvidenceFiltersType;
  competitors: string[];
  onFilterChange: (filters: Partial<EvidenceFiltersType>) => void;
}

export function EvidenceFilters({
  filters,
  competitors,
  onFilterChange,
}: EvidenceFiltersProps) {
  const clearFilters = () => {
    onFilterChange({
      competitor: undefined,
      violationType: undefined,
      severity: undefined,
      dateFrom: undefined,
      dateTo: undefined,
      keywords: undefined,
      sourceType: undefined,
    });
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {/* Competitor dropdown */}
        <select
          value={filters.competitor || ""}
          onChange={(e) => onFilterChange({ competitor: e.target.value || undefined })}
          className="border rounded-md px-3 py-2 text-sm"
        >
          <option value="">All Competitors</option>
          {competitors.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>

        {/* Violation type */}
        <select
          value={filters.violationType || ""}
          onChange={(e) => onFilterChange({ violationType: e.target.value || undefined })}
          className="border rounded-md px-3 py-2 text-sm"
        >
          <option value="">All Violation Types</option>
          <option value="unauthorized_treatment_claim">Treatment Claim</option>
          <option value="unauthorized_prevention_claim">Prevention Claim</option>
          <option value="unauthorized_enhancement_claim">Enhancement Claim</option>
          <option value="unauthorized_wellness_claim">Wellness Claim</option>
        </select>

        {/* Severity */}
        <select
          value={filters.severity || ""}
          onChange={(e) => onFilterChange({ severity: e.target.value || undefined })}
          className="border rounded-md px-3 py-2 text-sm"
        >
          <option value="">All Severities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        {/* Keywords */}
        <input
          type="text"
          placeholder="Search claims..."
          value={filters.keywords || ""}
          onChange={(e) => onFilterChange({ keywords: e.target.value || undefined })}
          className="border rounded-md px-3 py-2 text-sm"
        />

        {/* Date from */}
        <input
          type="date"
          value={filters.dateFrom || ""}
          onChange={(e) => onFilterChange({ dateFrom: e.target.value || undefined })}
          className="border rounded-md px-3 py-2 text-sm"
        />

        {/* Date to */}
        <input
          type="date"
          value={filters.dateTo || ""}
          onChange={(e) => onFilterChange({ dateTo: e.target.value || undefined })}
          className="border rounded-md px-3 py-2 text-sm"
        />

        {/* Source type */}
        <select
          value={filters.sourceType || ""}
          onChange={(e) => onFilterChange({ sourceType: e.target.value || undefined })}
          className="border rounded-md px-3 py-2 text-sm"
        >
          <option value="">All Sources</option>
          <option value="instagram_post">Instagram</option>
          <option value="website_page">Website</option>
        </select>

        {/* Clear button */}
        <button
          onClick={clearFilters}
          className="border rounded-md px-3 py-2 text-sm text-gray-600 hover:bg-gray-100"
        >
          Clear Filters
        </button>
      </div>
    </div>
  );
}

export default EvidenceFilters;
