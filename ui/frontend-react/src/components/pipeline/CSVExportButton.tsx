/**
 * CSVExportButton component.
 *
 * Story 5-5, Task 8.10: Export button that triggers CSV download.
 * Passes current filter parameters to the export endpoint.
 */

import React from "react";
import { Button } from "@/components/ui/button";

export interface CSVExportButtonProps {
  onExport: (status?: string) => void;
  currentStatus?: string | null;
  className?: string;
}

/**
 * Button to trigger CSV export of pipeline leads.
 */
export function CSVExportButton({
  onExport,
  currentStatus,
  className,
}: CSVExportButtonProps): React.ReactElement {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => onExport(currentStatus ?? undefined)}
      className={className}
      aria-label="Export leads as CSV"
    >
      Export CSV
    </Button>
  );
}

export default CSVExportButton;
