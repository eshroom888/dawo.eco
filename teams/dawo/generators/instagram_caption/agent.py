"""Instagram Caption Generator Agent.

Generates Norwegian Instagram captions for DAWO following brand voice guidelines.
Uses 'generate' tier (defaults to Sonnet) for quality content creation.

Configuration is received via dependency injection - NEVER loads config directly.

The generator follows the Content Generator Framework:
1. Accept research item and optional product handle
2. Generate Norwegian caption with LLM
3. Validate against Brand Voice Validator
4. Return result with validation status and suggestions
"""

import logging
import re
import time
from typing import Optional, Protocol, runtime_checkable

# Use direct module imports to avoid circular import issues
from integrations.shopify.client import (
    ShopifyClientProtocol,
    ShopifyProduct,
)
from integrations.shopify.utm import build_utm_url
from teams.dawo.validators.brand_voice.agent import (
    BrandVoiceValidator,
    BrandValidationResult,
    ValidationStatus,
)
from teams.dawo.validators.brand_voice.profile import BrandProfile

from .prompts import (
    CAPTION_SYSTEM_PROMPT,
    CAPTION_USER_PROMPT_TEMPLATE,
    PRODUCT_SECTION_TEMPLATE,
    NO_PRODUCT_SECTION,
    REFINEMENT_PROMPT,
)
from .schemas import CaptionRequest, CaptionResult
from .tools import (
    count_words,
    validate_word_count,
    generate_hashtags,
    validate_hashtags,
    format_research_citation,
    MIN_WORDS,
    MAX_WORDS,
    BRAND_TAGS,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol for LLM client interface.

    Any LLM client implementing this protocol can be used with the generator.
    Compatible with Google ADK, Anthropic SDK, or custom implementations.
    """

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt

        Returns:
            The LLM's response text
        """
        ...


@runtime_checkable
class CaptionGeneratorProtocol(Protocol):
    """Protocol defining the caption generator interface.

    Any class implementing this protocol can be used for caption generation.
    Enables easy mocking and alternative implementations.
    """

    async def generate(self, request: CaptionRequest) -> CaptionResult:
        """Generate an Instagram caption.

        Args:
            request: Caption generation request with research and product data

        Returns:
            CaptionResult with generated caption and validation status
        """
        ...


class CaptionGenerator:
    """Norwegian Instagram Caption Generator for DAWO.

    Generates brand-aligned Norwegian captions following the DAWO voice:
    warm, educational, and Nordic simplicity.

    Uses 'generate' tier (defaults to Sonnet) for quality content creation.

    CRITICAL: Accept config via dependency injection - NEVER load directly.

    Attributes:
        _brand_profile: Brand voice configuration (Norwegian section used)
        _shopify: Shopify client for product data enrichment
        _validator: Brand Voice Validator for caption validation
        _llm_client: LLM client for caption generation
    """

    def __init__(
        self,
        brand_profile: BrandProfile,
        shopify: ShopifyClientProtocol,
        brand_validator: BrandVoiceValidator,
        llm_client: LLMClientProtocol,
    ) -> None:
        """Initialize the caption generator with injected dependencies.

        Args:
            brand_profile: Brand profile configuration (dict with 'norwegian' section).
                          Injected by Team Builder - NEVER load from file directly.
            shopify: Shopify client for product data retrieval.
            brand_validator: Brand Voice Validator for caption validation.
            llm_client: LLM client for generating caption text.

        Raises:
            ValueError: If brand_profile is missing required 'norwegian' section.
        """
        if "norwegian" not in brand_profile:
            raise ValueError("Brand profile must contain 'norwegian' section")

        self._brand_profile = brand_profile
        self._norwegian = brand_profile["norwegian"]
        self._shopify = shopify
        self._validator = brand_validator
        self._llm_client = llm_client

        # Extract Norwegian-specific configuration
        self._caption_guidelines = self._norwegian.get("caption_guidelines", {})
        self._ai_patterns = self._norwegian.get("ai_generic_patterns", [])
        self._forbidden_terms = self._norwegian.get("forbidden_terms", {})

        logger.info("CaptionGenerator initialized with Norwegian brand profile")

    async def generate(self, request: CaptionRequest) -> CaptionResult:
        """Generate an Instagram caption for the given request.

        Follows the Content Generator Framework:
        1. Fetch product data if handle provided
        2. Generate Norwegian caption with LLM
        3. Validate against Brand Voice Validator
        4. Check for AI-generic patterns
        5. Return result with validation status

        Args:
            request: Caption generation request

        Returns:
            CaptionResult with caption, validation status, and any suggestions
        """
        start_time = time.time()

        try:
            # Step 1: Fetch product data if handle provided
            product = None
            product_link = None
            if request.product_handle:
                product = await self._fetch_product(request.product_handle)
                if product:
                    product_link = build_utm_url(
                        base_url=product.product_url,
                        content_type="feed_post",
                        post_id=request.content_id,
                    )

            # Step 2: Generate hashtags
            hashtags = generate_hashtags(
                topic=request.target_topic,
                research_tags=request.research_tags,
            )

            # Step 3: Build prompt and generate caption
            prompt = self._build_prompt(request, product, product_link, hashtags)
            caption_text = await self._llm_client.generate(
                prompt=prompt,
                system=CAPTION_SYSTEM_PROMPT,
            )

            # Step 4: Post-process caption
            caption_text = self._post_process_caption(caption_text)
            word_count = count_words(caption_text)

            # Step 5: Validate word count
            is_valid_length, length_msg = validate_word_count(caption_text)
            if not is_valid_length:
                logger.warning("Caption length validation failed: %s", length_msg)

            # Step 6: Validate brand voice
            validation_result = await self._validate_brand_voice(caption_text)

            # Step 7: Check AI-generic patterns
            authenticity_score = self._calculate_authenticity_score(caption_text)

            # Step 8: Build result
            generation_time_ms = int((time.time() - start_time) * 1000)

            return CaptionResult(
                caption_text=caption_text,
                word_count=word_count,
                hashtags=hashtags,
                product_link=product_link,
                brand_voice_status=validation_result.status.value.upper(),
                brand_voice_score=validation_result.brand_score,
                revision_suggestions=self._extract_suggestions(validation_result),
                authenticity_score=authenticity_score,
                generation_time_ms=generation_time_ms,
                research_citation=format_research_citation(
                    request.research_source,
                    request.research_content,
                ),
                success=True,
            )

        except Exception as e:
            logger.error("Caption generation failed: %s", e)
            return CaptionResult.failure(str(e))

    async def _fetch_product(self, handle: str) -> Optional[ShopifyProduct]:
        """Fetch product data from Shopify.

        Args:
            handle: Product URL handle

        Returns:
            ShopifyProduct if found, None otherwise
        """
        try:
            product = await self._shopify.get_product_by_handle(handle)
            if product:
                logger.debug("Fetched product: %s", product.title)
            else:
                logger.warning("Product not found: %s", handle)
            return product
        except Exception as e:
            logger.error("Failed to fetch product %s: %s", handle, e)
            return None

    def _build_prompt(
        self,
        request: CaptionRequest,
        product: Optional[ShopifyProduct],
        product_link: Optional[str],
        hashtags: list[str],
    ) -> str:
        """Build the user prompt for caption generation.

        Args:
            request: Caption request
            product: Optional product data
            product_link: Optional product URL with UTM params
            hashtags: Generated hashtags

        Returns:
            Formatted user prompt
        """
        # Build product section
        if product:
            product_section = PRODUCT_SECTION_TEMPLATE.format(
                product_name=product.title,
                product_benefits=", ".join(product.benefits) if product.benefits else "Se produktside",
                novel_food_classification=product.novel_food_classification,
                product_link=product_link or product.product_url,
            )
        else:
            product_section = NO_PRODUCT_SECTION

        # Format hashtags for prompt
        hashtags_str = " ".join(hashtags)

        return CAPTION_USER_PROMPT_TEMPLATE.format(
            research_source=request.research_source,
            research_content=request.research_content,
            product_section=product_section,
            target_topic=request.target_topic,
            hashtags=hashtags_str,
        )

    def _post_process_caption(self, caption_text: str) -> str:
        """Clean up and format the generated caption.

        Args:
            caption_text: Raw LLM output

        Returns:
            Cleaned caption text
        """
        # Remove any markdown formatting
        caption_text = re.sub(r"\*\*(.+?)\*\*", r"\1", caption_text)
        caption_text = re.sub(r"__(.+?)__", r"\1", caption_text)

        # Remove any "Hashtags:" or similar prefixes
        caption_text = re.sub(r"(?i)hashtags?:\s*", "", caption_text)

        # Ensure hashtags are on their own line at the end
        lines = caption_text.strip().split("\n")
        text_lines = []
        hashtag_lines = []

        for line in lines:
            if line.strip().startswith("#") or all(
                word.startswith("#") for word in line.split() if word
            ):
                hashtag_lines.append(line.strip())
            else:
                text_lines.append(line)

        # Reconstruct with hashtags at end
        result = "\n".join(text_lines).strip()
        if hashtag_lines:
            result += "\n\n" + " ".join(hashtag_lines)

        return result.strip()

    async def _validate_brand_voice(self, caption_text: str) -> BrandValidationResult:
        """Validate caption against brand voice guidelines.

        Args:
            caption_text: Caption text to validate

        Returns:
            BrandValidationResult with status and issues
        """
        # Use Norwegian profile for validation
        norwegian_profile = {
            "brand_name": self._brand_profile.get("brand_name", "DAWO"),
            "tone_pillars": self._norwegian.get("tone_pillars", {}),
            "forbidden_terms": self._norwegian.get("forbidden_terms", {}),
            "ai_generic_patterns": self._norwegian.get("ai_generic_patterns", []),
            "scoring_thresholds": self._brand_profile.get("scoring_thresholds", {}),
        }

        # Create temporary validator with Norwegian profile
        norwegian_validator = BrandVoiceValidator(norwegian_profile)
        return norwegian_validator.validate_content_sync(caption_text)

    def _calculate_authenticity_score(self, caption_text: str) -> float:
        """Calculate authenticity score based on AI-generic patterns.

        Higher score = more human-like, lower score = more AI-like.

        Args:
            caption_text: Caption text to analyze

        Returns:
            Score between 0.0 and 1.0
        """
        score = 1.0
        caption_lower = caption_text.lower()

        for pattern in self._ai_patterns:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                if regex.search(caption_text):
                    score -= 0.15
                    logger.debug("AI pattern detected: %s", pattern)
            except re.error:
                # If pattern is invalid regex, try literal match
                if pattern.lower() in caption_lower:
                    score -= 0.15

        return max(0.0, min(1.0, score))

    def _extract_suggestions(
        self, validation_result: BrandValidationResult
    ) -> list[str]:
        """Extract revision suggestions from validation result.

        Args:
            validation_result: Brand validation result

        Returns:
            List of suggestion strings
        """
        suggestions = []
        for issue in validation_result.issues:
            if issue.suggestion:
                suggestions.append(f"{issue.phrase}: {issue.suggestion}")
        return suggestions
