/**
 * ApprovalDetailModal component.
 *
 * Modal dialog for viewing full details of an approval item.
 * Displays full image, caption, hashtags, compliance details, and quality breakdown.
 *
 * Features:
 * - Full-size image preview
 * - Complete caption with hashtags
 * - Compliance check details with expandable explanations
 * - Quality score breakdown by factor
 * - Keyboard navigation (Escape, arrows)
 * - Approve/Reject/Edit action buttons
 * - Toast notifications for action results
 */

import React, { useEffect, useCallback, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import { ApprovalQueueItem, RejectActionRequest } from "@/types/approval";
import { QualityScoreBadge } from "./QualityScoreBadge";
import { ComplianceStatusBadge } from "./ComplianceStatusBadge";
import { AutoPublishBadge } from "./AutoPublishBadge";
import { SourceTypeBadge } from "./SourceTypeBadge";
import { PublishTimeDisplay } from "./PublishTimeDisplay";
import { ComplianceDetails } from "./ComplianceDetails";
import { QualityBreakdown } from "./QualityBreakdown";
import { ApprovalActions } from "./ApprovalActions";
import { RejectReasonModal } from "./RejectReasonModal";
import { CaptionEditor } from "./CaptionEditor";
import { RewriteSuggestionsPanel } from "./RewriteSuggestionsPanel";
import { useApprovalActions } from "@/hooks/useApprovalActions";

export interface ApprovalDetailModalProps {
  item: ApprovalQueueItem | null;
  isOpen: boolean;
  onClose: () => void;
  onNavigate?: (direction: "prev" | "next") => void;
  hasPrev?: boolean;
  hasNext?: boolean;
  onActionComplete?: (action: "approve" | "reject" | "edit", itemId: string) => void;
}

/**
 * Detail modal for approval queue items.
 */
export function ApprovalDetailModal({
  item,
  isOpen,
  onClose,
  onNavigate,
  hasPrev = false,
  hasNext = false,
  onActionComplete,
}: ApprovalDetailModalProps): React.ReactElement | null {
  const [isEditing, setIsEditing] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);

  const {
    approve,
    reject,
    edit,
    applyRewrite,
    isLoading,
    loadingAction,
    error,
  } = useApprovalActions();

  // Handle approve action
  const handleApprove = useCallback(async () => {
    if (!item) return;

    try {
      const response = await approve(item.id);

      toast.success("Content approved", {
        description: response.message || `Scheduled for publishing`,
      });

      onActionComplete?.("approve", item.id);
      onClose();
    } catch (err) {
      toast.error("Approval failed", {
        description: err instanceof Error ? err.message : "Unknown error",
        action: {
          label: "Retry",
          onClick: handleApprove,
        },
      });
    }
  }, [item, approve, onActionComplete, onClose]);

  // Handle reject action (opens modal)
  const handleReject = useCallback(() => {
    setShowRejectModal(true);
  }, []);

  // Handle reject submission
  const handleRejectSubmit = useCallback(async (request: RejectActionRequest) => {
    if (!item) return;

    try {
      const response = await reject(item.id, request);

      toast.success("Content rejected", {
        description: response.message || "Item archived with rejection reason",
      });

      onActionComplete?.("reject", item.id);
      setShowRejectModal(false);
      onClose();
    } catch (err) {
      // Error is handled by the modal
      throw err;
    }
  }, [item, reject, onActionComplete, onClose]);

  // Handle edit action (enter edit mode)
  const handleEdit = useCallback(() => {
    setIsEditing(true);
  }, []);

  // Handle cancel edit
  const handleCancelEdit = useCallback(() => {
    setIsEditing(false);
  }, []);

  // Handle save caption
  const handleSaveCaption = useCallback(
    async (newCaption: string, newHashtags: string[]) => {
      if (!item) return;

      try {
        const response = await edit(item.id, {
          caption: newCaption,
          hashtags: newHashtags,
        });

        toast.success("Caption saved", {
          description: response.message || "Caption updated successfully",
        });

        setIsEditing(false);
        onActionComplete?.("edit", item.id);
      } catch (err) {
        toast.error("Save failed", {
          description: err instanceof Error ? err.message : "Unknown error",
        });
        throw err; // Re-throw to let CaptionEditor handle error state
      }
    },
    [item, edit, onActionComplete]
  );

  // Handle accept AI rewrite suggestions
  const handleAcceptRewrites = useCallback(
    async (suggestionIds: string[]) => {
      if (!item) return;

      try {
        const response = await applyRewrite(item.id, suggestionIds);

        toast.success("Suggestions applied", {
          description: `Applied ${suggestionIds.length} suggestion(s)`,
        });

        onActionComplete?.("edit", item.id);
      } catch (err) {
        toast.error("Failed to apply suggestions", {
          description: err instanceof Error ? err.message : "Unknown error",
        });
        throw err;
      }
    },
    [item, applyRewrite, onActionComplete]
  );

  // Keyboard navigation - modified to work with action shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen || showRejectModal) return;

      switch (e.key) {
        case "Escape":
          if (isEditing) {
            setIsEditing(false);
          } else {
            onClose();
          }
          break;
        case "ArrowLeft":
          if (hasPrev && onNavigate && !isEditing) {
            e.preventDefault();
            onNavigate("prev");
          }
          break;
        case "ArrowRight":
          if (hasNext && onNavigate && !isEditing) {
            e.preventDefault();
            onNavigate("next");
          }
          break;
      }
    },
    [isOpen, showRejectModal, isEditing, onClose, onNavigate, hasPrev, hasNext]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Reset edit state when item changes
  useEffect(() => {
    setIsEditing(false);
  }, [item?.id]);

  // Show error toast when error occurs
  useEffect(() => {
    if (error) {
      toast.error("Action failed", {
        description: error.message,
      });
    }
  }, [error]);

  if (!item) return null;

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="max-w-4xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              <SourceTypeBadge sourceType={item.source_type} />
              <span className="text-gray-400">|</span>
              <PublishTimeDisplay suggestedPublishTime={item.suggested_publish_time} />
            </DialogTitle>
          </DialogHeader>

          <ScrollArea className="max-h-[60vh]">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-4">
              {/* Left column: Image and badges */}
              <div className="space-y-4">
                {/* Full-size image */}
                <div className="rounded-lg overflow-hidden border">
                  <img
                    src={item.thumbnail_url.replace("?w=200&h=200", "")}
                    alt="Content preview"
                    className="w-full h-auto object-contain max-h-96"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = "/placeholder-image.svg";
                    }}
                  />
                </div>

                {/* Badges */}
                <div className="flex flex-wrap gap-2">
                  <QualityScoreBadge score={item.quality_score} size="lg" />
                  <ComplianceStatusBadge status={item.compliance_status} size="lg" />
                  <AutoPublishBadge wouldAutoPublish={item.would_auto_publish} size="lg" />
                </div>
              </div>

              {/* Right column: Caption and details */}
              <div className="space-y-4">
                {isEditing ? (
                  /* Edit mode: CaptionEditor */
                  <CaptionEditor
                    caption={item.full_caption}
                    originalCaption={item.original_caption}
                    hashtags={item.hashtags}
                    onSave={handleSaveCaption}
                    onCancel={handleCancelEdit}
                    isLoading={isLoading && loadingAction === "edit"}
                  />
                ) : (
                  <>
                    {/* Full caption */}
                    <div>
                      <h3 className="font-medium text-gray-900 mb-2">Caption</h3>
                      <p className="text-gray-700 whitespace-pre-wrap">
                        {item.full_caption}
                      </p>
                    </div>

                    {/* Hashtags */}
                    {item.hashtags.length > 0 && (
                      <div>
                        <h3 className="font-medium text-gray-900 mb-2">Hashtags</h3>
                        <div className="flex flex-wrap gap-2">
                          {item.hashtags.map((tag) => (
                            <span
                              key={tag}
                              className="text-sm text-blue-600 bg-blue-50 px-2 py-1 rounded"
                            >
                              {tag.startsWith("#") ? tag : `#${tag}`}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {/* AI Rewrite Suggestions */}
                {item.rewrite_suggestions && item.rewrite_suggestions.length > 0 && (
                  <RewriteSuggestionsPanel
                    suggestions={item.rewrite_suggestions}
                    onAccept={handleAcceptRewrites}
                    isLoading={isLoading && loadingAction === "edit"}
                  />
                )}

                {/* Compliance Details */}
                {item.compliance_details && item.compliance_details.length > 0 && (
                  <ComplianceDetails
                    status={item.compliance_status}
                    checks={item.compliance_details}
                  />
                )}

                {/* Quality Breakdown */}
                {item.quality_breakdown && (
                  <QualityBreakdown
                    breakdown={item.quality_breakdown}
                    overallScore={item.quality_score}
                  />
                )}
              </div>
            </div>
          </ScrollArea>

          {/* Action buttons */}
          <div className="border-t pt-4">
            <ApprovalActions
              onApprove={handleApprove}
              onReject={handleReject}
              onEdit={handleEdit}
              isLoading={isLoading}
              loadingAction={loadingAction}
              isEditing={isEditing}
              enableKeyboardShortcuts={isOpen && !showRejectModal && !isEditing}
              className="justify-center"
            />
          </div>

          {/* Navigation footer */}
          <div className="flex justify-between items-center pt-4 border-t">
            <Button
              variant="outline"
              onClick={() => onNavigate?.("prev")}
              disabled={!hasPrev || isLoading}
              aria-label="Previous item"
            >
              {"\u2190"} Previous
            </Button>
            <span className="text-sm text-gray-500">
              Press A to approve, R to reject, E to edit
            </span>
            <Button
              variant="outline"
              onClick={() => onNavigate?.("next")}
              disabled={!hasNext || isLoading}
              aria-label="Next item"
            >
              Next {"\u2192"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reject Reason Modal */}
      <RejectReasonModal
        isOpen={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        onSubmit={handleRejectSubmit}
        isLoading={isLoading && loadingAction === "reject"}
      />
    </>
  );
}

export default ApprovalDetailModal;
