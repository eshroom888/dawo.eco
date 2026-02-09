/**
 * ComplianceDetails component.
 *
 * Displays detailed compliance check results with:
 * - Overall compliance summary
 * - Collapsible sections for PROHIBITED vs BORDERLINE phrases
 * - Each flagged phrase with severity color
 * - EU regulation references for violations
 */

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { ComplianceCheck, ComplianceStatus } from "@/types/approval";
import { ComplianceStatusBadge } from "./ComplianceStatusBadge";

export interface ComplianceDetailsProps {
  status: ComplianceStatus;
  checks: ComplianceCheck[];
  className?: string;
}

/**
 * Get status color for individual check.
 */
function getCheckStatusColor(status: string): string {
  switch (status) {
    case "prohibited":
      return "bg-red-50 border-red-200 text-red-800";
    case "borderline":
      return "bg-yellow-50 border-yellow-200 text-yellow-800";
    case "permitted":
      return "bg-green-50 border-green-200 text-green-800";
    default:
      return "bg-gray-50 border-gray-200 text-gray-800";
  }
}

/**
 * Get status badge variant.
 */
function getStatusBadgeClass(status: string): string {
  switch (status) {
    case "prohibited":
      return "bg-red-100 text-red-800";
    case "borderline":
      return "bg-yellow-100 text-yellow-800";
    case "permitted":
      return "bg-green-100 text-green-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

/**
 * Individual compliance check item.
 */
function ComplianceCheckItem({
  check,
}: {
  check: ComplianceCheck;
}): React.ReactElement {
  return (
    <div
      className={`p-3 rounded-lg border ${getCheckStatusColor(check.status)}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-medium text-sm">"{check.phrase}"</span>
        <Badge variant="outline" className={`text-xs ${getStatusBadgeClass(check.status)}`}>
          {check.status}
        </Badge>
      </div>
      <p className="text-sm opacity-80">{check.explanation}</p>
      {check.regulation_reference && (
        <p className="text-xs mt-2 opacity-60">
          Reference: {check.regulation_reference}
        </p>
      )}
    </div>
  );
}

/**
 * Compliance details with collapsible sections.
 */
export function ComplianceDetails({
  status,
  checks,
  className = "",
}: ComplianceDetailsProps): React.ReactElement {
  // Group checks by status
  const prohibitedChecks = checks.filter((c) => c.status === "prohibited");
  const borderlineChecks = checks.filter((c) => c.status === "borderline");
  const permittedChecks = checks.filter((c) => c.status === "permitted");

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-3">
          Compliance Details
          <ComplianceStatusBadge status={status} size="sm" />
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Summary */}
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            {checks.length} phrases analyzed:{" "}
            <span className="text-red-600 font-medium">
              {prohibitedChecks.length} prohibited
            </span>
            ,{" "}
            <span className="text-yellow-600 font-medium">
              {borderlineChecks.length} borderline
            </span>
            ,{" "}
            <span className="text-green-600 font-medium">
              {permittedChecks.length} permitted
            </span>
          </p>
        </div>

        {/* Collapsible sections */}
        <Accordion type="multiple" defaultValue={["prohibited"]} className="space-y-2">
          {/* Prohibited section */}
          {prohibitedChecks.length > 0 && (
            <AccordionItem value="prohibited" className="border-red-200">
              <AccordionTrigger className="text-sm font-medium text-red-800 hover:no-underline">
                <span className="flex items-center gap-2">
                  <span className="text-red-500">{"\u26D4"}</span>
                  Prohibited Phrases ({prohibitedChecks.length})
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2 pt-2">
                  {prohibitedChecks.map((check, index) => (
                    <ComplianceCheckItem key={index} check={check} />
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Borderline section */}
          {borderlineChecks.length > 0 && (
            <AccordionItem value="borderline" className="border-yellow-200">
              <AccordionTrigger className="text-sm font-medium text-yellow-800 hover:no-underline">
                <span className="flex items-center gap-2">
                  <span className="text-yellow-500">{"\u26A0"}</span>
                  Borderline Phrases ({borderlineChecks.length})
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2 pt-2">
                  {borderlineChecks.map((check, index) => (
                    <ComplianceCheckItem key={index} check={check} />
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Permitted section */}
          {permittedChecks.length > 0 && (
            <AccordionItem value="permitted" className="border-green-200">
              <AccordionTrigger className="text-sm font-medium text-green-800 hover:no-underline">
                <span className="flex items-center gap-2">
                  <span className="text-green-500">{"\u2713"}</span>
                  Permitted Phrases ({permittedChecks.length})
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2 pt-2">
                  {permittedChecks.map((check, index) => (
                    <ComplianceCheckItem key={index} check={check} />
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          )}
        </Accordion>

        {/* Empty state */}
        {checks.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">
            No compliance checks performed.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default ComplianceDetails;
