"""LLM prompts for PubMed Scientific Research Scanner.

Contains prompts for:
    - FindingSummarizer: Scientific finding summarization (tier="generate")
    - ClaimValidator: EU Health Claims assessment (tier="generate")

CRITICAL: These prompts are used by tier="generate" (Sonnet) for quality
scientific summarization and compliance assessment.

The prompts are designed to:
    1. Extract compound studied and effect measured
    2. Generate plain-language summaries for content inspiration
    3. Assess content potential under EU Health Claims Regulation
    4. Add appropriate caveats about research vs. marketing claims

NEVER mention specific LLM model names in prompts or code.
"""

# Finding summarization prompt for FindingSummarizer
FINDING_SUMMARIZATION_PROMPT = '''You are a scientific research summarizer for a health food company.

Analyze this PubMed abstract and extract key information:

TITLE: {title}
STUDY TYPE: {study_type}
ABSTRACT: {abstract}

Extract and summarize:
1. COMPOUND STUDIED: The main substance/ingredient studied (include scientific name if present)
2. EFFECT MEASURED: What health/wellness effect was being investigated
3. KEY FINDINGS: 2-3 sentence plain-language summary of results (suitable for general audience)
4. STATISTICAL SIGNIFICANCE: If mentioned, note p-values, confidence intervals, sample size
5. STUDY STRENGTH: Rate as "strong" (RCT, large sample), "moderate" (smaller RCT, review), or "weak" (observational, case study)
6. CONTENT POTENTIAL: Tag as one or more of:
   - "educational": Can discuss the science generally
   - "citation_worthy": Worth citing with DOI link
   - "trend_indicator": Shows research direction in the field

CRITICAL: This is for content inspiration only. All summaries must include this caveat:
"Research finding - not an approved health claim. Can cite study but cannot claim treatment/prevention/cure."

Respond in JSON format:
{{
    "compound_studied": "...",
    "effect_measured": "...",
    "key_findings": "...",
    "statistical_significance": "..." or null,
    "study_strength": "strong|moderate|weak",
    "content_potential": ["educational", "citation_worthy"],
    "caveat": "Research finding - not an approved health claim..."
}}'''

# Claim validation prompt for ClaimValidator
CLAIM_VALIDATION_PROMPT = '''You are an EU Health Claims compliance expert.

Given this research finding summary, determine how it can be used for content marketing under EU Health Claims Regulation (EC 1924/2006):

COMPOUND: {compound}
EFFECT: {effect}
SUMMARY: {summary}
STUDY STRENGTH: {strength}

CRITICAL CONTEXT: There are currently ZERO approved EU health claims for functional mushrooms (Lion's Mane, Chaga, Reishi, Cordyceps, etc.). Any content using these findings CANNOT make health claims.

Determine:
1. CONTENT POTENTIAL: How can this research be used?
   - "citation_only": Can cite the study with DOI link in educational content
   - "educational": Can discuss the science/research direction without claims
   - "trend_awareness": Useful for understanding market/research trends
   - "no_claim": Cannot be used for any marketing claims

2. USAGE GUIDANCE: Specific guidance on how to use this research compliantly

3. EU CLAIM STATUS: Current status for this type of claim
   - "no_approved_claim": No approved claim exists (most common for mushrooms)
   - "pending": Claim under review (rare)
   - "approved": Claim is approved (unlikely for functional mushrooms)

Respond in JSON format:
{{
    "content_potential": ["citation_only", "educational"],
    "usage_guidance": "Can cite this study when discussing research directions...",
    "eu_claim_status": "no_approved_claim",
    "caveat": "Can cite study but NOT claim treatment/prevention/cure",
    "can_cite_study": true,
    "can_make_claim": false
}}'''

# Sample size extraction patterns for harvester
# All patterns support optional comma formatting (e.g., 1,847)
SAMPLE_SIZE_PATTERNS = [
    r"n\s*=\s*([\d,]+)",  # n=77, n = 1,847
    r"([\d,]+)\s*participants",  # 77 participants, 1,500 participants
    r"([\d,]+)\s*subjects",  # 50 subjects
    r"([\d,]+)\s*patients",  # 120 patients, 1,500 patients
    r"([\d,]+)\s*individuals",  # 45 individuals
    r"sample\s*(?:size|of)\s*([\d,]+)",  # sample size 77, sample of 100
    r"([\d,]+)\s*healthy\s*(?:adults|volunteers)",  # 60 healthy adults
    r"([\d,]+)\s*(?:men|women|people)",  # 30 men, 40 women
]

# Study type mapping from PubMed publication types
STUDY_TYPE_MAPPINGS = {
    "randomized controlled trial": "rct",
    "meta-analysis": "meta_analysis",
    "systematic review": "systematic_review",
    "review": "review",
    "clinical trial": "rct",
    "controlled clinical trial": "rct",
}
