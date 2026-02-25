/**
 * EvidenceSummaryCards component.
 *
 * Story 6-9, Task 8.2: Dashboard summary cards showing total evidence
 * count and severity breakdown with color coding.
 */

import { EvidenceSummary, SEVERITY_COLORS } from "@/types/evidence";

interface EvidenceSummaryCardsProps {
  summary: EvidenceSummary | null;
}

export function EvidenceSummaryCards({ summary }: EvidenceSummaryCardsProps) {
  if (!summary) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 animate-pulse">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-200 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="bg-white rounded-lg shadow p-4">
        <p className="text-sm text-gray-500">Total Evidence</p>
        <p className="text-2xl font-bold">{summary.total_evidence}</p>
      </div>
      {["high", "medium", "low"].map((severity) => (
        <div key={severity} className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500 capitalize">{severity} Severity</p>
          <p className="text-2xl font-bold">
            <span className={SEVERITY_COLORS[severity]?.split(" ")[1] || ""}>
              {summary.by_severity[severity] || 0}
            </span>
          </p>
        </div>
      ))}
    </div>
  );
}

export default EvidenceSummaryCards;
