"""Tests for PubMed scanner configuration.

Tests config validation, defaults, and dataclass behavior.
"""

import pytest


class TestEntrezConfig:
    """Tests for EntrezConfig dataclass."""

    def test_create_entrez_config_with_api_key(self):
        """Test creating EntrezConfig with API key."""
        from teams.dawo.scanners.pubmed.config import EntrezConfig

        config = EntrezConfig(
            email="researcher@university.edu",
            api_key="ncbi_api_key_12345",
        )
        assert config.email == "researcher@university.edu"
        assert config.api_key == "ncbi_api_key_12345"

    def test_create_entrez_config_without_api_key(self):
        """Test creating EntrezConfig without API key (optional)."""
        from teams.dawo.scanners.pubmed.config import EntrezConfig

        config = EntrezConfig(email="researcher@university.edu")
        assert config.email == "researcher@university.edu"
        assert config.api_key is None

    def test_entrez_config_email_required(self):
        """Test that email is required (NCBI policy)."""
        from teams.dawo.scanners.pubmed.config import EntrezConfig

        with pytest.raises((TypeError, ValueError)):
            EntrezConfig()  # type: ignore

    def test_entrez_config_immutable(self):
        """Test EntrezConfig is immutable (frozen dataclass)."""
        from teams.dawo.scanners.pubmed.config import EntrezConfig

        config = EntrezConfig(email="test@example.com")
        with pytest.raises(Exception):  # FrozenInstanceError
            config.email = "other@example.com"


class TestPubMedScannerConfig:
    """Tests for PubMedScannerConfig dataclass."""

    def test_create_config_minimal(self):
        """Test creating config with minimal required fields."""
        from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

        config = PubMedScannerConfig(email="test@example.com")
        assert config.email == "test@example.com"

    def test_create_config_full(self):
        """Test creating config with all fields."""
        from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

        config = PubMedScannerConfig(
            email="test@example.com",
            api_key="test_key",
            search_queries=["lion's mane cognition"],
            publication_type_filters=["Randomized Controlled Trial"],
            lookback_days=60,
            max_results_per_query=25,
        )
        assert config.email == "test@example.com"
        assert config.api_key == "test_key"
        assert config.search_queries == ["lion's mane cognition"]
        assert config.publication_type_filters == ["Randomized Controlled Trial"]
        assert config.lookback_days == 60
        assert config.max_results_per_query == 25

    def test_default_search_queries(self):
        """Test default search queries are populated."""
        from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

        config = PubMedScannerConfig(email="test@example.com")
        assert len(config.search_queries) > 0
        assert "lion's mane cognition" in config.search_queries

    def test_default_publication_type_filters(self):
        """Test default publication type filters."""
        from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

        config = PubMedScannerConfig(email="test@example.com")
        assert "Randomized Controlled Trial" in config.publication_type_filters
        assert "Meta-Analysis" in config.publication_type_filters
        assert "Review" in config.publication_type_filters

    def test_default_lookback_days(self):
        """Test default lookback days is 90."""
        from teams.dawo.scanners.pubmed.config import (
            PubMedScannerConfig,
            DEFAULT_LOOKBACK_DAYS,
        )

        config = PubMedScannerConfig(email="test@example.com")
        assert config.lookback_days == DEFAULT_LOOKBACK_DAYS
        assert config.lookback_days == 90

    def test_default_max_results_per_query(self):
        """Test default max results per query is 50."""
        from teams.dawo.scanners.pubmed.config import (
            PubMedScannerConfig,
            DEFAULT_MAX_RESULTS_PER_QUERY,
        )

        config = PubMedScannerConfig(email="test@example.com")
        assert config.max_results_per_query == DEFAULT_MAX_RESULTS_PER_QUERY
        assert config.max_results_per_query == 50

    def test_config_validation_invalid_lookback_days(self):
        """Test config validation rejects invalid lookback_days."""
        from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

        with pytest.raises(ValueError) as exc_info:
            PubMedScannerConfig(email="test@example.com", lookback_days=0)
        assert "lookback_days" in str(exc_info.value)

    def test_config_validation_invalid_max_results(self):
        """Test config validation rejects invalid max_results_per_query."""
        from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

        with pytest.raises(ValueError) as exc_info:
            PubMedScannerConfig(email="test@example.com", max_results_per_query=0)
        assert "max_results_per_query" in str(exc_info.value)

    def test_config_validation_empty_email(self):
        """Test config validation rejects empty email."""
        from teams.dawo.scanners.pubmed.config import PubMedScannerConfig

        with pytest.raises(ValueError) as exc_info:
            PubMedScannerConfig(email="")
        assert "email" in str(exc_info.value).lower()


class TestConfigConstants:
    """Tests for configuration constants."""

    def test_default_lookback_days_constant(self):
        """Test DEFAULT_LOOKBACK_DAYS constant."""
        from teams.dawo.scanners.pubmed.config import DEFAULT_LOOKBACK_DAYS

        assert DEFAULT_LOOKBACK_DAYS == 90

    def test_default_max_results_per_query_constant(self):
        """Test DEFAULT_MAX_RESULTS_PER_QUERY constant."""
        from teams.dawo.scanners.pubmed.config import DEFAULT_MAX_RESULTS_PER_QUERY

        assert DEFAULT_MAX_RESULTS_PER_QUERY == 50

    def test_default_batch_size_constant(self):
        """Test DEFAULT_BATCH_SIZE constant (NCBI limit is 200)."""
        from teams.dawo.scanners.pubmed.config import DEFAULT_BATCH_SIZE

        assert DEFAULT_BATCH_SIZE == 200

    def test_rate_limit_no_key_constant(self):
        """Test rate limit without API key (3 req/sec per NCBI)."""
        from teams.dawo.scanners.pubmed.config import RATE_LIMIT_NO_KEY

        assert RATE_LIMIT_NO_KEY == 3

    def test_rate_limit_with_key_constant(self):
        """Test rate limit with API key (10 req/sec per NCBI)."""
        from teams.dawo.scanners.pubmed.config import RATE_LIMIT_WITH_KEY

        assert RATE_LIMIT_WITH_KEY == 10
