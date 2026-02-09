/**
 * Tests for PublishedPostCard component.
 *
 * Story 4-5, Task 9.7: Test dashboard displays published post correctly.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { PublishedPostCard } from "../PublishedPostCard";
import { ScheduledItem } from "@/types/schedule";
import { SourcePriority, ComplianceStatus } from "@/types/approval";

// Mock the RetryButton to avoid testing it here
jest.mock("../RetryButton", () => ({
  RetryButton: ({ itemId, onRetrySuccess }: { itemId: string; onRetrySuccess?: () => void }) => (
    <button data-testid={`mock-retry-button-${itemId}`} onClick={onRetrySuccess}>
      Mock Retry
    </button>
  ),
}));

describe("PublishedPostCard", () => {
  const baseItem: ScheduledItem = {
    id: "test-item-1",
    title: "Test post about wellness",
    thumbnail_url: "https://example.com/thumb.jpg",
    scheduled_publish_time: "2026-02-10T09:00:00Z",
    source_type: "instagram_post",
    source_priority: SourcePriority.EVERGREEN,
    quality_score: 8.5,
    quality_color: "green",
    compliance_status: ComplianceStatus.COMPLIANT,
    conflicts: [],
    is_imminent: false,
  };

  describe("Published post display", () => {
    const publishedItem: ScheduledItem = {
      ...baseItem,
      status: "published",
      instagram_permalink: "https://www.instagram.com/p/ABC123/",
      published_at: "2026-02-10T09:05:00Z",
    };

    it("renders card with correct testid", () => {
      render(<PublishedPostCard item={publishedItem} />);
      expect(
        screen.getByTestId(`published-post-card-${publishedItem.id}`)
      ).toBeInTheDocument();
    });

    it("displays thumbnail image", () => {
      render(<PublishedPostCard item={publishedItem} />);
      const img = screen.getByAltText(publishedItem.title);
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute("src", publishedItem.thumbnail_url);
    });

    it("displays post title", () => {
      render(<PublishedPostCard item={publishedItem} />);
      expect(screen.getByText(publishedItem.title)).toBeInTheDocument();
    });

    it("shows green checkmark for published posts (Task 7.7)", () => {
      render(<PublishedPostCard item={publishedItem} />);
      expect(screen.getByTestId("published-checkmark")).toBeInTheDocument();
    });

    it("shows Instagram permalink as clickable link (Task 7.3)", () => {
      render(<PublishedPostCard item={publishedItem} />);
      const link = screen.getByTestId("instagram-link");
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", publishedItem.instagram_permalink);
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    });

    it("displays publish timestamp in readable format (Task 7.4)", () => {
      render(<PublishedPostCard item={publishedItem} />);
      // Should show "Published: <formatted date>"
      expect(screen.getByText(/Published:/)).toBeInTheDocument();
    });

    it("does not show retry button for published posts", () => {
      render(<PublishedPostCard item={publishedItem} />);
      expect(
        screen.queryByTestId(`mock-retry-button-${publishedItem.id}`)
      ).not.toBeInTheDocument();
    });

    it("applies green border for published status", () => {
      render(<PublishedPostCard item={publishedItem} />);
      const card = screen.getByTestId(`published-post-card-${publishedItem.id}`);
      expect(card).toHaveClass("border-green-200");
    });
  });

  describe("Failed post display", () => {
    const failedItem: ScheduledItem = {
      ...baseItem,
      status: "publish_failed",
      publish_error: "Rate limit exceeded",
    };

    it("shows error message for failed posts", () => {
      render(<PublishedPostCard item={failedItem} />);
      expect(screen.getByTestId("publish-error")).toBeInTheDocument();
      expect(screen.getByText(/Rate limit exceeded/)).toBeInTheDocument();
    });

    it("shows retry button for failed posts (Task 7.6)", () => {
      render(<PublishedPostCard item={failedItem} />);
      expect(
        screen.getByTestId(`mock-retry-button-${failedItem.id}`)
      ).toBeInTheDocument();
    });

    it("applies red border for failed status", () => {
      render(<PublishedPostCard item={failedItem} />);
      const card = screen.getByTestId(`published-post-card-${failedItem.id}`);
      expect(card).toHaveClass("border-red-200");
    });

    it("does not show Instagram link for failed posts", () => {
      render(<PublishedPostCard item={failedItem} />);
      expect(screen.queryByTestId("instagram-link")).not.toBeInTheDocument();
    });

    it("does not show green checkmark for failed posts", () => {
      render(<PublishedPostCard item={failedItem} />);
      expect(screen.queryByTestId("published-checkmark")).not.toBeInTheDocument();
    });
  });

  describe("Retry functionality", () => {
    const failedItem: ScheduledItem = {
      ...baseItem,
      status: "publish_failed",
      publish_error: "Network error",
    };

    it("calls onRetrySuccess callback when retry succeeds", () => {
      const onRetrySuccess = jest.fn();
      render(
        <PublishedPostCard item={failedItem} onRetrySuccess={onRetrySuccess} />
      );

      // Click the mocked retry button
      fireEvent.click(
        screen.getByTestId(`mock-retry-button-${failedItem.id}`)
      );

      expect(onRetrySuccess).toHaveBeenCalled();
    });
  });

  describe("Timestamp formatting", () => {
    it("formats timestamp to local timezone (Task 7.4)", () => {
      const publishedItem: ScheduledItem = {
        ...baseItem,
        status: "published",
        instagram_permalink: "https://www.instagram.com/p/ABC123/",
        published_at: "2026-02-10T14:30:00Z",
      };

      render(<PublishedPostCard item={publishedItem} />);

      // Should format the date - exact format depends on locale
      const publishedText = screen.getByText(/Published:/);
      expect(publishedText).toBeInTheDocument();
      // The date should be formatted (not raw ISO string)
      expect(publishedText.textContent).not.toContain("2026-02-10T14:30:00Z");
    });

    it("shows N/A when published_at is missing", () => {
      const publishedItem: ScheduledItem = {
        ...baseItem,
        status: "published",
        instagram_permalink: "https://www.instagram.com/p/ABC123/",
        // No published_at
      };

      render(<PublishedPostCard item={publishedItem} />);

      // Should not show Published timestamp
      expect(screen.queryByText(/Published:/)).not.toBeInTheDocument();
    });
  });

  describe("Custom styling", () => {
    it("applies custom className", () => {
      const publishedItem: ScheduledItem = {
        ...baseItem,
        status: "published",
      };

      render(
        <PublishedPostCard item={publishedItem} className="custom-class" />
      );

      const card = screen.getByTestId(`published-post-card-${publishedItem.id}`);
      expect(card).toHaveClass("custom-class");
    });
  });
});
