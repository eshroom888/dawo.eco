"""Tests for PubMed Scanner stage.

Tests the PubMedScanner class with mocked PubMed client.
"""

import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch


# Create mock Bio module for testing
@pytest.fixture(autouse=True)
def mock_bio_module():
    """Mock Bio module for all tests."""
    mock_entrez = MagicMock()
    mock_entrez.email = None
    mock_entrez.api_key = None
    mock_entrez.tool = None

    mock_bio = MagicMock()
    mock_bio.Entrez = mock_entrez

    with patch.dict(sys.modules, {"Bio": mock_bio, "Bio.Entrez": mock_entrez}):
        yield mock_entrez


class TestPubMedScanner:
    """Tests for PubMedScanner class."""

    @pytest.fixture
    def scanner_config(self):
        """Create test scanner config."""
        from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

        return PubMedScannerConfig(
            email="test@example.com",
            api_key="test_api_key",
            search_queries=["lion's mane cognition", "Hericium erinaceus"],
            publication_type_filters=["Randomized Controlled Trial"],
            lookback_days=90,
            max_results_per_query=10,
        )

    @pytest.fixture
    def mock_pubmed_client(self):
        """Create mock PubMed client."""
        client = AsyncMock()
        client.search = AsyncMock(return_value=["12345678", "87654321"])
        client.fetch_details = AsyncMock(
            return_value=[
                {
                    "pmid": "12345678",
                    "title": "Test Article 1",
                    "abstract": "Test abstract 1",
                    "authors": ["Smith J"],
                    "journal": "Test Journal",
                    "pub_date": None,
                    "doi": "10.1000/test1",
                    "publication_types": ["Randomized Controlled Trial"],
                },
                {
                    "pmid": "87654321",
                    "title": "Test Article 2",
                    "abstract": "Test abstract 2",
                    "authors": ["Doe A"],
                    "journal": "Another Journal",
                    "pub_date": None,
                    "doi": "10.1000/test2",
                    "publication_types": ["Meta-Analysis"],
                },
            ]
        )
        return client

    def test_scanner_initialization(self, scanner_config, mock_pubmed_client):
        """Test PubMedScanner initializes correctly."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)
        assert scanner._config == scanner_config
        assert scanner._client == mock_pubmed_client

    @pytest.mark.asyncio
    async def test_scan_returns_scan_result(self, scanner_config, mock_pubmed_client):
        """Test scan returns ScanResult with articles."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner
        from teams.dawo.scanners.pubmed.schemas import ScanResult

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)
        result = await scanner.scan()

        assert isinstance(result, ScanResult)
        assert len(result.articles) == 2
        assert result.statistics.queries_executed == 2

    @pytest.mark.asyncio
    async def test_scan_executes_all_queries(self, scanner_config, mock_pubmed_client):
        """Test scan executes all configured search queries."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)
        await scanner.scan()

        # Should call search twice (2 queries)
        assert mock_pubmed_client.search.call_count == 2

    @pytest.mark.asyncio
    async def test_scan_applies_filters(self, scanner_config, mock_pubmed_client):
        """Test scan applies date and publication type filters."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)
        await scanner.scan()

        # Verify filters were passed to search
        call_kwargs = mock_pubmed_client.search.call_args_list[0][1]
        assert call_kwargs["date_filter"] == 90
        assert call_kwargs["publication_types"] == ["Randomized Controlled Trial"]

    @pytest.mark.asyncio
    async def test_scan_deduplicates_pmids(self, scanner_config, mock_pubmed_client):
        """Test scan deduplicates PMIDs across queries."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner

        # Same PMIDs returned for both queries
        mock_pubmed_client.search = AsyncMock(return_value=["12345678", "87654321"])

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)
        result = await scanner.scan()

        # Should deduplicate - 4 total PMIDs but only 2 unique
        assert result.statistics.total_pmids_found == 4
        assert result.statistics.pmids_after_dedup == 2

    @pytest.mark.asyncio
    async def test_scan_tracks_statistics(self, scanner_config, mock_pubmed_client):
        """Test scan tracks execution statistics."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)
        result = await scanner.scan()

        stats = result.statistics
        assert stats.queries_executed == 2
        assert stats.total_pmids_found == 4  # 2 queries * 2 PMIDs each
        assert stats.pmids_after_dedup == 2  # Deduplicated
        assert stats.queries_failed == 0

    @pytest.mark.asyncio
    async def test_scan_handles_query_failures(self, scanner_config, mock_pubmed_client):
        """Test scan continues when some queries fail."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner
        from teams.dawo.scanners.pubmed.tools import PubMedSearchError

        # First query succeeds, second fails
        mock_pubmed_client.search = AsyncMock(
            side_effect=[
                ["12345678"],
                PubMedSearchError("Query failed", "test query"),
            ]
        )

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)
        result = await scanner.scan()

        assert result.statistics.queries_executed == 1
        assert result.statistics.queries_failed == 1
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_scan_raises_when_all_queries_fail(self, scanner_config, mock_pubmed_client):
        """Test scan raises PubMedScanError when all queries fail."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner, PubMedScanError
        from teams.dawo.scanners.pubmed.tools import PubMedSearchError

        mock_pubmed_client.search = AsyncMock(
            side_effect=PubMedSearchError("All queries failed", "test")
        )

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)

        with pytest.raises(PubMedScanError) as exc_info:
            await scanner.scan()

        assert "All" in str(exc_info.value)
        assert "failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_scan_returns_raw_pubmed_articles(self, scanner_config, mock_pubmed_client):
        """Test scan returns list of RawPubMedArticle objects."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner
        from teams.dawo.scanners.pubmed.schemas import RawPubMedArticle

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)
        result = await scanner.scan()

        for article in result.articles:
            assert isinstance(article, RawPubMedArticle)
            assert article.pmid is not None
            assert article.title is not None

    @pytest.mark.asyncio
    async def test_scan_single_query(self, scanner_config, mock_pubmed_client):
        """Test scan_single_query executes single query."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)
        result = await scanner.scan_single_query("lion's mane cognition")

        assert result.statistics.queries_executed == 1
        mock_pubmed_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_single_query_handles_failure(self, scanner_config, mock_pubmed_client):
        """Test scan_single_query returns result with error on failure."""
        from teams.dawo.scanners.pubmed.agent import PubMedScanner
        from teams.dawo.scanners.pubmed.tools import PubMedSearchError

        mock_pubmed_client.search = AsyncMock(
            side_effect=PubMedSearchError("Query failed", "test")
        )

        scanner = PubMedScanner(scanner_config, mock_pubmed_client)
        result = await scanner.scan_single_query("test query")

        assert result.statistics.queries_failed == 1
        assert len(result.errors) == 1
        assert len(result.articles) == 0


