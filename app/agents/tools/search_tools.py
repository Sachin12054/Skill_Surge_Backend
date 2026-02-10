"""
Research search tools for hypothesis agents
"""

from typing import Optional, List, Dict, Any
from langchain.tools import tool
import httpx
import logging

logger = logging.getLogger(__name__)


@tool
def search_arxiv(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search ArXiv for academic papers related to a query.
    
    Args:
        query: Search query (keywords, concepts, or research topics)
        max_results: Maximum number of results to return (default 5)
    
    Returns:
        List of papers with title, abstract, authors, and URL
    """
    try:
        import arxiv
        
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        results = []
        for paper in search.results():
            results.append({
                "title": paper.title,
                "abstract": paper.summary[:500] + "..." if len(paper.summary) > 500 else paper.summary,
                "authors": [author.name for author in paper.authors],
                "published": paper.published.isoformat(),
                "url": paper.entry_id,
                "pdf_url": paper.pdf_url,
            })
        
        logger.info(f"Found {len(results)} papers on ArXiv for query: {query}")
        return results
        
    except Exception as e:
        logger.error(f"ArXiv search error: {e}")
        return [{"error": str(e)}]


@tool
def search_semantic_scholar(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search Semantic Scholar for academic papers with citation data.
    
    Args:
        query: Search query (keywords or paper topics)
        limit: Maximum number of results (default 5)
    
    Returns:
        List of papers with citations, influential citations, and metadata
    """
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,authors,year,citationCount,influentialCitationCount,url,openAccessPdf"
        }
        
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        
        data = response.json()
        papers = data.get("data", [])
        
        results = []
        for paper in papers:
            results.append({
                "title": paper.get("title", ""),
                "abstract": paper.get("abstract", "")[:500] if paper.get("abstract") else "",
                "authors": [a.get("name", "") for a in paper.get("authors", [])],
                "year": paper.get("year"),
                "citations": paper.get("citationCount", 0),
                "influential_citations": paper.get("influentialCitationCount", 0),
                "url": paper.get("url", ""),
                "pdf_url": paper.get("openAccessPdf", {}).get("url") if paper.get("openAccessPdf") else None,
            })
        
        logger.info(f"Found {len(results)} papers on Semantic Scholar for query: {query}")
        return results
        
    except Exception as e:
        logger.error(f"Semantic Scholar search error: {e}")
        return [{"error": str(e)}]


@tool
def check_hypothesis_novelty(hypothesis: str) -> Dict[str, Any]:
    """
    Check if a hypothesis already exists in published literature.
    
    Args:
        hypothesis: The hypothesis statement to check
    
    Returns:
        Dictionary with novelty score and similar existing work
    """
    try:
        # Search for similar work
        papers = search_semantic_scholar.invoke({"query": hypothesis[:200], "limit": 3})
        
        if papers and not any("error" in p for p in papers):
            total_citations = sum(p.get("citations", 0) for p in papers if "citations" in p)
            
            # Simple novelty heuristic
            if total_citations > 100:
                novelty_score = 0.3  # Likely well-studied
            elif total_citations > 20:
                novelty_score = 0.6  # Some existing work
            else:
                novelty_score = 0.9  # Relatively novel
            
            return {
                "novelty_score": novelty_score,
                "similar_papers_count": len(papers),
                "similar_papers": papers,
                "assessment": "High novelty - limited existing work" if novelty_score > 0.7 else 
                             "Moderate novelty - some related research" if novelty_score > 0.4 else
                             "Low novelty - well-studied area"
            }
        
        return {
            "novelty_score": 0.8,
            "similar_papers_count": 0,
            "similar_papers": [],
            "assessment": "No similar work found - potentially highly novel"
        }
        
    except Exception as e:
        logger.error(f"Novelty check error: {e}")
        return {"error": str(e), "novelty_score": 0.5}


@tool
def find_related_concepts(concept: str, max_results: int = 5) -> List[str]:
    """
    Find related research concepts and keywords using paper abstracts.
    
    Args:
        concept: The concept to find related terms for
        max_results: Maximum number of related concepts to return
    
    Returns:
        List of related concept strings
    """
    try:
        # Search papers about this concept
        papers = search_arxiv.invoke({"query": concept, "max_results": 3})
        
        if not papers or any("error" in p for p in papers):
            return []
        
        # Extract frequent terms from abstracts (simplified)
        all_text = " ".join(p.get("abstract", "") for p in papers if "abstract" in p)
        
        # Simple keyword extraction (in production, use proper NLP)
        import re
        words = re.findall(r'\b[a-z]{4,}\b', all_text.lower())
        from collections import Counter
        common = Counter(words).most_common(max_results + 10)
        
        # Filter out stop words and the original concept
        stopwords = {'that', 'with', 'this', 'from', 'have', 'been', 'which', 'their', 'these', 'such'}
        related = [word for word, _ in common if word not in stopwords and word != concept.lower()]
        
        return related[:max_results]
        
    except Exception as e:
        logger.error(f"Related concepts error: {e}")
        return []
