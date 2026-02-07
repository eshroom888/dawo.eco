"""Tests for PubMed Entrez client.

Tests the PubMedClient class with mocked Entrez API responses.
Tests are designed to work without Biopython installed by mocking the module.
"""

import pytest
import sys
from datetime import datetime, timezone, timedelta
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


class TestPubMedClient:
    """Tests for PubMedClient class."""

    @pytest.fixture
    def entrez_config(self):
        """Create test Entrez config."""
        from teams.dawo.scanners.pubmed.config import EntrezConfig

        return EntrezConfig(
            email="test@example.com",
            api_key="test_api_key",
        )

    @pytest.fixture
    def retry_middleware(self):
        """Create mock retry middleware."""
        return MagicMock()

    def test_client_initialization(self, entrez_config, retry_middleware, mock_bio_module):
        """Test PubMedClient initializes correctly."""
        from teams.dawo.scanners.pubmed.tools import PubMedClient, RATE_LIMIT_WITH_KEY

        client = PubMedClient(entrez_config, retry_middleware)
        assert client._config == entrez_config
        assert client._retry == retry_middleware
        assert client._rate_limit == RATE_LIMIT_WITH_KEY

    def test_client_rate_limit_without_api_key(self, retry_middleware, mock_bio_module):
        """Test rate limit is lower without API key."""
        from teams.dawo.scanners.pubmed.config import EntrezConfig
        from teams.dawo.scanners.pubmed.tools import PubMedClient, RATE_LIMIT_NO_KEY

        config = EntrezConfig(email="test@example.com")  # No API key

        client = PubMedClient(config, retry_middleware)
        assert client._rate_limit == RATE_LIMIT_NO_KEY

    @pytest.mark.asyncio
    async def test_search_returns_pmids(self, entrez_config, retry_middleware, mock_bio_module):
        """Test search returns list of PMIDs."""
        from teams.dawo.scanners.pubmed.tools import PubMedClient

        client = PubMedClient(entrez_config, retry_middleware)

        # Mock Entrez.esearch and Entrez.read
        mock_handle = MagicMock()
        mock_bio_module.esearch.return_value = mock_handle
        mock_bio_module.read.return_value = {
            "IdList": ["12345678", "87654321", "11111111"]
        }

        pmids = await client.search("lion's mane cognition")

        assert pmids == ["12345678", "87654321", "11111111"]
        mock_bio_module.esearch.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_date_filter(self, entrez_config, retry_middleware, mock_bio_module):
        """Test search includes date filter in query."""
        from teams.dawo.scanners.pubmed.tools import PubMedClient

        client = PubMedClient(entrez_config, retry_middleware)

        mock_handle = MagicMock()
        mock_bio_module.esearch.return_value = mock_handle
        mock_bio_module.read.return_value = {"IdList": ["12345678"]}

        await client.search("test query", date_filter=90)

        # Verify esearch was called with date in term
        call_kwargs = mock_bio_module.esearch.call_args[1]
        assert "PDAT" in call_kwargs["term"]

    @pytest.mark.asyncio
    async def test_search_with_publication_types(self, entrez_config, retry_middleware, mock_bio_module):
        """Test search includes publication type filter."""
        from teams.dawo.scanners.pubmed.tools import PubMedClient

        client = PubMedClient(entrez_config, retry_middleware)

        mock_handle = MagicMock()
        mock_bio_module.esearch.return_value = mock_handle
        mock_bio_module.read.return_value = {"IdList": ["12345678"]}

        await client.search(
            "test query",
            publication_types=["Randomized Controlled Trial"],
        )

        call_kwargs = mock_bio_module.esearch.call_args[1]
        assert "Publication Type" in call_kwargs["term"]

    @pytest.mark.asyncio
    async def test_search_error_raises_exception(self, entrez_config, retry_middleware, mock_bio_module):
        """Test search raises PubMedSearchError on failure."""
        from teams.dawo.scanners.pubmed.tools import PubMedClient, PubMedSearchError

        client = PubMedClient(entrez_config, retry_middleware)

        mock_bio_module.esearch.side_effect = Exception("API error")

        with pytest.raises(PubMedSearchError) as exc_info:
            await client.search("test query")

        assert "Search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_details_returns_articles(self, entrez_config, retry_middleware, mock_bio_module):
        """Test fetch_details returns parsed articles."""
        from teams.dawo.scanners.pubmed.tools import PubMedClient

        client = PubMedClient(entrez_config, retry_middleware)

        # Create mock DOI object with attributes
        mock_doi = MagicMock()
        mock_doi.attributes = {"IdType": "doi"}
        mock_doi.__str__ = lambda x: "10.1000/test"

        # Mock article data
        mock_article = {
            "MedlineCitation": {
                "PMID": "12345678",
                "Article": {
                    "ArticleTitle": "Test Article Title",
                    "Abstract": {"AbstractText": ["Test abstract text"]},
                    "AuthorList": [
                        {"LastName": "Smith", "ForeName": "John"},
                    ],
                    "Journal": {
                        "Title": "Test Journal",
                        "JournalIssue": {
                            "PubDate": {"Year": "2026", "Month": "Jan"}
                        },
                    },
                    "ArticleDate": [
                        {"Year": "2026", "Month": "01", "Day": "15"}
                    ],
                    "PublicationTypeList": ["Randomized Controlled Trial"],
                },
            },
            "PubmedData": {
                "ArticleIdList": [mock_doi],
            },
        }

        mock_handle = MagicMock()
        mock_bio_module.efetch.return_value = mock_handle
        mock_bio_module.read.return_value = {"PubmedArticle": [mock_article]}

        articles = await client.fetch_details(["12345678"])

        assert len(articles) == 1
        assert articles[0]["pmid"] == "12345678"
        assert articles[0]["title"] == "Test Article Title"

    @pytest.mark.asyncio
    async def test_fetch_details_empty_list(self, entrez_config, retry_middleware, mock_bio_module):
        """Test fetch_details returns empty list for empty input."""
        from teams.dawo.scanners.pubmed.tools import PubMedClient

        client = PubMedClient(entrez_config, retry_middleware)

        articles = await client.fetch_details([])
        assert articles == []

    @pytest.mark.asyncio
    async def test_fetch_details_batching(self, entrez_config, retry_middleware, mock_bio_module):
        """Test fetch_details batches large PMID lists."""
        from teams.dawo.scanners.pubmed.tools import PubMedClient

        client = PubMedClient(entrez_config, retry_middleware)

        # Create list of 250 PMIDs (should result in 2 batches of 200 + 50)
        pmids = [str(i) for i in range(250)]

        mock_handle = MagicMock()
        mock_bio_module.efetch.return_value = mock_handle
        mock_bio_module.read.return_value = {"PubmedArticle": []}

        await client.fetch_details(pmids, batch_size=200)

        # Should be called twice (batch 1: 200, batch 2: 50)
        assert mock_bio_module.efetch.call_count == 2


