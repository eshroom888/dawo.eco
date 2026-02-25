/**
 * CompetitorProfile component.
 *
 * Story 6-9, Task 8.6: All violations by competitor, violation count trend
 * chart (CSS bar chart), and timeline of violations.
 */

import { useCompetitorTimeline } from "@/hooks/useEvidence";
import {
  Evidence,
  SEVERITY_COLORS,
  VIOLATION_TYPE_LABELS,
} from "@/types/evidence";

interface CompetitorProfileProps {
  competitorName: string;
  violations: Evidence[];
  onClose: () => void;
  onEvidenceClick: (evidence: Evidence) => void;
}

export function CompetitorProfile({
  competitorName,
  violations,
  onClose,
  onEvidenceClick,
}: CompetitorProfileProps) {
  const { timeline, isLoading: timelineLoading } = useCompetitorTimeline(competitorName);

  const maxCount = Math.max(...timeline.map((t) => t.count), 1);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">{competitorName}</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-sm">
          Back to all
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="text-center p-3 bg-gray-50 rounded">
          <p className="text-2xl font-bold">{violations.length}</p>
          <p className="text-xs text-gray-500">Total Violations</p>
        </div>
        <div className="text-center p-3 bg-red-50 rounded">
          <p className="text-2xl font-bold text-red-700">
            {violations.filter((v) => v.severity === "high").length}
          </p>
          <p className="text-xs text-gray-500">High Severity</p>
        </div>
        <div className="text-center p-3 bg-yellow-50 rounded">
          <p className="text-2xl font-bold text-yellow-700">
            {violations.filter((v) => v.severity === "medium").length}
          </p>
          <p className="text-xs text-gray-500">Medium Severity</p>
        </div>
      </div>

      {/* Trend Chart (CSS bar chart) */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold mb-2">Violation Trend</h3>
        {timelineLoading ? (
          <div className="h-32 bg-gray-100 rounded animate-pulse" />
        ) : timeline.length === 0 ? (
          <p className="text-sm text-gray-500">No trend data available</p>
        ) : (
          <div className="flex items-end gap-1 h-32">
            {timeline.map((entry) => (
              <div key={entry.month} className="flex-1 flex flex-col items-center">
                <span className="text-xs text-gray-500 mb-1">{entry.count}</span>
                <div
                  className="w-full bg-blue-500 rounded-t"
                  style={{ height: `${(entry.count / maxCount) * 100}%`, minHeight: "4px" }}
                />
                <span className="text-xs text-gray-400 mt-1 truncate w-full text-center">
                  {entry.month.slice(5)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Violations Timeline */}
      <div>
        <h3 className="text-sm font-semibold mb-2">Violations</h3>
        {violations.length === 0 ? (
          <p className="text-sm text-gray-500">No violations found</p>
        ) : (
          <div className="space-y-2">
            {violations.map((v) => (
              <div
                key={v.id}
                className="flex items-center gap-3 p-2 rounded hover:bg-gray-50 cursor-pointer"
                onClick={() => onEvidenceClick(v)}
              >
                <span className={`text-xs px-2 py-0.5 rounded-full ${SEVERITY_COLORS[v.severity] || ""}`}>
                  {v.severity}
                </span>
                <span className="text-sm flex-1 truncate">{v.claim_text}</span>
                <span className="text-xs text-gray-400">
                  {VIOLATION_TYPE_LABELS[v.violation_type] || v.violation_type}
                </span>
                <span className="text-xs text-gray-400">
                  {new Date(v.captured_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default CompetitorProfile;