class TestPubMedScannerLogging:
    """Tests for scanner logging behavior."""

    @pytest.fixture
    def scanner_config(self):
        """Create test scanner config."""
        from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

        return PubMedScannerConfig(
            email="test@example.com",
            search_queries=["test query"],
        )

    @pytest.fixture
    def mock_pubmed_client(self):
        """Create mock PubMed client."""
        client = AsyncMock()
        client.search = AsyncMock(return_value=["12345678"])
        client.fetch_details = AsyncMock(
            return_value=[
                {
                    "pmid": "12345678",
                    "title": "Test",
                    "abstract": "",
                    "authors": [],
                    "journal": "",
                    "pub_date": None,
                    "doi": None,
                    "publication_types": [],
                }
            ]
        )
        return client

    @pytest.mark.asyncio
    async def test_scan_logs_start_info(self, scanner_config, mock_pubmed_client, caplog):
        """Test scan logs start information."""
        import logging
        from teams.dawo.scanners.pubmed.agent import PubMedScanner

        with caplog.at_level(logging.INFO):
            scanner = PubMedScanner(scanner_config, mock_pubmed_client)
            await scanner.scan()

        assert "Starting PubMed scan" in caplog.text

    @pytest.mark.asyncio
    async def test_scan_logs_completion(self, scanner_config, mock_pubmed_client, caplog):
        """Test scan logs completion information."""
        import logging
        from teams.dawo.scanners.pubmed.agent import PubMedScanner

        with caplog.at_level(logging.INFO):
            scanner = PubMedScanner(scanner_config, mock_pubmed_client)
            await scanner.scan()

        assert "PubMed scan complete" in caplog.text
