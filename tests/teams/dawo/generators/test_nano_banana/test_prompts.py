"""Unit tests for prompt engineering module."""

import pytest

from teams.dawo.generators.nano_banana.prompts import (
    build_prompt,
    get_negative_prompt,
    get_brand_keywords,
    validate_prompt_length,
    STYLE_TEMPLATES,
    MAX_POSITIVE_PROMPT_LENGTH,
    MAX_NEGATIVE_PROMPT_LENGTH,
)
from teams.dawo.generators.nano_banana.schemas import ImageStyleType


class TestBuildPrompt:
    """Test prompt building."""

    def test_build_prompt_includes_topic(self):
        """Built prompt includes the topic."""
        prompt = build_prompt(
            topic="morning coffee ritual",
            style=ImageStyleType.LIFESTYLE,
        )

        assert "morning coffee ritual" in prompt

    def test_build_prompt_includes_style_prefix(self):
        """Built prompt includes style prefix."""
        prompt = build_prompt(
            topic="test topic",
            style=ImageStyleType.NATURE,
        )

        # Nature style should include Norwegian nature terms
        assert "Norwegian" in prompt or "forest" in prompt or "nature" in prompt.lower()

    def test_build_prompt_includes_brand_keywords(self):
        """Built prompt includes brand keywords."""
        prompt = build_prompt(
            topic="test topic",
            style=ImageStyleType.WELLNESS,
            brand_keywords=["peaceful", "organic"],
        )

        assert "peaceful" in prompt
        assert "organic" in prompt

    def test_build_prompt_includes_mood(self):
        """Built prompt includes mood when provided."""
        prompt = build_prompt(
            topic="test topic",
            style=ImageStyleType.WELLNESS,
            mood="serene and calm",
        )

        assert "serene and calm" in prompt

    def test_build_prompt_natural_aesthetic_suffix(self):
        """Built prompt includes natural aesthetic suffix."""
        prompt = build_prompt(
            topic="test topic",
            style=ImageStyleType.WELLNESS,
        )

        assert "authentic" in prompt.lower() or "organic" in prompt.lower()

    def test_build_prompt_respects_length_limit(self):
        """Built prompt is truncated if too long."""
        # Create very long topic
        long_topic = "very detailed topic " * 100

        prompt = build_prompt(
            topic=long_topic,
            style=ImageStyleType.WELLNESS,
        )

        assert len(prompt) <= MAX_POSITIVE_PROMPT_LENGTH

    def test_build_prompt_all_styles(self):
        """All styles produce valid prompts."""
        for style in ImageStyleType:
            prompt = build_prompt(
                topic="test topic",
                style=style,
            )

            assert len(prompt) > 0
            assert "test topic" in prompt


class TestGetNegativePrompt:
    """Test negative prompt generation."""

    def test_negative_prompt_includes_mushrooms(self):
        """Negative prompt includes mushroom avoidance."""
        negative = get_negative_prompt(ImageStyleType.WELLNESS)

        assert "mushroom" in negative.lower()

    def test_negative_prompt_includes_medical(self):
        """Negative prompt includes medical avoidance."""
        negative = get_negative_prompt(ImageStyleType.WELLNESS)

        assert "medical" in negative.lower()

    def test_negative_prompt_includes_ai_markers(self):
        """Negative prompt includes AI marker avoidance."""
        negative = get_negative_prompt(ImageStyleType.WELLNESS)

        assert "AI generated" in negative or "artificial" in negative

    def test_negative_prompt_includes_additional(self):
        """Negative prompt includes additional elements."""
        negative = get_negative_prompt(
            ImageStyleType.WELLNESS,
            additional_avoid=["pills", "supplements"],
        )

        assert "pills" in negative
        assert "supplements" in negative

    def test_negative_prompt_all_styles(self):
        """All styles produce valid negative prompts."""
        for style in ImageStyleType:
            negative = get_negative_prompt(style)

            assert len(negative) > 0


class TestGetBrandKeywords:
    """Test brand keyword retrieval."""

    def test_brand_keywords_not_empty(self):
        """Brand keywords list is not empty."""
        keywords = get_brand_keywords()

        assert len(keywords) > 0

    def test_brand_keywords_include_nordic(self):
        """Brand keywords include Nordic-related terms."""
        keywords = get_brand_keywords()

        nordic_terms = ["Nordic", "Norwegian", "Scandinavian"]
        has_nordic = any(term in keywords for term in nordic_terms)

        assert has_nordic

    def test_brand_keywords_include_wellness(self):
        """Brand keywords include wellness-related terms."""
        keywords = get_brand_keywords()

        wellness_terms = ["wellness", "natural", "peaceful"]
        has_wellness = any(term in keywords for term in wellness_terms)

        assert has_wellness


class TestValidatePromptLength:
    """Test prompt length validation."""

    def test_valid_prompts_pass(self):
        """Valid length prompts pass validation."""
        prompt = "Short prompt"
        negative = "Short negative"

        is_valid, message = validate_prompt_length(prompt, negative)

        assert is_valid is True

    def test_long_positive_prompt_fails(self):
        """Too long positive prompt fails validation."""
        prompt = "x" * (MAX_POSITIVE_PROMPT_LENGTH + 100)
        negative = "short"

        is_valid, message = validate_prompt_length(prompt, negative)

        assert is_valid is False
        assert "Positive prompt" in message

    def test_long_negative_prompt_fails(self):
        """Too long negative prompt fails validation."""
        prompt = "short"
        negative = "x" * (MAX_NEGATIVE_PROMPT_LENGTH + 100)

        is_valid, message = validate_prompt_length(prompt, negative)

        assert is_valid is False
        assert "Negative prompt" in message


class TestStyleTemplates:
    """Test style template structure."""

    def test_all_styles_have_templates(self):
        """All image styles have defined templates."""
        for style in ImageStyleType:
            assert style in STYLE_TEMPLATES

    def test_templates_have_required_keys(self):
        """All templates have prefix, suffix, and negative keys."""
        for style, template in STYLE_TEMPLATES.items():
            assert "prefix" in template, f"{style} missing prefix"
            assert "suffix" in template, f"{style} missing suffix"
            assert "negative" in template, f"{style} missing negative"

    def test_templates_not_empty(self):
        """All template values are non-empty."""
        for style, template in STYLE_TEMPLATES.items():
            assert len(template["prefix"]) > 0
            assert len(template["suffix"]) > 0
            assert len(template["negative"]) > 0
