/**
 * RewriteSuggestion component.
 *
 * Displays AI-generated rewrite suggestions with accept functionality.
 *
 * Features:
 * - Original vs suggested text comparison
 * - Accept/reject per suggestion
 * - Type-based styling (compliance, brand_voice, quality)
 */

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, X, AlertCircle, Palette, Star } from "lucide-react";
import { RewriteSuggestion as RewriteSuggestionType } from "@/types/approval";

export interface RewriteSuggestionProps {
  suggestion: RewriteSuggestionType;
  onAccept: (suggestionId: string) => void;
  onReject?: (suggestionId: string) => void;
  isLoading?: boolean;
  isAccepted?: boolean;
}

/**
 * Get icon for suggestion type.
 */
function getTypeIcon(type: string): React.ReactElement {
  switch (type) {
    case "compliance":
      return <AlertCircle className="h-4 w-4" />;
    case "brand_voice":
      return <Palette className="h-4 w-4" />;
    case "quality":
      return <Star className="h-4 w-4" />;
    default:
      return <AlertCircle className="h-4 w-4" />;
  }
}

/**
 * Get styling for suggestion type.
 */
function getTypeStyle(type: string): string {
  switch (type) {
    case "compliance":
      return "bg-red-100 text-red-800 border-red-200";
    case "brand_voice":
      return "bg-purple-100 text-purple-800 border-purple-200";
    case "quality":
      return "bg-blue-100 text-blue-800 border-blue-200";
    default:
      return "bg-gray-100 text-gray-800 border-gray-200";
  }
}

/**
 * Get label for suggestion type.
 */
function getTypeLabel(type: string): string {
  switch (type) {
    case "compliance":
      return "Compliance";
    case "brand_voice":
      return "Brand Voice";
    case "quality":
      return "Quality";
    default:
      return type;
  }
}

/**
 * Single AI rewrite suggestion card.
 */
export function RewriteSuggestion({
  suggestion,
  onAccept,
  onReject,
  isLoading = false,
  isAccepted = false,
}: RewriteSuggestionProps): React.ReactElement {
  return (
    <Card
      className={`transition-all ${
        isAccepted
          ? "border-green-500 bg-green-50"
          : "hover:border-gray-300"
      }`}
    >
      <CardContent className="p-4 space-y-3">
        {/* Header with type badge */}
        <div className="flex items-center justify-between">
          <Badge
            variant="outline"
            className={`flex items-center gap-1 ${getTypeStyle(suggestion.type)}`}
          >
            {getTypeIcon(suggestion.type)}
            {getTypeLabel(suggestion.type)}
          </Badge>

          {isAccepted && (
            <Badge variant="default" className="bg-green-600">
              <Check className="h-3 w-3 mr-1" />
              Applied
            </Badge>
          )}
        </div>

        {/* Reason */}
        <p className="text-sm text-gray-600">{suggestion.reason}</p>

        {/* Text comparison */}
        <div className="space-y-2">
          {/* Original text */}
          <div className="p-2 bg-red-50 border border-red-200 rounded">
            <p className="text-xs text-red-600 font-medium mb-1">Original:</p>
            <p className="text-sm line-through text-red-800">
              {suggestion.original_text}
            </p>
          </div>

          {/* Suggested text */}
          <div className="p-2 bg-green-50 border border-green-200 rounded">
            <p className="text-xs text-green-600 font-medium mb-1">Suggested:</p>
            <p className="text-sm text-green-800">{suggestion.suggested_text}</p>
          </div>
        </div>

        {/* Action buttons */}
        {!isAccepted && (
          <div className="flex justify-end gap-2 pt-2">
            {onReject && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onReject(suggestion.id)}
                disabled={isLoading}
              >
                <X className="h-4 w-4 mr-1" />
                Dismiss
              </Button>
            )}
            <Button
              size="sm"
              onClick={() => onAccept(suggestion.id)}
              disabled={isLoading}
              className="bg-green-600 hover:bg-green-700"
            >
              <Check className="h-4 w-4 mr-1" />
              Accept
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default RewriteSuggestion;
