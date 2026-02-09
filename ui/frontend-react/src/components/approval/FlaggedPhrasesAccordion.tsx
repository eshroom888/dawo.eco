/**
 * FlaggedPhrasesAccordion component.
 *
 * Expandable accordion showing flagged phrases with explanations.
 * Part of the detail view for compliance information.
 */

import React from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { ComplianceCheck } from "@/types/approval";

export interface FlaggedPhrasesAccordionProps {
  checks: ComplianceCheck[];
  defaultExpanded?: boolean;
  className?: string;
}

/**
 * Get status color for phrase.
 */
function getStatusColor(status: string): string {
  switch (status) {
    case "prohibited":
      return "text-red-700 bg-red-50";
    case "borderline":
      return "text-yellow-700 bg-yellow-50";
    case "permitted":
      return "text-green-700 bg-green-50";
    default:
      return "text-gray-700 bg-gray-50";
  }
}

/**
 * Get status icon.
 */
function getStatusIcon(status: string): string {
  switch (status) {
    case "prohibited":
      return "\u2717"; // X
    case "borderline":
      return "\u26A0"; // Warning
    case "permitted":
      return "\u2713"; // Checkmark
    default:
      return "\u2022"; // Bullet
  }
}

/**
 * Accordion for expanding flagged phrases with explanations.
 */
export function FlaggedPhrasesAccordion({
  checks,
  defaultExpanded = false,
  className = "",
}: FlaggedPhrasesAccordionProps): React.ReactElement {
  // Only show non-permitted checks
  const flaggedChecks = checks.filter((c) => c.status !== "permitted");

  if (flaggedChecks.length === 0) {
    return (
      <div className={`text-sm text-green-600 ${className}`}>
        {"\u2713"} No flagged phrases
      </div>
    );
  }

  return (
    <Accordion
      type="single"
      collapsible
      defaultValue={defaultExpanded ? "flagged" : undefined}
      className={className}
    >
      <AccordionItem value="flagged">
        <AccordionTrigger className="text-sm font-medium hover:no-underline py-2">
          <span className="flex items-center gap-2">
            <span className="text-amber-500">{"\u26A0"}</span>
            {flaggedChecks.length} Flagged Phrase
            {flaggedChecks.length !== 1 ? "s" : ""}
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-3 pt-2">
            {flaggedChecks.map((check, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border ${getStatusColor(check.status)}`}
              >
                <div className="flex items-start gap-2">
                  <span className="mt-0.5">{getStatusIcon(check.status)}</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-sm">
                        "{check.phrase}"
                      </span>
                      <Badge
                        variant="outline"
                        className="text-xs capitalize"
                      >
                        {check.status}
                      </Badge>
                    </div>
                    <p className="text-sm opacity-80">{check.explanation}</p>
                    {check.regulation_reference && (
                      <p className="text-xs mt-2 opacity-60">
                        {"\uD83D\uDCCB"} {check.regulation_reference}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

export default FlaggedPhrasesAccordion;
