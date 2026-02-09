/**
 * Tests for useApprovalQueue hook.
 *
 * Task 9.6: Test queue sorting by source priority
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { useApprovalQueue } from "@/hooks/useApprovalQueue";
import { SourcePriority, ComplianceStatus } from "@/types/approval";

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Wrapper to provide SWR config for tests
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
    {children}
  </SWRConfig>
);

// Mock response data with items in different priority order
const mockQueueResponse = {
  items: [
    {
      id: "1",
      thumbnail_url: "https://example.com/1.jpg",
      caption_excerpt: "Trending content",
      full_caption: "Trending content full",
      quality_score: 9.0,
      quality_color: "green",
      compliance_status: ComplianceStatus.COMPLIANT,
      would_auto_publish: true,
      suggested_publish_time: "2026-02-10T14:00:00Z",
      source_type: "instagram_post",
      source_priority: SourcePriority.TRENDING,
      hashtags: [],
      created_at: "2026-02-08T10:00:00Z",
    },
    {
      id: "2",
      thumbnail_url: "https://example.com/2.jpg",
      caption_excerpt: "Scheduled content",
      full_caption: "Scheduled content full",
      quality_score: 8.0,
      quality_color: "green",
      compliance_status: ComplianceStatus.COMPLIANT,
      would_auto_publish: false,
      suggested_publish_time: "2026-02-11T10:00:00Z",
      source_type: "instagram_post",
      source_priority: SourcePriority.SCHEDULED,
      hashtags: [],
      created_at: "2026-02-08T11:00:00Z",
    },
    {
      id: "3",
      thumbnail_url: "https://example.com/3.jpg",
      caption_excerpt: "Research content",
      full_caption: "Research content full",
      quality_score: 7.0,
      quality_color: "yellow",
      compliance_status: ComplianceStatus.WARNING,
      would_auto_publish: false,
      suggested_publish_time: null,
      source_type: "instagram_post",
      source_priority: SourcePriority.RESEARCH,
      hashtags: [],
      created_at: "2026-02-08T12:00:00Z",
    },
  ],
  total_count: 3,
  next_cursor: null,
  has_more: false,
};

describe("useApprovalQueue", () => {
  beforeEach(() => {
    mockFetch.mockClear();
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockQueueResponse,
    });
  });

  describe("data fetching", () => {
    it("fetches approval queue data", async () => {
      const { result } = renderHook(() => useApprovalQueue(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.items).toHaveLength(3);
      expect(result.current.totalCount).toBe(3);
    });

    it("returns empty items while loading", () => {
      const { result } = renderHook(() => useApprovalQueue(), { wrapper });
      expect(result.current.items).toEqual([]);
    });

    it("handles fetch error", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
      });

      const { result } = renderHook(() => useApprovalQueue(), { wrapper });

      await waitFor(() => {
        expect(result.current.error).toBeDefined();
      });
    });
  });

  describe("priority sorting (AC #2)", () => {
    it("returns items sorted by source priority (TRENDING first)", async () => {
      const { result } = renderHook(() => useApprovalQueue(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const items = result.current.items;
      expect(items[0].source_priority).toBe(SourcePriority.TRENDING);
      expect(items[1].source_priority).toBe(SourcePriority.SCHEDULED);
      expect(items[2].source_priority).toBe(SourcePriority.RESEARCH);
    });

    it("TRENDING has lower priority value than SCHEDULED", () => {
      expect(SourcePriority.TRENDING).toBeLessThan(SourcePriority.SCHEDULED);
    });

    it("SCHEDULED has lower priority value than EVERGREEN", () => {
      expect(SourcePriority.SCHEDULED).toBeLessThan(SourcePriority.EVERGREEN);
    });

    it("EVERGREEN has lower priority value than RESEARCH", () => {
      expect(SourcePriority.EVERGREEN).toBeLessThan(SourcePriority.RESEARCH);
    });
  });

  describe("pagination", () => {
    it("returns pagination info", async () => {
      const { result } = renderHook(() => useApprovalQueue(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.hasMore).toBe(false);
      expect(result.current.nextCursor).toBeNull();
    });

    it("passes limit parameter to API", async () => {
      renderHook(() => useApprovalQueue(25), { wrapper });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const fetchUrl = mockFetch.mock.calls[0][0];
      expect(fetchUrl).toContain("limit=25");
    });

    it("passes cursor parameter to API", async () => {
      renderHook(() => useApprovalQueue(50, "test-cursor"), { wrapper });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const fetchUrl = mockFetch.mock.calls[0][0];
      expect(fetchUrl).toContain("cursor=test-cursor");
    });
  });

  describe("refresh functionality", () => {
    it("provides refresh function", async () => {
      const { result } = renderHook(() => useApprovalQueue(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(typeof result.current.refresh).toBe("function");
    });
  });
});
