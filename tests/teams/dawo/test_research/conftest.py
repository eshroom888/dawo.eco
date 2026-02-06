"""Pytest fixtures for Research Pool tests.

Provides database session fixtures, test data factories, and
seeding utilities for research module testing.
"""

import pytest


# =============================================================================
# Pytest Marker Registration
# =============================================================================

def pytest_configure(config):
    """Register custom pytest markers for research tests."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (may be slower)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
import pytest_asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from core.models import Base
from teams.dawo.research.models import ResearchItem, ResearchSource, ComplianceStatus


# Test database URL - in-memory SQLite for unit tests
# Note: SQLite doesn't support all PostgreSQL features (ARRAY, JSONB, TSVECTOR)
# For full integration tests, use PostgreSQL test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    """Create async database engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session for tests."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


def create_test_research_item(
    index: int = 0,
    source: ResearchSource = ResearchSource.REDDIT,
    score: float = 5.0,
    compliance_status: ComplianceStatus = ComplianceStatus.COMPLIANT,
    tags: list[str] | None = None,
) -> dict:
    """Factory function to create test research item data.

    Args:
        index: Unique index for generating distinct data
        source: Research source type
        score: Content potential score (0-10)
        compliance_status: Compliance check status
        tags: Optional list of tags

    Returns:
        Dictionary of research item attributes
    """
    return {
        "id": uuid4(),
        "source": source.value,
        "title": f"Test Research Item {index}",
        "content": f"This is test content for research item {index}. It contains useful information.",
        "url": f"https://example.com/research/{index}",
        "tags": tags or ["test", "research"],
        "source_metadata": {"author": f"test_author_{index}", "index": index},
        "created_at": datetime.now(timezone.utc),
        "score": score,
        "compliance_status": compliance_status.value,
    }


@pytest.fixture
def sample_research_data() -> list[dict]:
    """Provide sample research item data for tests."""
    return [
        create_test_research_item(0, ResearchSource.REDDIT, 8.5, tags=["lions_mane", "cognition"]),
        create_test_research_item(1, ResearchSource.YOUTUBE, 7.0, tags=["reishi", "sleep"]),
        create_test_research_item(2, ResearchSource.PUBMED, 9.5, tags=["lions_mane", "ngt"]),
        create_test_research_item(3, ResearchSource.NEWS, 6.0, tags=["cordyceps", "energy"]),
        create_test_research_item(4, ResearchSource.INSTAGRAM, 5.5, tags=["chaga", "immunity"]),
    ]
