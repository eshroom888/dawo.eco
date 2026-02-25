/**
 * EvidenceDetailDrawer component.
 *
 * Story 6-9, Task 8.5: Slide-out drawer showing full evidence detail
 * including screenshot, all fields, audit log, and download button.
 */

import { useEvidenceDetail } from "@/hooks/useEvidence";
import { SEVERITY_COLORS } from "@/types/evidence";

interface EvidenceDetailDrawerProps {
  evidenceId: string | null;
  onClose: () => void;
  onDownload: (id: string) => Promise<void>;
}

export function EvidenceDetailDrawer({
  evidenceId,
  onClose,
  onDownload,
}: EvidenceDetailDrawerProps) {
  const { detail, isLoading } = useEvidenceDetail(evidenceId);

  if (!evidenceId) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* Drawer */}
      <div className="relative w-full max-w-lg bg-white shadow-xl overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Evidence Detail</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">
              &times;
            </button>
          </div>

          {isLoading || !detail ? (
            <div className="space-y-4 animate-pulse">
              <div className="h-48 bg-gray-200 rounded" />
              <div className="h-4 bg-gray-200 rounded w-3/4" />
              <div className="h-4 bg-gray-200 rounded w-1/2" />
            </div>
          ) : (
            <>
              {/* Screenshot */}
              <img
                src={`/api/evidence/${detail.id}/screenshot`}
                alt="Evidence screenshot"
                className="w-full rounded border mb-4 cursor-zoom-in"
              />

              {/* Fields */}
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Competitor</span>
                  <span className="font-medium">{detail.competitor_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Severity</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs ${SEVERITY_COLORS[detail.severity] || ""}`}>
                    {detail.severity}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Violation Type</span>
                  <span>{detail.violation_type}</span>
                </div>
                <div>
                  <span className="text-gray-500 block mb-1">Claim Text</span>
                  <p className="text-gray-800 bg-gray-50 p-2 rounded">{detail.claim_text}</p>
                </div>
                {detail.regulation_violated && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Regulation</span>
                    <span>{detail.regulation_violated}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-500">Source</span>
                  <a href={detail.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline truncate max-w-[200px]">
                    {detail.source_type}
                  </a>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Confidence</span>
                  <span>{(detail.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Captured</span>
                  <span>{new Date(detail.captured_at).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Integrity Hash</span>
                  <span className="font-mono text-xs truncate max-w-[200px]">{detail.screenshot_hash}</span>
                </div>
              </div>

              {/* Download button */}
              <button
                onClick={() => onDownload(detail.id)}
                className="mt-4 w-full bg-blue-600 text-white rounded-md py-2 hover:bg-blue-700 transition-colors"
              >
                Download Evidence Package
              </button>

              {/* Audit Log */}
              {detail.audit_logs.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-sm font-semibold mb-2">Audit Log</h3>
                  <div className="space-y-2">
                    {detail.audit_logs.map((log) => (
                      <div key={log.id} className="text-xs text-gray-600 flex justify-between border-b pb-1">
                        <span>{log.action} by {log.actor}</span>
                        <span>{new Date(log.created_at).toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default EvidenceDetailDrawer;
