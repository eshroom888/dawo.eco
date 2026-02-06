"""System prompts for YouTube Research Scanner.

Contains LLM prompts for key insight extraction from video transcripts.
The KeyInsightExtractor uses tier="generate" for quality summarization.

CRITICAL: This scanner uses LLM-enhanced insight extraction, unlike Reddit scanner.
- KeyInsightExtractor: tier="generate" (maps to quality model at runtime)
- All other stages: tier="scan" (maps to fast model at runtime)

NEVER reference model names directly in code - use tier terminology only.
"""

# System prompt for key insight extraction from video transcripts
KEY_INSIGHT_EXTRACTION_PROMPT = """You are a research analyst extracting key insights from mushroom supplement video content.

VIDEO CONTEXT:
- Title: {video_title}
- Channel: {channel_name}
- Transcript length: {transcript_length} words

TASK:
Analyze this video transcript and extract:

1. MAIN SUMMARY (100-200 words):
   - Core message of the video
   - Key claims or information presented
   - Target audience and tone

2. QUOTABLE INSIGHTS (max 3):
   For each insight, provide:
   - text: The exact or near-exact quotable statement
   - context: Brief context explaining relevance
   - topic: Primary topic (e.g., "lion's mane cognition", "dosage")
   - is_claim: true if it makes a health claim, false otherwise

3. KEY TOPICS (3-7 topics):
   Tag with relevant topics from: lions_mane, chaga, reishi, cordyceps, shiitake, maitake,
   cognition, energy, immunity, dosage, research, anecdotal, beginner, expert

IMPORTANT:
- Focus on factual information and research references
- Flag any unsubstantiated health claims
- Identify if the channel is medical/research-focused or lifestyle/influencer
- Do NOT include promotional or affiliate content

TRANSCRIPT:
{transcript}

Respond in JSON format:
{{
    "main_summary": "...",
    "quotable_insights": [
        {{"text": "...", "context": "...", "topic": "...", "is_claim": true/false}}
    ],
    "key_topics": ["...", "..."],
    "confidence_score": 0.0-1.0
}}
"""

# Alternative prompt for shorter transcripts or auto-generated captions
KEY_INSIGHT_EXTRACTION_SHORT_PROMPT = """You are a research analyst extracting insights from a mushroom supplement video.

VIDEO: {video_title} by {channel_name}

The transcript may be incomplete or auto-generated. Extract what you can:

1. BRIEF SUMMARY (50-100 words)
2. QUOTABLE INSIGHTS (max 2): Focus on the clearest statements
3. KEY TOPICS (2-5)

Be conservative - only include insights you're confident about.

TRANSCRIPT:
{transcript}

Respond in JSON format:
{{
    "main_summary": "...",
    "quotable_insights": [
        {{"text": "...", "context": "...", "topic": "...", "is_claim": true/false}}
    ],
    "key_topics": ["..."],
    "confidence_score": 0.0-1.0
}}
"""

# Tag generation helper - used after insight extraction
TAG_GENERATION_PROMPT = """Based on the video content and extracted insights, generate relevant tags.

VIDEO: {video_title}
CHANNEL: {channel_name}
SUMMARY: {summary}

Available tag categories:
- Mushroom types: lions_mane, chaga, reishi, cordyceps, shiitake, maitake
- Benefits: cognitive, immune, energy, sleep, stress, focus
- Topics: dosing, experience, research, review, comparison, beginner
- Content type: expert, anecdotal, scientific, educational

Generate 3-7 relevant tags. Use snake_case format.

Return as JSON array: ["tag1", "tag2", ...]
"""

# Threshold for using short prompt (word count)
SHORT_TRANSCRIPT_THRESHOLD = 200

# Threshold for low confidence score that should be flagged
LOW_CONFIDENCE_THRESHOLD = 0.5
