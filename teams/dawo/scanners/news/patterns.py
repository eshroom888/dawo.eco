"""Categorization patterns for Industry News Scanner.

Rule-based categorization patterns for news articles.
UNIQUE to News Scanner:
    - NO LLM calls - all categorization uses regex pattern matching
    - Uses tier="scan" but no actual model calls needed
    - Lightweight, cost-effective for daily execution

Patterns classify articles into categories:
    - REGULATORY: EU, FDA, Mattilsynet, compliance news
    - RESEARCH: Studies, clinical trials, findings
    - PRODUCT_NEWS: Launches, announcements
    - COMPETITOR: Competitor brand mentions
    - GENERAL: Other industry news

Priority Keywords trigger HIGH priority for regulatory news:
    - health claims, novel food, EC 1924, compliance violation
"""

import re

# Regulatory detection patterns - highest priority
# Matches: EU health claims, EC 1924/2006, novel food, Mattilsynet, FDA
REGULATORY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bEU\s+(?:health\s+claims?|regulation|directive|commission)\b", re.IGNORECASE),
    re.compile(r"\bEC\s+1924/2006\b", re.IGNORECASE),
    re.compile(r"\bnovel\s+food\b", re.IGNORECASE),
    re.compile(r"\bMattilsynet\b", re.IGNORECASE),
    re.compile(r"\bFDA\s+(?:approval|warning|regulation|enforcement)\b", re.IGNORECASE),
    re.compile(r"\bhealth\s+claims?\s+(?:register|regulation|compliance)\b", re.IGNORECASE),
    re.compile(r"\bregulatory\s+(?:update|change|approval|enforcement)\b", re.IGNORECASE),
    re.compile(r"\bcompliance\s+(?:update|requirement|warning)\b", re.IGNORECASE),
    re.compile(r"\bEFSA\b", re.IGNORECASE),  # European Food Safety Authority
]

# High-priority keywords - boost regulatory news to HIGH priority
# These trigger requires_operator_attention=True and score boost to 8+
HIGH_PRIORITY_KEYWORDS: list[str] = [
    "health claims",
    "novel food",
    "ec 1924",
    "compliance violation",
    "enforcement action",
    "regulatory warning",
    "product recall",
    "food safety alert",
]

# Research detection patterns
RESEARCH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bclinical\s+(?:trial|study|research)\b", re.IGNORECASE),
    re.compile(r"\bstudy\s+(?:finds|shows|reveals|demonstrates)\b", re.IGNORECASE),
    re.compile(r"\bresearch(?:ers)?\s+(?:found|discover|report)\b", re.IGNORECASE),
    re.compile(r"\bpeer[- ]reviewed\b", re.IGNORECASE),
    re.compile(r"\bscientific\s+evidence\b", re.IGNORECASE),
    re.compile(r"\brandomized\s+controlled\b", re.IGNORECASE),
    re.compile(r"\bdouble[- ]blind\b", re.IGNORECASE),
]

# Product news detection patterns
PRODUCT_NEWS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\blaunches?\b", re.IGNORECASE),
    re.compile(r"\bnew\s+product\b", re.IGNORECASE),
    re.compile(r"\bannounces?\b", re.IGNORECASE),
    re.compile(r"\bintroduces?\b", re.IGNORECASE),
    re.compile(r"\bpartnership\b", re.IGNORECASE),
    re.compile(r"\bacquisition\b", re.IGNORECASE),
    re.compile(r"\bmerger\b", re.IGNORECASE),
    re.compile(r"\bexpansion\b", re.IGNORECASE),
]

# Mushroom-specific keywords for research boost
MUSHROOM_KEYWORDS: list[str] = [
    "lion's mane",
    "hericium",
    "chaga",
    "inonotus",
    "reishi",
    "ganoderma",
    "cordyceps",
    "shiitake",
    "maitake",
    "functional mushroom",
    "adaptogen",
    "turkey tail",
    "trametes",
]
