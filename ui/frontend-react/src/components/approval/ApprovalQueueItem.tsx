/**
 * ApprovalQueueItem component.
 *
 * Displays a single approval queue item as a card with:
 * - Thumbnail preview
 * - Caption excerpt (first 100 chars)
 * - Quality score badge with color coding
 * - Compliance status badge
 * - Auto-publish badge (if applicable)
 * - Source type badge
 * - Suggested publish time
 */

import React from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ApprovalQueueItem as ApprovalQueueItemType } from "@/types/approval";
import { QualityScoreBadge } from "./QualityScoreBadge";
import { ComplianceStatusBadge } from "./ComplianceStatusBadge";
import { AutoPublishBadge } from "./AutoPublishBadge";
import { SourceTypeBadge } from "./SourceTypeBadge";
import { PublishTimeDisplay } from "./PublishTimeDisplay";

export interface ApprovalQueueItemProps {
  item: ApprovalQueueItemType;
  onClick?: (item: ApprovalQueueItemType) => void;
  className?: string;
  /** Story 4-3: Enable selection checkbox */
  selectable?: boolean;
  /** Story 4-3: Whether this item is currently selected */
  isSelected?: boolean;
  /** Story 4-3: Callback when selection changes */
  onSelectionChange?: (itemId: string) => void;
}

/**
 * Individual approval queue item card.
 *
 * Clicking the card triggers the onClick handler to open detail view.
 * Story 4-3: Supports optional checkbox for batch selection.
 */
export function ApprovalQueueItem({
  item,
  onClick,
  className = "",
  selectable = false,
  isSelected = false,
  onSelectionChange,
}: ApprovalQueueItemProps): React.ReactElement {
  const handleClick = () => {
    if (onClick) {
      onClick(item);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  };

  /**
   * Story 4-3: Handle checkbox click without triggering card click.
   */
  const handleCheckboxClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  /**
   * Story 4-3: Handle checkbox change.
   */
  const handleCheckboxChange = () => {
    if (onSelectionChange) {
      onSelectionChange(item.id);
    }
  };

  // Task 1.4: Visual highlight for selected items
  const selectedClassName = isSelected
    ? "ring-2 ring-blue-500 bg-blue-50/50"
    : "";

  return (
    <Card
      className={`cursor-pointer hover:shadow-lg transition-shadow duration-200 focus-within:ring-2 focus-within:ring-blue-500 ${selectedClassName} ${className}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="article"
      aria-label={`View details for: ${item.caption_excerpt}`}
      data-selected={isSelected}
    >
      <CardHeader className="pb-2">
        {/* Thumbnail and badges row */}
        <div className="flex gap-4">
          {/* Story 4-3: Selection checkbox */}
          {selectable && (
            <div
              className="flex-shrink-0 flex items-start pt-1"
              onClick={handleCheckboxClick}
            >
              <Checkbox
                checked={isSelected}
                onCheckedChange={handleCheckboxChange}
                aria-label={`Select item: ${item.caption_excerpt}`}
              />
            </div>
          )}

          {/* Thumbnail */}
          <div className="flex-shrink-0">
            <img
              src={item.thumbnail_url}
              alt="Content preview"
              className="w-20 h-20 object-cover rounded-md"
              loading="lazy"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.src = "/placeholder-image.svg";
                target.alt = "Preview unavailable";
              }}
            />
          </div>

          {/* Badges column */}
          <div className="flex flex-col gap-2 flex-1 min-w-0">
            {/* Top row: Quality score and compliance */}
            <div className="flex flex-wrap gap-2">
              <QualityScoreBadge score={item.quality_score} size="sm" />
              <ComplianceStatusBadge status={item.compliance_status} size="sm" />
              <AutoPublishBadge wouldAutoPublish={item.would_auto_publish} size="sm" />
            </div>

            {/* Middle row: Source type */}
            <div className="flex flex-wrap gap-2">
              <SourceTypeBadge sourceType={item.source_type} size="sm" />
            </div>

            {/* Bottom row: Publish time */}
            <PublishTimeDisplay suggestedPublishTime={item.suggested_publish_time} />
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-2">
        {/* Caption excerpt */}
        <p className="text-sm text-gray-700 line-clamp-2">
          {item.caption_excerpt}
          {item.full_caption.length > 100 && "..."}
        </p>

        {/* Hashtags preview */}
        {item.hashtags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {item.hashtags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded"
              >
                {tag.startsWith("#") ? tag : `#${tag}`}
              </span>
            ))}
            {item.hashtags.length > 3 && (
              <span className="text-xs text-gray-400">
                +{item.hashtags.length - 3} more
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default ApprovalQueueItem;
