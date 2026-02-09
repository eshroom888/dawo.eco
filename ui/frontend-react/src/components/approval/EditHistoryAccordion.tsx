/**
 * EditHistoryAccordion component.
 *
 * Displays version timeline of caption edits for audit trail.
 * Allows viewing previous versions and reverting to them.
 *
 * Features:
 * - Accordion view of edit history
 * - Diff highlighting (strikethrough old, green new)
 * - Revert to any previous version
 * - Timestamp and editor display
 */

import React, { useState } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, RotateCcw, Clock, User } from "lucide-react";
import { EditHistoryEntry } from "@/types/approval";

export interface EditHistoryAccordionProps {
  history: EditHistoryEntry[];
  onRevert: (versionId: string) => Promise<void>;
  isLoading?: boolean;
  currentCaption?: string;
}

/**
 * Format timestamp for display.
 */
function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Simple diff display showing old vs new text.
 */
function DiffView({
  previous,
  current,
}: {
  previous: string;
  current: string;
}): React.ReactElement {
  // For now, show simple before/after view
  // A full diff algorithm could be added later
  const truncate = (text: string, maxLen: number) =>
    text.length > maxLen ? text.slice(0, maxLen) + "..." : text;

  return (
    <div className="space-y-2 text-sm">
      <div>
        <span className="text-gray-500 font-medium">Before:</span>
        <p className="text-red-600 line-through mt-1 p-2 bg-red-50 rounded">
          {truncate(previous, 200)}
        </p>
      </div>
      <div>
        <span className="text-gray-500 font-medium">After:</span>
        <p className="text-green-600 mt-1 p-2 bg-green-50 rounded">
          {truncate(current, 200)}
        </p>
      </div>
    </div>
  );
}

/**
 * Accordion component showing edit history timeline.
 */
export function EditHistoryAccordion({
  history,
  onRevert,
  isLoading = false,
  currentCaption,
}: EditHistoryAccordionProps): React.ReactElement {
  const [revertingId, setRevertingId] = useState<string | null>(null);

  const handleRevert = async (versionId: string) => {
    setRevertingId(versionId);
    try {
      await onRevert(versionId);
    } finally {
      setRevertingId(null);
    }
  };

  if (history.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>No edit history available</p>
        <p className="text-sm">Changes will appear here after editing</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-700">
          Edit History ({history.length} {history.length === 1 ? "edit" : "edits"})
        </h4>
      </div>

      <Accordion type="single" collapsible className="w-full">
        {history.map((entry, index) => (
          <AccordionItem key={entry.id} value={entry.id}>
            <AccordionTrigger className="hover:no-underline">
              <div className="flex items-center gap-3 text-left">
                <Badge
                  variant={index === 0 ? "default" : "secondary"}
                  className="text-xs"
                >
                  v{history.length - index}
                </Badge>
                <div className="flex flex-col">
                  <span className="text-sm font-medium">
                    {formatTimestamp(entry.edited_at)}
                  </span>
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {entry.editor}
                  </span>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 pt-2">
                <DiffView
                  previous={entry.previous_caption}
                  current={entry.new_caption}
                />

                {/* Only show revert if this isn't the current version */}
                {entry.new_caption !== currentCaption && (
                  <div className="flex justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRevert(entry.id)}
                      disabled={isLoading || revertingId !== null}
                    >
                      {revertingId === entry.id ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <RotateCcw className="h-4 w-4 mr-2" />
                      )}
                      Revert to this version
                    </Button>
                  </div>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}

export default EditHistoryAccordion;
