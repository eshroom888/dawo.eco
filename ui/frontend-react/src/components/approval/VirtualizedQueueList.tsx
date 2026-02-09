/**
 * VirtualizedQueueList component.
 *
 * Renders a virtualized list of approval queue items for
 * performance with large queues (100+ items).
 *
 * Uses react-window for efficient rendering of only visible items.
 */

import React, { useCallback } from "react";
import { FixedSizeGrid as Grid } from "react-window";
import AutoSizer from "react-virtualized-auto-sizer";
import { ApprovalQueueItem as ApprovalQueueItemType } from "@/types/approval";
import { ApprovalQueueItem } from "./ApprovalQueueItem";

export interface VirtualizedQueueListProps {
  items: ApprovalQueueItemType[];
  onItemClick: (item: ApprovalQueueItemType) => void;
  columnCount?: number;
  rowHeight?: number;
  className?: string;
  /** Story 4-3: Enable selection for batch operations */
  selectable?: boolean;
  /** Story 4-3: Check if item is selected */
  isSelected?: (itemId: string) => boolean;
  /** Story 4-3: Toggle item selection */
  onSelectionChange?: (itemId: string) => void;
}

// Default dimensions
const DEFAULT_COLUMN_COUNT = 3;
const DEFAULT_ROW_HEIGHT = 280;
const COLUMN_GAP = 16;
const ROW_GAP = 16;

/**
 * Virtualized list for rendering large approval queues efficiently.
 *
 * Only renders items that are currently visible in the viewport,
 * significantly improving performance for queues with 100+ items.
 */
export function VirtualizedQueueList({
  items,
  onItemClick,
  columnCount = DEFAULT_COLUMN_COUNT,
  rowHeight = DEFAULT_ROW_HEIGHT,
  className = "",
  selectable = false,
  isSelected,
  onSelectionChange,
}: VirtualizedQueueListProps): React.ReactElement {
  const rowCount = Math.ceil(items.length / columnCount);

  const Cell = useCallback(
    ({
      columnIndex,
      rowIndex,
      style,
    }: {
      columnIndex: number;
      rowIndex: number;
      style: React.CSSProperties;
    }) => {
      const itemIndex = rowIndex * columnCount + columnIndex;
      if (itemIndex >= items.length) {
        return null;
      }

      const item = items[itemIndex];

      return (
        <div
          style={{
            ...style,
            left: Number(style.left) + COLUMN_GAP / 2,
            top: Number(style.top) + ROW_GAP / 2,
            width: Number(style.width) - COLUMN_GAP,
            height: Number(style.height) - ROW_GAP,
          }}
        >
          <ApprovalQueueItem
            item={item}
            onClick={onItemClick}
            className="h-full"
            selectable={selectable}
            isSelected={isSelected ? isSelected(item.id) : false}
            onSelectionChange={onSelectionChange}
          />
        </div>
      );
    },
    [items, columnCount, onItemClick, selectable, isSelected, onSelectionChange]
  );

  return (
    <div className={`w-full h-full ${className}`}>
      <AutoSizer>
        {({ height, width }) => {
          const columnWidth = width / columnCount;

          return (
            <Grid
              columnCount={columnCount}
              columnWidth={columnWidth}
              height={height}
              rowCount={rowCount}
              rowHeight={rowHeight}
              width={width}
              itemData={items}
            >
              {Cell}
            </Grid>
          );
        }}
      </AutoSizer>
    </div>
  );
}

export default VirtualizedQueueList;
