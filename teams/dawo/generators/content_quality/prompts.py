"""AI Detectability Prompts for Content Quality Scorer.

System and user prompts for LLM-based authenticity analysis.
Uses the 'generate' tier for accurate AI detection.
"""

from teams.dawo.generators.content_quality.schemas import AuthenticityResult


AI_DETECTABILITY_SYSTEM_PROMPT = """You are an AI content authenticity analyzer. Your task is to detect whether content appears to be AI-generated or human-written.

Analyze the content for these AI-generated markers:
1. **Generic Phrasing**: Overused phrases like "in today's fast-paced world", "it's no secret that", "let's dive in", "game-changer", "unlock your potential"
2. **Perfect Structure**: Unnaturally perfect formatting, consistent paragraph lengths, formulaic organization
3. **Vocabulary Patterns**: Limited word variety, repetitive nouns, overuse of filler words
4. **Norwegian AI Markers**: Direct translations like "i dagens moderne verden", "la oss dykke inn i"
5. **Emotional Flatness**: Lack of genuine personality, too polished, missing human quirks

Respond in this EXACT format:
AUTHENTICITY_SCORE: [0-10, where 10 = definitely human, 0 = definitely AI]
AI_PROBABILITY: [0.0-1.0, probability of AI generation]
PATTERNS_DETECTED: [comma-separated list or "none"]
VOCABULARY_DIVERSITY: [0.0-1.0, word variety score]
CONFIDENCE: [0.0-1.0, your confidence in this analysis]
REASONING: [Brief explanation]"""


AI_DETECTABILITY_USER_PROMPT = """Analyze this content for AI-generated characteristics:

---
{content}
---

Provide your analysis in the specified format."""


def parse_authenticity_response(response: str) -> AuthenticityResult:
    """Parse LLM response into AuthenticityResult.

    Args:
        response: Raw LLM response text

    Returns:
        AuthenticityResult parsed from response

    Raises:
        ValueError: If response cannot be parsed
    """
    lines = response.strip().split("\n")
    result_dict = {}

    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().upper().replace(" ", "_")
            value = value.strip()
            result_dict[key] = value

    # Parse values with defaults
    try:
        authenticity_score = float(result_dict.get("AUTHENTICITY_SCORE", "5.0"))
    except ValueError:
        authenticity_score = 5.0

    try:
        ai_probability = float(result_dict.get("AI_PROBABILITY", "0.5"))
    except ValueError:
        ai_probability = 0.5

    try:
        vocabulary_diversity = float(result_dict.get("VOCABULARY_DIVERSITY", "0.5"))
    except ValueError:
        vocabulary_diversity = 0.5

    try:
        confidence = float(result_dict.get("CONFIDENCE", "0.5"))
    except ValueError:
        confidence = 0.5

    # Parse patterns
    patterns_str = result_dict.get("PATTERNS_DETECTED", "none")
    if patterns_str.lower() == "none" or not patterns_str:
        flagged_patterns = []
    else:
        flagged_patterns = [p.strip() for p in patterns_str.split(",") if p.strip()]

    # Clamp values to valid ranges
    authenticity_score = max(0.0, min(10.0, authenticity_score))
    ai_probability = max(0.0, min(1.0, ai_probability))
    vocabulary_diversity = max(0.0, min(1.0, vocabulary_diversity))
    confidence = max(0.0, min(1.0, confidence))

    return AuthenticityResult(
        authenticity_score=authenticity_score,
        ai_probability=ai_probability,
        flagged_patterns=flagged_patterns,
        vocabulary_diversity=vocabulary_diversity,
        analysis_confidence=confidence,
    )
