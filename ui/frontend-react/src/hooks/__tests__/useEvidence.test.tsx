/**
 * Tests for useEvidence hook.
 *
 * Story 6-9, Task 13: Test data fetching, filters, pagination, and download.
 */

import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import { useEvidence } from "../useEvidence";

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
    {children}
  </SWRConfig>
);

const mockEvidenceList = {
  items: [
    {
      id: "ev-1",
      competitor_name: "CompetitorA",
      violation_type: "unauthorized_treatment_claim",
      severity: "high",
      claim_text: "treats brain fog",
      claim_category: "treatment",
      source_type: "instagram_post",
      source_url: "https://instagram.com/p/ABC123/",
      captured_at: "2026-02-15T10:00:00Z",
      screenshot_path: "/evidence/screenshots/test.png",
      screenshot_hash: "a".repeat(64),
    },
  ],
  total_count: 1,
  has_more: false,
};

const mockSummary = {
  total_evidence: 10,
  by_severity: { high: 3, medium: 5, low: 2 },
  by_competitor: { CompetitorA: 6, CompetitorB: 4 },
  by_violation_type: { unauthorized_treatment_claim: 7 },
};

const mockCompetitors = ["CompetitorA", "CompetitorB"];

describe("useEvidence", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/evidence/summary")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      if (url.includes("/evidence/competitors") && !url.includes("/timeline")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockCompetitors),
        });
      }
      if (url.includes("/evidence")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockEvidenceList),
        });
      }
      return Promise.resolve({ ok: false, status: 404 });
    });
  });

  it("fetches evidence list", async () => {
    const { result } = renderHook(() => useEvidence(), { wrapper });

    await waitFor(() => {
      expect(result.current.evidence).not.toBeNull();
    });

    expect(result.current.evidence?.items.length).toBe(1);
    expect(result.current.evidence?.items[0].competitor_name).toBe("CompetitorA");
    expect(result.current.evidence?.total_count).toBe(1);
  });

  it("filter changes trigger re-fetch", async () => {
    const { result } = renderHook(() => useEvidence(), { wrapper });

    await waitFor(() => {
      expect(result.current.evidence).not.toBeNull();
    });

    const callCountBefore = mockFetch.mock.calls.length;

    act(() => {
      result.current.setFilters({ severity: "high" });
    });

    await waitFor(() => {
      // SWR should re-fetch with new URL including severity param
      const evidenceCalls = mockFetch.mock.calls.filter(
        (c: [string]) => c[0].includes("/evidence") && c[0].includes("severity=high")
      );
      expect(evidenceCalls.length).toBeGreaterThan(0);
    });

    // Filter should reset page to 0
    expect(result.current.page).toBe(0);
  });

  it("pagination state management", async () => {
    const { result } = renderHook(() => useEvidence(), { wrapper });

    expect(result.current.page).toBe(0);
    expect(result.current.pageSize).toBe(25);

    act(() => {
      result.current.setPage(2);
    });

    expect(result.current.page).toBe(2);

    // Setting filters resets page to 0
    act(() => {
      result.current.setFilters({ competitor: "CompetitorA" });
    });

    expect(result.current.page).toBe(0);
  });

  it("downloadEvidence triggers blob download", async () => {
    const mockBlob = new Blob(["fake zip"], { type: "application/zip" });
    const mockUrl = "blob:http://localhost/fake-url";
    const mockCreateObjectURL = jest.fn(() => mockUrl);
    const mockRevokeObjectURL = jest.fn();
    const mockClick = jest.fn();

    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;

    jest.spyOn(document, "createElement").mockImplementation((tag: string) => {
      if (tag === "a") {
        return { href: "", download: "", click: mockClick } as unknown as HTMLAnchorElement;
      }
      return document.createElement(tag);
    });

    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/download")) {
        return Promise.resolve({
          ok: true,
          blob: () => Promise.resolve(mockBlob),
        });
      }
      if (url.includes("/evidence/summary")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockSummary) });
      }
      if (url.includes("/evidence/competitors")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockCompetitors) });
      }
      if (url.includes("/evidence")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockEvidenceList) });
      }
      return Promise.resolve({ ok: false, status: 404 });
    });

    const { result } = renderHook(() => useEvidence(), { wrapper });

    await act(async () => {
      await result.current.downloadEvidence("ev-1");
    });

    expect(mockCreateObjectURL).toHaveBeenCalledWith(mockBlob);
    expect(mockClick).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalledWith(mockUrl);

    jest.restoreAllMocks();
  });
});
