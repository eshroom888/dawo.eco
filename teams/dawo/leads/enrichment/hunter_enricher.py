"""Hunter.io Extended Enrichment for Lead Enrichment.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 4: Implement Hunter.io Extended Enrichment

Reuses HunterClient from Story 5-1 to provide:
- Company enrichment (organization, headcount, industry)
- Decision maker discovery (owners, CEOs, buyers)
- Email verification
- API usage tracking
"""

import logging
from typing import Any, Optional, Protocol

from teams.dawo.leads.scanner.schemas import HarvestedContact
from teams.dawo.leads.scanner.tools import HunterAPIError
from teams.dawo.leads.enrichment.schemas import CompanyEnrichment


logger = logging.getLogger(__name__)


# Decision-maker positions to prioritize
DECISION_MAKER_POSITIONS = [
    "owner",
    "ceo",
    "chief executive",
    "founder",
    "co-founder",
    "director",
    "manager",
    "buyer",
    "purchasing",
    "procurement",
    "innkjøp",  # Norwegian: purchasing
    "daglig leder",  # Norwegian: general manager
    "eier",  # Norwegian: owner
]


class HunterClientProtocol(Protocol):
    """Protocol for Hunter.io client dependency injection."""

    async def domain_search(
        self,
        domain: str,
        department: Optional[str] = None,
        seniority: Optional[str] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search for emails at a domain."""
        ...

    async def email_verifier(self, email: str) -> dict[str, Any]:
        """Verify if an email is deliverable."""
        ...


class HunterEnricher:
    """Hunter.io extended enrichment for leads.

    Reuses HunterClient from Story 5-1 via dependency injection.
    Provides company enrichment, decision maker discovery,
    and email verification.

    Tracks API usage for budget monitoring.

    Attributes:
        _client: Hunter.io client
        _domain_searches: Count of domain search API calls
        _verifications: Count of email verification API calls
    """

    def __init__(self, hunter_client: HunterClientProtocol) -> None:
        """Initialize the Hunter.io enricher.

        Args:
            hunter_client: HunterClient instance from Story 5-1
        """
        self._client = hunter_client
        self._domain_searches = 0
        self._verifications = 0

    async def enrich_company(self, domain: str) -> CompanyEnrichment:
        """Enrich company data from Hunter.io.

        Calls domain_search to get:
        - Organization name
        - Headcount/employee count
        - Industry classification
        - Email patterns

        Args:
            domain: Company domain (e.g., "healthstore.no")

        Returns:
            CompanyEnrichment with company data
        """
        self._domain_searches += 1

        try:
            data = await self._client.domain_search(domain, limit=20)

            # Extract email patterns
            emails = data.get("emails", [])
            email_patterns = [e.get("value") for e in emails if e.get("value")]

            return CompanyEnrichment(
                domain=domain,
                organization=data.get("organization") or data.get("company"),
                headcount=data.get("headcount"),
                industry=data.get("industry"),
                email_patterns=email_patterns,
            )

        except HunterAPIError as e:
            logger.warning(f"Hunter.io enrichment failed for {domain}: {e}")
            return CompanyEnrichment(domain=domain)

        except Exception as e:
            logger.error(f"Unexpected error enriching {domain}: {e}")
            return CompanyEnrichment(domain=domain)

    async def find_decision_makers(
        self,
        domain: str,
    ) -> list[HarvestedContact]:
        """Find decision-maker contacts at a company.

        Filters contacts by position to prioritize:
        - Owners, CEOs, Founders
        - Directors, Managers
        - Buyers, Purchasing

        Results are sorted by confidence score (highest first).

        Args:
            domain: Company domain

        Returns:
            List of HarvestedContact for decision makers
        """
        self._domain_searches += 1

        try:
            data = await self._client.domain_search(
                domain,
                seniority="senior",
                limit=20,
            )

            emails = data.get("emails", [])
            decision_makers = []

            for email_data in emails:
                position = (email_data.get("position") or "").lower()

                # Check if position matches decision-maker criteria
                is_decision_maker = any(
                    dm_pos in position for dm_pos in DECISION_MAKER_POSITIONS
                )

                if is_decision_maker:
                    contact = HarvestedContact(
                        email=email_data.get("value", ""),
                        first_name=email_data.get("first_name"),
                        last_name=email_data.get("last_name"),
                        position=email_data.get("position"),
                        department=email_data.get("department"),
                        linkedin=email_data.get("linkedin"),
                        phone=email_data.get("phone_number"),
                        confidence=float(email_data.get("confidence", 0)),
                    )
                    decision_makers.append(contact)

            # Sort by confidence (highest first)
            decision_makers.sort(key=lambda c: c.confidence, reverse=True)

            return decision_makers

        except HunterAPIError as e:
            logger.warning(f"Hunter.io decision maker search failed for {domain}: {e}")
            return []

        except Exception as e:
            logger.error(f"Unexpected error finding decision makers for {domain}: {e}")
            return []

    async def verify_contacts(
        self,
        contacts: list[HarvestedContact],
    ) -> list[HarvestedContact]:
        """Verify email addresses for a list of contacts.

        Filters to only include deliverable emails.

        Args:
            contacts: List of contacts to verify

        Returns:
            List of contacts with verified/deliverable emails
        """
        verified = []

        for contact in contacts:
            self._verifications += 1

            try:
                result = await self._client.email_verifier(contact.email)

                # Check if email is deliverable
                status = result.get("status", "").lower()
                delivery_result = result.get("result", "").lower()

                if status == "valid" or delivery_result == "deliverable":
                    # Update confidence with verification score
                    verification_score = result.get("score", contact.confidence)
                    contact.confidence = float(verification_score)
                    verified.append(contact)
                else:
                    logger.debug(f"Email {contact.email} not deliverable: {status}")

            except HunterAPIError as e:
                logger.warning(f"Email verification failed for {contact.email}: {e}")
                continue

            except Exception as e:
                logger.error(f"Unexpected error verifying {contact.email}: {e}")
                continue

        return verified

    def get_usage_stats(self) -> dict[str, int]:
        """Get API usage statistics.

        Returns:
            Dict with domain_searches and verifications counts
        """
        return {
            "domain_searches": self._domain_searches,
            "verifications": self._verifications,
        }

    def reset_usage_stats(self) -> None:
        """Reset API usage counters."""
        self._domain_searches = 0
        self._verifications = 0
