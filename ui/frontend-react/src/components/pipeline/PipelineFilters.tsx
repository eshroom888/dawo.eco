/**
 * PipelineFilters component.
 *
 * Story 5-5, Task 8.5: Search input, status filter dropdown, and sort dropdown.
 */

import React, { useCallback } from "react";
import { Button } from "@/components/ui/button";
import { LeadStatus, STATUS_CONFIGS } from "@/types/pipeline";

export interface PipelineFiltersProps {
  status: string | null;
  search: string;
  sort: string;
  onStatusChange: (status: string | null) => void;
  onSearchChange: (search: string) => void;
  onSortChange: (sort: string) => void;
  className?: string;
}

const SORT_OPTIONS = [
  { value: "score", label: "Score" },
  { value: "created_at", label: "Newest" },
  { value: "last_contacted_at", label: "Last Contacted" },
  { value: "company", label: "Company" },
];

/**
 * Pipeline filter controls.
 */
export function PipelineFilters({
  status,
  search,
  sort,
  onStatusChange,
  onSearchChange,
  onSortChange,
  className = "",
}: PipelineFiltersProps): React.ReactElement {
  const handleSearchInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onSearchChange(e.target.value);
    },
    [onSearchChange]
  );

  const handleStatusSelect = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onStatusChange(e.target.value || null);
    },
    [onStatusChange]
  );

  const handleSortSelect = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onSortChange(e.target.value);
    },
    [onSortChange]
  );

  return (
    <div className={`flex flex-wrap items-center gap-3 ${className}`}>
      {/* Search */}
      <input
        type="text"
        placeholder="Search leads..."
        value={search}
        onChange={handleSearchInput}
        className="px-3 py-1.5 border rounded-md text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Search leads"
      />

      {/* Status filter */}
      <select
        value={status ?? ""}
        onChange={handleStatusSelect}
        className="px-3 py-1.5 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Filter by status"
      >
        <option value="">All Statuses</option>
        {Object.values(LeadStatus).map((s) => (
          <option key={s} value={s}>
            {STATUS_CONFIGS[s].label}
          </option>
        ))}
      </select>

      {/* Sort */}
      <select
        value={sort}
        onChange={handleSortSelect}
        className="px-3 py-1.5 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Sort by"
      >
        {SORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            Sort: {opt.label}
          </option>
        ))}
      </select>

      {/* Clear filters */}
      {(status || search) && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            onStatusChange(null);
            onSearchChange("");
          }}
        >
          Clear
        </Button>
      )}
    </div>
  );
}

export default PipelineFilters;
