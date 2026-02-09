/**
 * Tests for useQueueSelection hook.
 *
 * Story 4-3: Batch Approval Capability
 * Task 1: Add selection checkboxes to queue items
 */

import { renderHook, act } from "@testing-library/react";
import { useQueueSelection } from "../useQueueSelection";
import { ApprovalQueueItem, ComplianceStatus, SourcePriority } from "@/types/approval";

// Mock items for testing
const createMockItem = (id: string, wouldAutoPublish = false): ApprovalQueueItem => ({
  id,
  thumbnail_url: `https://example.com/thumb-${id}.jpg`,
  caption_excerpt: `Caption for ${id}`,
  full_caption: `Full caption for ${id}`,
  quality_score: 8.5,
  quality_color: "green",
  compliance_status: ComplianceStatus.COMPLIANT,
  would_auto_publish: wouldAutoPublish,
  suggested_publish_time: "2026-02-10T14:00:00Z",
  source_type: "instagram_post",
  source_priority: SourcePriority.TRENDING,
  hashtags: ["#DAWO"],
  created_at: "2026-02-08T10:00:00Z",
});

const mockItems: ApprovalQueueItem[] = [
  createMockItem("item-1", true),
  createMockItem("item-2", false),
  createMockItem("item-3", true),
  createMockItem("item-4", false),
  createMockItem("item-5", true),
];

