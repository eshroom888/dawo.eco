"""Tests for Email Signature Builder.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 5: Email Signature Builder
"""

import pytest

from teams.dawo.leads.gmail.signature import SignatureBuilder
from teams.dawo.leads.gmail.config import GmailConfig


@pytest.fixture
def gmail_config() -> GmailConfig:
    """Provide Gmail config for testing."""
    return GmailConfig(
        sender_email="erik@dawo.no",
        sender_name="Erik Hansen",
        sender_role="B2B Sales Manager",
        company_name="ImagoEco AS",
        company_address="Storgata 1, 0155 Oslo, Norway",
    )


@pytest.fixture
def signature_builder(gmail_config: GmailConfig) -> SignatureBuilder:
    """Provide SignatureBuilder with test config."""
    return SignatureBuilder(config=gmail_config)


class TestBuildSignature:
    """Tests for signature building."""

    def test_signature_contains_sender_name(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test signature includes sender name."""
        sig = signature_builder.build_signature()
        assert "Erik Hansen" in sig

    def test_signature_contains_role(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test signature includes sender role."""
        sig = signature_builder.build_signature()
        assert "B2B Sales Manager" in sig

    def test_signature_contains_company(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test signature includes company name."""
        sig = signature_builder.build_signature()
        assert "ImagoEco AS" in sig
        assert "DAWO" in sig

    def test_signature_contains_address(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test signature includes company address."""
        sig = signature_builder.build_signature()
        assert "Storgata 1, 0155 Oslo" in sig

    def test_signature_contains_email(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test signature includes sender email."""
        sig = signature_builder.build_signature()
        assert "erik@dawo.no" in sig


class TestBuildGDPRFooter:
    """Tests for GDPR footer building."""

    def test_gdpr_footer_norwegian_text(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test GDPR footer is in Norwegian."""
        footer = signature_builder.build_gdpr_footer()
        assert "Hvorfor mottok du denne e-posten?" in footer

    def test_gdpr_footer_contains_explanation(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test GDPR footer explains why email was received."""
        footer = signature_builder.build_gdpr_footer()
        assert "DAWO-produktene" in footer

    def test_gdpr_footer_default_unsubscribe(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test GDPR footer has reply-based unsubscribe by default."""
        footer = signature_builder.build_gdpr_footer()
        assert "avmeld" in footer

    def test_gdpr_footer_with_unsubscribe_url(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test GDPR footer with explicit unsubscribe URL."""
        footer = signature_builder.build_gdpr_footer(
            unsubscribe_url="https://dawo.no/unsubscribe?id=123"
        )
        assert "https://dawo.no/unsubscribe?id=123" in footer

    def test_gdpr_footer_contains_company_identity(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test GDPR footer identifies the company."""
        footer = signature_builder.build_gdpr_footer()
        assert "ImagoEco AS" in footer


class TestBuildFullFooter:
    """Tests for combined signature + GDPR footer."""

    def test_full_footer_combines_both(
        self, signature_builder: SignatureBuilder
    ) -> None:
        """Test full footer contains both signature and GDPR footer."""
        full = signature_builder.build_full_footer()
        assert "Erik Hansen" in full  # Signature
        assert "Hvorfor mottok du denne e-posten?" in full  # GDPR
