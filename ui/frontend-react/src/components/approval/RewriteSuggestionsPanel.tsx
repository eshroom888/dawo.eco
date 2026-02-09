/**
 * RewriteSuggestionsPanel component.
 *
 * Container for AI rewrite suggestions with bulk accept functionality.
 *
 * Features:
 * - List of suggestion cards
 * - Accept All button
 * - Collapsible panel
 * - Loading states
 */

import React, { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, CheckCheck, Loader2, Sparkles } from "lucide-react";
import { RewriteSuggestion as RewriteSuggestionType } from "@/types/approval";
import { RewriteSuggestion } from "./RewriteSuggestion";

export interface RewriteSuggestionsPanelProps {
  suggestions: RewriteSuggestionType[];
  onAccept: (suggestionIds: string[]) => Promise<void>;
  onDismiss?: (suggestionId: string) => void;
  isLoading?: boolean;
}

/**
 * Panel containing AI rewrite suggestions.
 */
export function RewriteSuggestionsPanel({
  suggestions,
  onAccept,
  onDismiss,
  isLoading = false,
}: RewriteSuggestionsPanelProps): React.ReactElement | null {
  const [isOpen, setIsOpen] = useState(true);
  const [acceptedIds, setAcceptedIds] = useState<Set<string>>(new Set());
  const [acceptingAll, setAcceptingAll] = useState(false);

  // Filter out dismissed suggestions
  const visibleSuggestions = suggestions.filter(
    (s) => !acceptedIds.has(s.id)
  );

  // Handle single accept
  const handleAccept = useCallback(
    async (suggestionId: string) => {
      await onAccept([suggestionId]);
      setAcceptedIds((prev) => new Set(prev).add(suggestionId));
    },
    [onAccept]
  );

  // Handle accept all
  const handleAcceptAll = useCallback(async () => {
    if (visibleSuggestions.length === 0) return;

    setAcceptingAll(true);
    try {
      const ids = visibleSuggestions.map((s) => s.id);
      await onAccept(ids);
      setAcceptedIds((prev) => {
        const next = new Set(prev);
        ids.forEach((id) => next.add(id));
        return next;
      });
    } finally {
      setAcceptingAll(false);
    }
  }, [visibleSuggestions, onAccept]);

  // Don't render if no suggestions
  if (suggestions.length === 0) {
    return null;
  }

  const pendingCount = visibleSuggestions.length;
  const acceptedCount = acceptedIds.size;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="border rounded-lg bg-white">
        {/* Header */}
        <CollapsibleTrigger asChild>
          <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-purple-600" />
              <h3 className="font-medium">AI Rewrite Suggestions</h3>
              {pendingCount > 0 && (
                <Badge variant="secondary">{pendingCount} pending</Badge>
              )}
              {acceptedCount > 0 && (
                <Badge variant="default" className="bg-green-600">
                  {acceptedCount} accepted
                </Badge>
              )}
            </div>
            <Button variant="ghost" size="sm">
              {isOpen ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="p-4 pt-0 space-y-4">
            {/* Accept All button */}
            {pendingCount > 1 && (
              <div className="flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleAcceptAll}
                  disabled={isLoading || acceptingAll}
                  className="border-green-500 text-green-600 hover:bg-green-50"
                >
                  {acceptingAll ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <CheckCheck className="h-4 w-4 mr-2" />
                  )}
                  Accept All ({pendingCount})
                </Button>
              </div>
            )}

            {/* Suggestion cards */}
            <div className="space-y-3">
              {suggestions.map((suggestion) => (
                <RewriteSuggestion
                  key={suggestion.id}
                  suggestion={suggestion}
                  onAccept={handleAccept}
                  onReject={onDismiss}
                  isLoading={isLoading}
                  isAccepted={acceptedIds.has(suggestion.id)}
                />
              ))}
            </div>

            {/* All accepted message */}
            {pendingCount === 0 && acceptedCount > 0 && (
              <p className="text-center text-sm text-green-600 py-4">
                All suggestions have been applied!
              </p>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

export default RewriteSuggestionsPanel;
