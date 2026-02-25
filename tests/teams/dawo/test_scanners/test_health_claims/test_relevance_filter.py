"""Tests for RelevanceFilter.

Story 6-1, Task 12.4-12.7: Relevance filter tests.
"""

import pytest

import pandas as pd

from teams.dawo.scanners.health_claims.relevance_filter import RelevanceFilter


@pytest.fixture
def filter_with_keywords():
    return RelevanceFilter(
        mushroom_keywords=("beta-glucan", "ganoderma", "reishi"),
        adaptogen_keywords=("ashwagandha", "rhodiola"),
        vitamin_mineral_keywords=("vitamin c", "vitamin d", "calcium"),
    )


@pytest.fixture
def filter_mushroom_only():
    return RelevanceFilter(
        mushroom_keywords=("beta-glucan", "ganoderma"),
    )


class TestRelevanceFilterMatchesMushroom:
    """Test 12.4: Filter matches mushroom keywords."""

    def test_matches_mushroom_in_substance(self, filter_with_keywords, sample_claims_df):
        filtered_df, stats = filter_with_keywords.filter(sample_claims_df)
        relevant = filtered_df[filtered_df["is_relevant"]]
        substances = relevant["substance"].str.lower().tolist()
        assert any("beta-glucan" in s for s in substances)

    def test_matches_ganoderma_in_substance(self, filter_with_keywords, sample_claims_df):
        filtered_df, stats = filter_with_keywords.filter(sample_claims_df)
        relevant = filtered_df[filtered_df["is_relevant"]]
        substances = relevant["substance"].str.lower().tolist()
        assert any("ganoderma" in s for s in substances)

    def test_mushroom_category_assigned(self, filter_with_keywords, sample_claims_df):
        filtered_df, stats = filter_with_keywords.filter(sample_claims_df)
        mushroom_rows = filtered_df[filtered_df["relevance_category"] == "mushroom"]
        assert len(mushroom_rows) > 0

    def test_mushroom_stats(self, filter_with_keywords, sample_claims_df):
        _, stats = filter_with_keywords.filter(sample_claims_df)
        assert stats.mushroom_matches >= 2  # Beta-glucans and Ganoderma


class TestRelevanceFilterMatchesAdaptogen:
    """Test 12.5: Filter matches adaptogen keywords."""

    def test_matches_ashwagandha(self, filter_with_keywords, sample_claims_df):
        filtered_df, stats = filter_with_keywords.filter(sample_claims_df)
        relevant = filtered_df[filtered_df["is_relevant"]]
        substances = relevant["substance"].str.lower().tolist()
        assert any("ashwagandha" in s for s in substances)

    def test_adaptogen_category_assigned(self, filter_with_keywords, sample_claims_df):
        filtered_df, stats = filter_with_keywords.filter(sample_claims_df)
        adaptogen_rows = filtered_df[filtered_df["relevance_category"] == "adaptogen"]
        assert len(adaptogen_rows) > 0


class TestRelevanceFilterReturnsEmpty:
    """Test 12.6: Filter returns empty for irrelevant claims."""

    def test_no_matches_for_unrelated_keywords(self):
        f = RelevanceFilter(mushroom_keywords=("nonexistent_substance_xyz",))
        df = pd.DataFrame({
            "claim_id": ["ID-001"],
            "substance": ["Calcium"],
            "claim_text": ["Calcium for bones"],
            "conditions_of_use": ["800mg"],
            "status": ["Authorised"],
        })
        filtered_df, stats = f.filter(df)
        relevant = filtered_df[filtered_df["is_relevant"]]
        assert len(relevant) == 0
        assert stats.relevant_claims == 0

    def test_empty_dataframe(self, filter_with_keywords):
        df = pd.DataFrame()
        filtered_df, stats = filter_with_keywords.filter(df)
        assert len(filtered_df) == 0
        assert stats.total_claims == 0


class TestRelevanceFilterCategorization:
    """Test 12.7: Filter categorizes matches correctly."""

    def test_vitamin_category(self, filter_with_keywords, sample_claims_df):
        filtered_df, _ = filter_with_keywords.filter(sample_claims_df)
        vitamin_c_row = filtered_df[filtered_df["claim_id"] == "ID-002"]
        # Vitamin C should be relevant
        assert vitamin_c_row["is_relevant"].iloc[0]

    def test_calcium_categorized_as_vitamin_mineral(self, filter_with_keywords, sample_claims_df):
        filtered_df, _ = filter_with_keywords.filter(sample_claims_df)
        calcium_row = filtered_df[filtered_df["claim_id"] == "ID-004"]
        assert calcium_row["is_relevant"].iloc[0]

    def test_case_insensitive_matching(self):
        f = RelevanceFilter(mushroom_keywords=("beta-glucan",))
        df = pd.DataFrame({
            "claim_id": ["ID-001"],
            "substance": ["BETA-GLUCANS FROM OAT"],
            "claim_text": [""],
            "conditions_of_use": [""],
            "status": ["Authorised"],
        })
        filtered_df, stats = f.filter(df)
        assert stats.mushroom_matches == 1

    def test_matches_in_claim_text(self):
        f = RelevanceFilter(mushroom_keywords=("reishi",))
        df = pd.DataFrame({
            "claim_id": ["ID-001"],
            "substance": ["Ganoderma"],
            "claim_text": ["Reishi mushroom extract benefits"],
            "conditions_of_use": [""],
            "status": ["On hold"],
        })
        filtered_df, stats = f.filter(df)
        assert stats.mushroom_matches == 1

    def test_stats_counts(self, filter_with_keywords, sample_claims_df):
        _, stats = filter_with_keywords.filter(sample_claims_df)
        assert stats.total_claims == 5
        assert stats.relevant_claims > 0
        assert stats.mushroom_matches >= 2
        assert stats.adaptogen_matches >= 1
