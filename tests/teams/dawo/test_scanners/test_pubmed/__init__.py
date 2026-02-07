"""Tests for PubMed Scientific Research Scanner.

Tests for the FIFTH scanner in the Harvester Framework:
    Scanner -> Harvester -> FindingSummarizer -> ClaimValidator -> Transformer -> Validator -> Scorer -> Publisher -> Research Pool

UNIQUE to PubMed Scanner:
    - Uses Biopython's Entrez module for NCBI E-utilities
    - Has TWO LLM stages: FindingSummarizer AND ClaimValidator (both tier="generate")
    - Weekly schedule (scientific publications have slower cadence)
    - Scientific metadata extraction: DOI, study type, sample size, authors
"""
