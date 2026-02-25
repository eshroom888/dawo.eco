/**
 * EvidenceCard component.
 *
 * Story 6-9, Task 8.4: List item card showing screenshot thumbnail,
 * competitor name, claim excerpt, severity badge, and metadata.
 */

import {
  Evidence,
  SEVERITY_COLORS,
  VIOLATION_TYPE_LABELS,
  SOURCE_TYPE_LABELS,
} from "@/types/evidence";

interface EvidenceCardProps {
  evidence: Evidence;
  onClick: (evidence: Evidence) => void;
  onCompetitorClick?: (name: string) => void;
  onSelect?: (evidence: Evidence) => void;
  isSelected?: boolean;
}

export function EvidenceCard({ evidence, onClick, onCompetitorClick, onSelect, isSelected }: EvidenceCardProps) {
  const severityClass = SEVERITY_COLORS[evidence.severity] || "bg-gray-100 text-gray-800";
  const violationLabel = VIOLATION_TYPE_LABELS[evidence.violation_type] || evidence.violation_type;
  const sourceLabel = SOURCE_TYPE_LABELS[evidence.source_type] || evidence.source_type;

  return (
    <div
      className="bg-white rounded-lg shadow hover:shadow-md transition-shadow cursor-pointer p-4"
      onClick={() => onClick(evidence)}
    >
      <div className="flex gap-3">
        {/* Selection checkbox */}
        {onSelect && (
          <div className="flex-shrink-0 flex items-center">
            <input
              type="checkbox"
              checked={isSelected ?? false}
              onChange={(e) => {
                e.stopPropagation();
                onSelect(evidence);
              }}
              onClick={(e) => e.stopPropagation()}
              className="h-4 w-4 text-blue-600 rounded border-gray-300"
            />
          </div>
        )}

        {/* Thumbnail */}
        <div className="flex-shrink-0">
          <img
            src={`/api/evidence/${evidence.id}/screenshot`}
            alt="Evidence screenshot"
            className="w-16 h-16 object-cover rounded border"
            loading="lazy"
          />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <button
              className="text-sm font-semibold text-blue-600 hover:underline"
              onClick={(e) => {
                e.stopPropagation();
                onCompetitorClick?.(evidence.competitor_name);
              }}
            >
              {evidence.competitor_name}
            </button>
            <span className={`text-xs px-2 py-0.5 rounded-full ${severityClass}`}>
              {evidence.severity}
            </span>
          </div>

          <p className="text-sm text-gray-700 truncate">{evidence.claim_text}</p>

          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span>{violationLabel}</span>
            <span>{sourceLabel}</span>
            <span>{new Date(evidence.captured_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default EvidenceCard;
