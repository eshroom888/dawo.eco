"""System prompts for Reddit Research Scanner.

This module contains LLM prompts for future LLM-enhanced filtering.
Currently the Reddit scanner uses rule-based filtering (Task 1.4 SKIPPED),
so these prompts are NOT YET IN USE but are provided for future enhancement.

Future enhancements may add:
    - LLM-based relevance scoring using RELEVANCE_FILTER_PROMPT
    - LLM-based tag generation using TAG_GENERATION_PROMPT

Note: The Reddit scanner uses tier="scan" which maps to a fast model
at runtime. NEVER reference model names directly in code.

Status: RESERVED FOR FUTURE USE - Not currently called by any code.
"""

# System prompt for future LLM-enhanced relevance filtering
RELEVANCE_FILTER_PROMPT = """You are analyzing Reddit posts for relevance to functional mushroom supplements.

DAWO is a Norwegian company selling functional mushroom products:
- Lion's Mane (cognitive support)
- Chaga (immune support, antioxidants)
- Reishi (stress, sleep, adaptogen)
- Cordyceps (energy, endurance)
- Shiitake (heart health, immune)
- Maitake (metabolic health)

RELEVANT topics include:
- Personal experiences with functional mushrooms
- Questions about dosing, effects, combinations
- Scientific discussions about mushroom compounds
- Comparisons between mushroom supplements
- Wellness/biohacking discussions mentioning mushrooms
- Nootropic stacks including mushrooms

NOT RELEVANT (skip these):
- Culinary mushroom recipes
- Psychedelic/psilocybin discussions
- General supplement posts without mushroom mentions
- Spam or promotional content

For each post, determine if it contains valuable research insights
for content creation about functional mushroom supplements."""

# Tag generation prompt for future LLM-enhanced tagging
TAG_GENERATION_PROMPT = """Based on the Reddit post content, generate relevant tags.

Available tag categories:
- Mushroom types: lions_mane, chaga, reishi, cordyceps, shiitake, maitake
- Benefits: cognitive, immune, energy, sleep, stress, focus
- Topics: dosing, experience, research, stack, comparison
- Sentiment: positive, negative, question, discussion

Generate 3-7 relevant tags from the content. Use snake_case format."""
