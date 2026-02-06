"""Performance tests for Research Pool queries.

These tests verify AC#2: Queries complete in < 500ms for pools up to 10,000 items.

Note: These are integration tests that require a PostgreSQL database.
They are skipped by default. To run:
    pytest tests/teams/dawo/test_research/test_performance.py --run-integration

Or set environment variable:
    RESEARCH_POOL_DB_URL=postgresql+asyncpg://user:pass@localhost/test_db
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import random

# Mark entire module as integration tests (skipped by default)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(reason="Integration tests require PostgreSQL database"),
]


# Performance thresholds from AC#2
QUERY_TIME_THRESHOLD_MS = 500
ITEM_COUNT = 10_000


def create_test_item(index: int) -> dict:
    """Create test research item data.

    Generates realistic test data with varied sources, tags, and scores.
    """
    sources = ["reddit", "youtube", "instagram", "news", "pubmed"]
    tag_options = [
        ["lions_mane", "cognition"],
        ["reishi", "sleep", "immunity"],
        ["cordyceps", "energy", "athletic"],
        ["chaga", "antioxidant"],
        ["mushrooms", "health", "wellness"],
        ["nootropics", "brain", "focus"],
        ["adaptogens", "stress"],
    ]
    compliance_statuses = ["COMPLIANT", "WARNING", "REJECTED"]

    return {
        "id": uuid4(),
        "source": random.choice(sources),
        "title": f"Research Item {index}: {random.choice(['Study', 'Review', 'Discussion', 'Analysis'])}",
        "content": f"Content for research item {index}. " * 10,
        "url": f"https://example.com/research/{index}",
        "tags": random.choice(tag_options),
        "source_metadata": {
            "author": f"author_{index}",
            "index": index,
            "views": random.randint(100, 100000),
        },
        "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 365)),
        "score": round(random.uniform(0, 10), 1),
        "compliance_status": random.choice(compliance_statuses),
    }


class TestQueryPerformance:
    """Performance tests for Research Pool queries.

    Requires PostgreSQL database with indexes properly configured.
    """

    @pytest.fixture(scope="class")
    async def seeded_pool(self, async_session):
        """Seed database with 10,000 research items."""
        from teams.dawo.research import ResearchPoolRepository, ResearchItemCreate

        repo = ResearchPoolRepository(async_session)

        # Create items in batches for efficiency
        batch_size = 1000
        for batch_start in range(0, ITEM_COUNT, batch_size):
            items = [
                ResearchItemCreate(**create_test_item(i))
                for i in range(batch_start, min(batch_start + batch_size, ITEM_COUNT))
            ]
            await repo.bulk_insert(items)

        return repo

    async def test_query_by_source_under_500ms(self, seeded_pool):
        """AC#2: Query by source completes in < 500ms."""
        from teams.dawo.research import ResearchQueryFilters, ResearchSource

        filters = ResearchQueryFilters(source=ResearchSource.REDDIT, limit=50)

        start = time.perf_counter()
        results = await seeded_pool.query(filters)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < QUERY_TIME_THRESHOLD_MS, (
            f"Query took {elapsed_ms:.1f}ms, expected < {QUERY_TIME_THRESHOLD_MS}ms"
        )
        assert len(results) <= 50

    async def test_query_by_tags_under_500ms(self, seeded_pool):
        """AC#2: Query by tags completes in < 500ms."""
        from teams.dawo.research import ResearchQueryFilters

        filters = ResearchQueryFilters(tags=["lions_mane", "cognition"], limit=50)

        start = time.perf_counter()
        results = await seeded_pool.query(filters)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < QUERY_TIME_THRESHOLD_MS, (
            f"Query took {elapsed_ms:.1f}ms, expected < {QUERY_TIME_THRESHOLD_MS}ms"
        )

    async def test_query_by_score_range_under_500ms(self, seeded_pool):
        """AC#2: Query by score range completes in < 500ms."""
        from teams.dawo.research import ResearchQueryFilters

        filters = ResearchQueryFilters(min_score=7.0, max_score=10.0, limit=50)

        start = time.perf_counter()
        results = await seeded_pool.query(filters)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < QUERY_TIME_THRESHOLD_MS, (
            f"Query took {elapsed_ms:.1f}ms, expected < {QUERY_TIME_THRESHOLD_MS}ms"
        )

    async def test_query_by_date_range_under_500ms(self, seeded_pool):
        """AC#2: Query by date range completes in < 500ms."""
        from teams.dawo.research import ResearchQueryFilters

        filters = ResearchQueryFilters(
            start_date=datetime.now(timezone.utc) - timedelta(days=30),
            end_date=datetime.now(timezone.utc),
            limit=50,
        )

        start = time.perf_counter()
        results = await seeded_pool.query(filters)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < QUERY_TIME_THRESHOLD_MS, (
            f"Query took {elapsed_ms:.1f}ms, expected < {QUERY_TIME_THRESHOLD_MS}ms"
        )

    async def test_combined_filters_under_500ms(self, seeded_pool):
        """AC#2: Combined filters complete in < 500ms."""
        from teams.dawo.research import ResearchQueryFilters, ResearchSource, ComplianceStatus

        filters = ResearchQueryFilters(
            source=ResearchSource.PUBMED,
            min_score=5.0,
            compliance_status=ComplianceStatus.COMPLIANT,
            limit=50,
        )

        start = time.perf_counter()
        results = await seeded_pool.query(filters)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < QUERY_TIME_THRESHOLD_MS, (
            f"Query took {elapsed_ms:.1f}ms, expected < {QUERY_TIME_THRESHOLD_MS}ms"
        )

    async def test_full_text_search_under_500ms(self, seeded_pool):
        """AC#3: Full-text search completes in < 500ms."""
        from teams.dawo.research import ResearchQueryFilters

        filters = ResearchQueryFilters(limit=50)

        start = time.perf_counter()
        results = await seeded_pool.search("research item study", filters)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < QUERY_TIME_THRESHOLD_MS, (
            f"Search took {elapsed_ms:.1f}ms, expected < {QUERY_TIME_THRESHOLD_MS}ms"
        )