class TestExtractSampleSize:
    """Tests for sample size extraction utility."""

    def test_extract_n_equals_format(self):
        """Test extraction of n=77 format."""
        from teams.dawo.scanners.pubmed.tools import extract_sample_size

        abstract = "A total of 77 participants (n=77) were enrolled."
        assert extract_sample_size(abstract) == 77

    def test_extract_participants_format(self):
        """Test extraction of '77 participants' format."""
        from teams.dawo.scanners.pubmed.tools import extract_sample_size

        abstract = "The study included 120 participants randomized to groups."
        assert extract_sample_size(abstract) == 120

    def test_extract_subjects_format(self):
        """Test extraction of '50 subjects' format."""
        from teams.dawo.scanners.pubmed.tools import extract_sample_size

        abstract = "50 subjects were recruited for the trial."
        assert extract_sample_size(abstract) == 50

    def test_extract_sample_of_format(self):
        """Test extraction of 'sample of 100' format."""
        from teams.dawo.scanners.pubmed.tools import extract_sample_size

        abstract = "We recruited a sample of 100 volunteers."
        assert extract_sample_size(abstract) == 100

    def test_extract_none_when_missing(self):
        """Test returns None when no sample size found."""
        from teams.dawo.scanners.pubmed.tools import extract_sample_size

        abstract = "This is a review article about lion's mane."
        assert extract_sample_size(abstract) is None


class TestClassifyStudyType:
    """Tests for study type classification."""

    def test_classify_rct(self):
        """Test RCT classification."""
        from teams.dawo.scanners.pubmed.tools import classify_study_type

        pub_types = ["Randomized Controlled Trial", "Journal Article"]
        assert classify_study_type(pub_types) == "rct"

    def test_classify_meta_analysis(self):
        """Test meta-analysis classification."""
        from teams.dawo.scanners.pubmed.tools import classify_study_type

        pub_types = ["Meta-Analysis", "Journal Article"]
        assert classify_study_type(pub_types) == "meta_analysis"

    def test_classify_systematic_review(self):
        """Test systematic review classification."""
        from teams.dawo.scanners.pubmed.tools import classify_study_type

        pub_types = ["Systematic Review", "Journal Article"]
        assert classify_study_type(pub_types) == "systematic_review"

    def test_classify_review(self):
        """Test review classification."""
        from teams.dawo.scanners.pubmed.tools import classify_study_type

        pub_types = ["Review", "Journal Article"]
        assert classify_study_type(pub_types) == "review"

    def test_classify_other(self):
        """Test other classification for unknown types."""
        from teams.dawo.scanners.pubmed.tools import classify_study_type

        pub_types = ["Journal Article", "Comment"]
        assert classify_study_type(pub_types) == "other"

    def test_classify_priority_order(self):
        """Test RCT takes priority over review when both present."""
        from teams.dawo.scanners.pubmed.tools import classify_study_type

        # If both RCT and Review are present, first match wins
        pub_types = ["Randomized Controlled Trial", "Review"]
        assert classify_study_type(pub_types) == "rct"