describe("useQueueSelection", () => {
  // Task 1.2: useQueueSelection hook manages selected item IDs
  describe("initial state", () => {
    it("starts with empty selection", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      expect(result.current.selectedIds.size).toBe(0);
      expect(result.current.selectedCount).toBe(0);
    });

    it("provides isSelected function that returns false for all items initially", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      mockItems.forEach((item) => {
        expect(result.current.isSelected(item.id)).toBe(false);
      });
    });
  });

  // Task 1.1: Toggle selection
  describe("toggleSelection", () => {
    it("adds item to selection when not selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.toggleSelection("item-1");
      });

      expect(result.current.isSelected("item-1")).toBe(true);
      expect(result.current.selectedCount).toBe(1);
    });

    it("removes item from selection when already selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.toggleSelection("item-1");
      });
      act(() => {
        result.current.toggleSelection("item-1");
      });

      expect(result.current.isSelected("item-1")).toBe(false);
      expect(result.current.selectedCount).toBe(0);
    });

    it("can select multiple items", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.toggleSelection("item-1");
        result.current.toggleSelection("item-2");
        result.current.toggleSelection("item-3");
      });

      expect(result.current.selectedCount).toBe(3);
      expect(result.current.isSelected("item-1")).toBe(true);
      expect(result.current.isSelected("item-2")).toBe(true);
      expect(result.current.isSelected("item-3")).toBe(true);
    });
  });

  // Task 1.3: Select All functionality
  describe("selectAll", () => {
    it("selects all provided item IDs", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));
      const allIds = mockItems.map((item) => item.id);

      act(() => {
        result.current.selectAll(allIds);
      });

      expect(result.current.selectedCount).toBe(5);
      mockItems.forEach((item) => {
        expect(result.current.isSelected(item.id)).toBe(true);
      });
    });
  });

  // Task 1.6: Clear selection
  describe("clearSelection", () => {
    it("clears all selections", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.toggleSelection("item-1");
        result.current.toggleSelection("item-2");
      });

      expect(result.current.selectedCount).toBe(2);

      act(() => {
        result.current.clearSelection();
      });

      expect(result.current.selectedCount).toBe(0);
      expect(result.current.isSelected("item-1")).toBe(false);
      expect(result.current.isSelected("item-2")).toBe(false);
    });
  });

  // Task 5.3: Filter to select only would_auto_publish=true items
  describe("selectByFilter", () => {
    it("selects items matching predicate", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.selectByFilter((item) => item.would_auto_publish);
      });

      // Items 1, 3, 5 have would_auto_publish = true
      expect(result.current.selectedCount).toBe(3);
      expect(result.current.isSelected("item-1")).toBe(true);
      expect(result.current.isSelected("item-2")).toBe(false);
      expect(result.current.isSelected("item-3")).toBe(true);
      expect(result.current.isSelected("item-4")).toBe(false);
      expect(result.current.isSelected("item-5")).toBe(true);
    });

    it("replaces previous selection when filter applied", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      // First select some items manually
      act(() => {
        result.current.toggleSelection("item-2");
        result.current.toggleSelection("item-4");
      });

      expect(result.current.selectedCount).toBe(2);

      // Apply filter - should replace selection
      act(() => {
        result.current.selectByFilter((item) => item.would_auto_publish);
      });

      expect(result.current.selectedCount).toBe(3);
      expect(result.current.isSelected("item-2")).toBe(false);
      expect(result.current.isSelected("item-4")).toBe(false);
    });
  });

  // getSelectedItems helper
  describe("getSelectedItems", () => {
    it("returns array of selected item objects", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.toggleSelection("item-1");
        result.current.toggleSelection("item-3");
      });

      const selectedItems = result.current.getSelectedItems();

      expect(selectedItems).toHaveLength(2);
      expect(selectedItems.map((i) => i.id)).toContain("item-1");
      expect(selectedItems.map((i) => i.id)).toContain("item-3");
    });
  });

  // Task 1.5: Selection persists across item updates
  describe("selection persistence", () => {
    it("maintains selection when items array updates", () => {
      const { result, rerender } = renderHook(
        ({ items }) => useQueueSelection(items),
        { initialProps: { items: mockItems } }
      );

      act(() => {
        result.current.toggleSelection("item-1");
        result.current.toggleSelection("item-3");
      });

      expect(result.current.selectedCount).toBe(2);

      // Simulate items update (e.g., from re-fetch)
      const updatedItems = [...mockItems];
      rerender({ items: updatedItems });

      // Selection should persist
      expect(result.current.selectedCount).toBe(2);
      expect(result.current.isSelected("item-1")).toBe(true);
      expect(result.current.isSelected("item-3")).toBe(true);
    });

    it("removes selection for items no longer in list", () => {
      const { result, rerender } = renderHook(
        ({ items }) => useQueueSelection(items),
        { initialProps: { items: mockItems } }
      );

      act(() => {
        result.current.toggleSelection("item-1");
        result.current.toggleSelection("item-3");
      });

      // Remove item-1 from list (simulating it was approved/rejected)
      const reducedItems = mockItems.filter((i) => i.id !== "item-1");
      rerender({ items: reducedItems });

      // item-1 should be auto-deselected, item-3 stays selected
      expect(result.current.selectedCount).toBe(1);
      expect(result.current.isSelected("item-1")).toBe(false);
      expect(result.current.isSelected("item-3")).toBe(true);
    });
  });

  // isAllSelected helper for "Select All" checkbox state
  describe("isAllSelected", () => {
    it("returns true when all items are selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.selectAll(mockItems.map((i) => i.id));
      });

      expect(result.current.isAllSelected).toBe(true);
    });

    it("returns false when no items are selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      expect(result.current.isAllSelected).toBe(false);
    });

    it("returns false when only some items are selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.toggleSelection("item-1");
        result.current.toggleSelection("item-2");
      });

      expect(result.current.isAllSelected).toBe(false);
    });
  });

  // isSomeSelected helper for indeterminate checkbox state
  describe("isSomeSelected", () => {
    it("returns true when some but not all items are selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.toggleSelection("item-1");
      });

      expect(result.current.isSomeSelected).toBe(true);
    });

    it("returns false when no items are selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      expect(result.current.isSomeSelected).toBe(false);
    });

    it("returns false when all items are selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.selectAll(mockItems.map((i) => i.id));
      });

      expect(result.current.isSomeSelected).toBe(false);
    });
  });

  // toggleSelectAll for "Select All" checkbox
  describe("toggleSelectAll", () => {
    it("selects all when none selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.toggleSelectAll();
      });

      expect(result.current.isAllSelected).toBe(true);
      expect(result.current.selectedCount).toBe(5);
    });

    it("deselects all when all selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.selectAll(mockItems.map((i) => i.id));
      });

      expect(result.current.isAllSelected).toBe(true);

      act(() => {
        result.current.toggleSelectAll();
      });

      expect(result.current.selectedCount).toBe(0);
    });

    it("selects all when some selected", () => {
      const { result } = renderHook(() => useQueueSelection(mockItems));

      act(() => {
        result.current.toggleSelection("item-1");
      });

      expect(result.current.isSomeSelected).toBe(true);

      act(() => {
        result.current.toggleSelectAll();
      });

      expect(result.current.isAllSelected).toBe(true);
      expect(result.current.selectedCount).toBe(5);
    });
  });
});
