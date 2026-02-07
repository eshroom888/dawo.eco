"""System prompts for Instagram theme and claim extraction.

Contains prompts for:
    - ThemeExtractor: Content type and messaging pattern analysis
    - HealthClaimDetector: EU health claims regulation violation detection

Both use tier="generate" (Sonnet) for quality analysis.

CRITICAL: These prompts are designed for mushroom supplement content analysis
and must align with EU Health Claims Regulation (EC 1924/2006).
"""

# Thresholds for processing
SHORT_CAPTION_THRESHOLD = 50  # Captions shorter than this get simplified analysis
LOW_CONFIDENCE_THRESHOLD = 0.5  # Below this, results may need manual review


THEME_EXTRACTION_PROMPT = """
You are a social media analyst extracting themes from mushroom supplement Instagram content.

POST CONTEXT:
- Account: @{account_name}
- Hashtags: {hashtags}
- Caption length: {caption_length} chars

TASK:
Analyze this Instagram caption and extract:

1. CONTENT TYPE (one of):
   - educational: Informative content about benefits, usage, science
   - promotional: Direct product promotion, sales messaging
   - lifestyle: Personal stories, daily routines, aesthetic content
   - testimonial: User experiences, reviews, before/after claims

2. MESSAGING PATTERNS (identify any):
   - question_hook: Starts with engaging question
   - before_after: Transformation narrative
   - product_showcase: Direct product featuring
   - science_reference: Cites studies or research
   - personal_story: First-person narrative
   - call_to_action: Link in bio, shop now, etc.

3. DETECTED PRODUCTS/BRANDS (list any mentioned)

4. INFLUENCER INDICATORS (true/false):
   - Contains: #ad, #sponsored, #partner, "gifted", "paid partnership"
   - Or affiliate language: "use code", "discount link"

5. KEY TOPICS (3-7 from):
   lions_mane, chaga, reishi, cordyceps, shiitake, maitake,
   cognition, energy, immunity, focus, sleep, stress, dosage,
   morning_routine, workout, productivity, wellness

CAPTION:
{caption}

Respond in JSON format:
{{
    "content_type": "...",
    "messaging_patterns": ["...", "..."],
    "detected_products": ["...", "..."],
    "influencer_indicators": true/false,
    "key_topics": ["...", "..."],
    "confidence_score": 0.0-1.0
}}
"""


THEME_EXTRACTION_SHORT_PROMPT = """
You are a social media analyst. Analyze this short Instagram caption about mushroom supplements.

Account: @{account_name}
Caption: {caption}

Extract:
1. content_type: educational, promotional, lifestyle, or testimonial
2. key_topics: 2-3 relevant topics (e.g., lions_mane, focus, wellness)
3. confidence_score: 0.0-1.0

Respond in JSON:
{{
    "content_type": "...",
    "messaging_patterns": [],
    "detected_products": [],
    "influencer_indicators": false,
    "key_topics": ["...", "..."],
    "confidence_score": 0.0-1.0
}}
"""


HEALTH_CLAIM_DETECTION_PROMPT = """
You are an EU Health Claims Regulation expert analyzing Instagram content for potential violations.

REGULATORY CONTEXT:
- EC 1924/2006 prohibits health claims on food/supplements unless explicitly authorized
- Zero approved health claims exist for functional mushrooms (lion's mane, chaga, reishi, etc.)
- Prohibited language: "treats", "cures", "prevents" disease, medical terminology

POST CONTEXT:
- Account: @{account_name}
- Is Competitor: {is_competitor}

TASK:
Scan this caption for health claims and classify each:

CLAIM CATEGORIES:
1. TREATMENT: Claims the product treats/cures conditions
   Examples: "treats brain fog", "cures fatigue", "heals inflammation"
   Severity: HIGH

2. PREVENTION: Claims the product prevents conditions
   Examples: "prevents cognitive decline", "protects against disease"
   Severity: HIGH

3. ENHANCEMENT: Claims the product improves body functions
   Examples: "boosts immunity", "enhances cognition", "improves focus"
   Severity: MEDIUM

4. GENERAL WELLNESS: Vague wellness language
   Examples: "supports wellbeing", "for your health journey"
   Severity: LOW

CAPTION:
{caption}

Respond in JSON format:
{{
    "claims_detected": [
        {{"claim_text": "exact phrase", "category": "treatment|prevention|enhancement|wellness", "confidence": 0.0-1.0, "severity": "high|medium|low"}}
    ],
    "requires_cleanmarket_review": true/false,
    "overall_risk_level": "none|low|medium|high",
    "summary": "Brief description for CleanMarket queue"
}}

Return empty claims_detected array if no health claims found.
"""


TAG_GENERATION_PROMPT = """
Generate relevant tags for this Instagram post about mushroom supplements.

Caption: {caption}
Hashtags used: {hashtags}
Theme analysis: {theme_summary}

Generate 5-10 tags that:
1. Describe the content accurately
2. Are relevant for content discovery
3. Include mushroom types mentioned
4. Include benefits/topics discussed
5. Do NOT include emojis

Respond with a JSON array of lowercase tags:
["tag1", "tag2", "tag3", ...]
"""
