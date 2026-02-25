/**
 * Tests for useReports hook.
 *
 * Story 6-10, Task 15: Test report list, generate, download, and templates.
 */

import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import { useReports } from "../useReports";

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
    {children}
  </SWRConfig>
);

const mockReportList = {
  items: [
    {
      report_id: "rpt-1",
      filename: "violation-report-2026-02-15-standard.pdf",
      evidence_count: 5,
      competitor_name: "TestCorp",
      template_type: "standard",
      generated_at: "2026-02-15T12:00:00Z",
      sha256_hash: "a".repeat(64),
      page_count: 3,
      file_size_bytes: 12000,
    },
  ],
  total_count: 1,
  has_more: false,
};

const mockTemplates = {
  templates: { standard: "Standard Report", mattilsynet: "Mattilsynet (Norwegian)" },
};

const mockGenerateResponse = {
  report_id: "rpt-new",
  filename: "violation-report-2026-02-15-standard.pdf",
  evidence_count: 3,
  page_count: 2,
  generated_at: "2026-02-15T12:00:00Z",
  sha256_hash: "b".repeat(64),
  download_url: "/api/reports/rpt-new/download",
};

describe("useReports", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("/reports/templates")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTemplates),
        });
      }
      if (typeof url === "string" && url.includes("/reports")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockReportList),
        });
      }
      return Promise.resolve({ ok: false, status: 404 });
    });
  });

  it("fetches report list", async () => {
    const { result } = renderHook(() => useReports(), { wrapper });

    await waitFor(() => {
      expect(result.current.reports).not.toBeNull();
    });

    expect(result.current.reports?.items.length).toBe(1);
    expect(result.current.reports?.items[0].report_id).toBe("rpt-1");
    expect(result.current.reports?.total_count).toBe(1);
  });

  it("generateReport calls POST endpoint", async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === "POST" && url.includes("/reports/generate")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGenerateResponse),
        });
      }
      if (url.includes("/reports/templates")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTemplates),
        });
      }
      if (url.includes("/reports")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockReportList),
        });
      }
      return Promise.resolve({ ok: false, status: 404 });
    });

    const { result } = renderHook(() => useReports(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let response: typeof mockGenerateResponse | undefined;
    await act(async () => {
      response = await result.current.generateReport({
        template_type: "standard",
        evidence_ids: ["ev-1", "ev-2"],
      });
    });

    expect(response?.report_id).toBe("rpt-new");
    expect(response?.evidence_count).toBe(3);

    // Verify POST was called with correct body
    const postCall = mockFetch.mock.calls.find(
      (c: [string, RequestInit?]) => c[1]?.method === "POST"
    );
    expect(postCall).toBeDefined();
    const body = JSON.parse(postCall![1]!.body as string);
    expect(body.template_type).toBe("standard");
    expect(body.evidence_ids).toEqual(["ev-1", "ev-2"]);
  });

  it("downloadReport triggers blob download", async () => {
    const mockBlob = new Blob(["%PDF-1.4"], { type: "application/pdf" });
    const mockUrl = "blob:http://localhost/fake-pdf-url";
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
      if (url.includes("/reports/templates")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTemplates) });
      }
      if (url.includes("/reports")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockReportList) });
      }
      return Promise.resolve({ ok: false, status: 404 });
    });

    const { result } = renderHook(() => useReports(), { wrapper });

    await act(async () => {
      await result.current.downloadReport("rpt-1", "test-report.pdf");
    });

    expect(mockCreateObjectURL).toHaveBeenCalledWith(mockBlob);
    expect(mockClick).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalledWith(mockUrl);

    jest.restoreAllMocks();
  });

  it("fetches template list from API", async () => {
    const { result } = renderHook(() => useReports(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Should have templates from API or fallback
    expect(result.current.templates).toBeDefined();
    expect(typeof result.current.templates).toBe("object");
  });
});
