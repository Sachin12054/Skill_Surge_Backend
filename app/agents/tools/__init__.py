"""
Tool registry and initialization
"""

from .search_tools import (
    search_arxiv,
    search_semantic_scholar,
    check_hypothesis_novelty,
    find_related_concepts,
)

from .validation_tools import (
    execute_python_code,
    validate_statistical_claim,
    score_hypothesis_testability,
    analyze_research_feasibility,
)

# Tool collections for different agent types
RESEARCH_TOOLS = [
    search_arxiv,
    search_semantic_scholar,
    find_related_concepts,
]

VALIDATION_TOOLS = [
    validate_statistical_claim,
    score_hypothesis_testability,
    analyze_research_feasibility,
    execute_python_code,
]

NOVELTY_TOOLS = [
    check_hypothesis_novelty,
    search_semantic_scholar,
]

ALL_TOOLS = RESEARCH_TOOLS + VALIDATION_TOOLS + NOVELTY_TOOLS

__all__ = [
    "RESEARCH_TOOLS",
    "VALIDATION_TOOLS", 
    "NOVELTY_TOOLS",
    "ALL_TOOLS",
    "search_arxiv",
    "search_semantic_scholar",
    "check_hypothesis_novelty",
    "find_related_concepts",
    "execute_python_code",
    "validate_statistical_claim",
    "score_hypothesis_testability",
    "analyze_research_feasibility",
]
