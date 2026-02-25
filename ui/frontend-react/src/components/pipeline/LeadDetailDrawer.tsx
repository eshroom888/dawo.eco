/**
 * LeadDetailDrawer component.
 *
 * Story 5-5, Task 8.6: Slide-out drawer with full lead info,
 * activity timeline, status transition buttons, and note input.
 */

import React, { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { LeadDetail, STATUS_CONFIGS, LeadStatus } from "@/types/pipeline";
import { useLeadDetail } from "@/hooks/useLeadDetail";
import { StatusTransitionButton } from "./StatusTransitionButton";
import { LeadHistoryTimeline } from "./LeadHistoryTimeline";
import { FollowUpBadge } from "./FollowUpBadge";

export interface LeadDetailDrawerProps {
  leadId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onStatusChange: (leadId: string, newStatus: string, reason?: string) => Promise<void>;
  onAddNote: (leadId: string, note: string) => Promise<void>;
  className?: string;
}

/**
 * Slide-out drawer displaying full lead detail.
 */
export function LeadDetailDrawer({
  leadId,
  isOpen,
  onClose,
  onStatusChange,
  onAddNote,
  className,
}: LeadDetailDrawerProps): React.ReactElement | null {
  const { lead, isLoading, error, refresh } = useLeadDetail(isOpen ? leadId : null);
  const [noteText, setNoteText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleStatusTransition = useCallback(
    async (newStatus: string, reason?: string) => {
      if (!leadId) return;
      await onStatusChange(leadId, newStatus, reason);
      refresh();
    },
    [leadId, onStatusChange, refresh]
  );

  const handleAddNote = useCallback(async () => {
    if (!leadId || !noteText.trim()) return;
    setIsSubmitting(true);
    try {
      await onAddNote(leadId, noteText.trim());
      setNoteText("");
      refresh();
    } finally {
      setIsSubmitting(false);
    }
  }, [leadId, noteText, onAddNote, refresh]);

  if (!isOpen) return null;

  const statusConfig = lead
    ? STATUS_CONFIGS[lead.status as LeadStatus] ?? { label: lead.status, color: "text-gray-700", bgColor: "bg-gray-100" }
    : null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={cn(
          "fixed right-0 top-0 bottom-0 w-full max-w-lg bg-white shadow-xl z-50 overflow-y-auto",
          className
        )}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-4 py-3 flex items-center justify-between z-10">
          <h2 className="text-lg font-semibold">Lead Detail</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            X
          </Button>
        </div>

        <div className="p-4 space-y-4">
          {isLoading && (
            <div className="space-y-3">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-64" />
              <Skeleton className="h-20 w-full" />
            </div>
          )}

          {error && (
            <Card className="border-red-200">
              <CardContent className="py-4">
                <p className="text-red-600 text-sm">{error.message}</p>
                <Button variant="outline" size="sm" onClick={refresh} className="mt-2">
                  Retry
                </Button>
              </CardContent>
            </Card>
          )}

          {lead && (
            <>
              {/* Lead info */}
              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-semibold">
                        {lead.first_name} {lead.last_name}
                      </h3>
                      <p className="text-sm text-gray-500">{lead.job_title}</p>
                      <p className="text-sm font-medium">{lead.company}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-2xl font-bold">{lead.score.toFixed(0)}</span>
                      <p className="text-xs text-gray-400">Score</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 mt-3">
                    {statusConfig && (
                      <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium", statusConfig.bgColor, statusConfig.color)}>
                        {statusConfig.label}
                      </span>
                    )}
                    {lead.needs_followup && lead.days_since_contact != null && (
                      <FollowUpBadge daysSinceContact={lead.days_since_contact} />
                    )}
                  </div>

                  {/* Contact details */}
                  <div className="mt-3 space-y-1 text-sm text-gray-600">
                    <p>{lead.email}</p>
                    {lead.phone && <p>{lead.phone}</p>}
                    {lead.linkedin_url && (
                      <a
                        href={lead.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        LinkedIn
                      </a>
                    )}
                    {lead.website_url && (
                      <a
                        href={lead.website_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline ml-3"
                      >
                        Website
                      </a>
                    )}
                  </div>

                  {/* Additional info */}
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-500">
                    {lead.country && <span>Country: {lead.country}</span>}
                    {lead.industry && <span>Industry: {lead.industry}</span>}
                    {lead.company_size && <span>Size: {lead.company_size}</span>}
                    {lead.source && <span>Source: {lead.source}</span>}
                    <span>Contacted: {lead.contact_count}x</span>
                  </div>

                  {/* Tags */}
                  {lead.tags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {lead.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Status transition */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Update Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <StatusTransitionButton
                    currentStatus={lead.status}
                    onTransition={handleStatusTransition}
                  />
                </CardContent>
              </Card>

              {/* Add note */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Add Note</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={noteText}
                      onChange={(e) => setNoteText(e.target.value)}
                      placeholder="Type a note..."
                      className="flex-1 px-3 py-1.5 border rounded-md text-sm"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && noteText.trim()) {
                          handleAddNote();
                        }
                      }}
                    />
                    <Button
                      size="sm"
                      onClick={handleAddNote}
                      disabled={!noteText.trim() || isSubmitting}
                    >
                      {isSubmitting ? "..." : "Add"}
                    </Button>
                  </div>
                  {lead.notes && (
                    <p className="mt-2 text-xs text-gray-400">{lead.notes}</p>
                  )}
                </CardContent>
              </Card>

              {/* Activity timeline */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Activity History</CardTitle>
                </CardHeader>
                <CardContent>
                  <LeadHistoryTimeline entries={lead.activities} />
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default LeadDetailDrawer;
