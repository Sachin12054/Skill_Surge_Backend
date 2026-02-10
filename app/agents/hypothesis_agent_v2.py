"""
Production-level Hypothesis Lab Agent using LangGraph
Generates research hypotheses, claims, and citations from academic papers
"""

from typing import TypedDict, List, Optional, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from openai import OpenAI
from app.core.config import get_settings
from app.services.mamba_pdf_processor import MambaPDFProcessor
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
settings = get_settings()


class Claim(TypedDict):
    """A claim extracted from a paper."""
    id: str
    text: str
    source_paper_id: str
    source_paper_title: str
    page_reference: Optional[str]
    confidence: float
    claim_type: str  # finding, method, theory, observation


class Citation(TypedDict):
    """A citation linking a claim to supporting evidence."""
    claim_id: str
    evidence_text: str
    source_paper_id: str
    relevance_score: float


class ResearchGap(TypedDict):
    """An identified gap in the research."""
    id: str
    title: str
    description: str
    related_concepts: List[str]
    importance_score: float
    suggested_approaches: List[str]


class GeneratedHypothesis(TypedDict):
    """A generated research hypothesis."""
    id: str
    title: str
    description: str
    rationale: str
    source_concepts: List[str]
    supporting_claims: List[str]  # claim IDs
    methodology_hints: List[str]
    testability_score: float
    novelty_score: float
    significance_score: float
    confidence: float
    status: str


class HypothesisLabState(TypedDict):
    """State for the hypothesis generation workflow."""
    papers: List[Dict[str, Any]]
    focus_area: Optional[str]
    
    # Extracted data
    concepts: List[Dict[str, Any]]
    claims: List[Claim]
    
    # Generated outputs
    hypotheses: List[GeneratedHypothesis]
    research_gaps: List[ResearchGap]
    citations: List[Citation]
    
    # Metadata
    error: Optional[str]
    status: str
    current_step: str
    progress: float


def get_openai_client() -> OpenAI:
    """Get OpenAI client."""
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def call_openai(
    prompt: str,
    system_prompt: str = "You are an expert research assistant.",
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> str:
    """Call OpenAI API with error handling."""
    client = get_openai_client()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    
    return response.choices[0].message.content


def parse_json_response(response: str) -> Any:
    """Parse JSON from LLM response, handling markdown code blocks."""
    response = response.strip()
    
    # Remove markdown code blocks
    if response.startswith("```"):
        lines = response.split("\n")
        # Remove first and last lines (```json and ```)
        lines = lines[1:-1] if lines[-1] == "```" else lines[1:]
        response = "\n".join(lines)
        if response.startswith("json"):
            response = response[4:].strip()
    
    return json.loads(response)


async def extract_concepts_and_claims(state: HypothesisLabState) -> HypothesisLabState:
    """Extract key concepts and claims from papers."""
    logger.info("Extracting concepts and claims from papers...")
    
    all_concepts = []
    all_claims = []
    
    for paper in state['papers']:
        content = paper.get('content', '')[:25000]  # Limit content
        
        prompt = f"""Analyze this academic paper and extract:

1. KEY CONCEPTS: Main ideas, theories, methods, and phenomena discussed
2. CLAIMS: Specific findings, assertions, or conclusions made

Paper Title: {paper.get('title', 'Unknown')}

Content:
{content}

{f"Focus Area: {state['focus_area']}" if state.get('focus_area') else ""}

Return a JSON object with:
{{
    "concepts": [
        {{
            "name": "concept name",
            "type": "theory|method|finding|phenomenon",
            "description": "brief description",
            "domain": "field of study",
            "importance": 0.0-1.0
        }}
    ],
    "claims": [
        {{
            "text": "the specific claim or finding",
            "claim_type": "finding|method|theory|observation",
            "confidence": 0.0-1.0,
            "page_reference": "if identifiable"
        }}
    ]
}}

Return ONLY valid JSON."""

        try:
            response = call_openai(
                prompt,
                system_prompt="You are an expert academic researcher skilled at extracting key information from papers.",
                max_tokens=3000,
            )
            
            data = parse_json_response(response)
            
            # Add paper reference to concepts
            for concept in data.get('concepts', []):
                concept['source_paper_id'] = paper.get('id', 'unknown')
                concept['source_paper_title'] = paper.get('title', 'Unknown')
                all_concepts.append(concept)
            
            # Add paper reference to claims
            for i, claim in enumerate(data.get('claims', [])):
                claim['id'] = f"{paper.get('id', 'unknown')}_claim_{i}"
                claim['source_paper_id'] = paper.get('id', 'unknown')
                claim['source_paper_title'] = paper.get('title', 'Unknown')
                all_claims.append(claim)
                
        except Exception as e:
            logger.error(f"Error extracting from paper: {e}")
            continue
    
    return {
        **state,
        "concepts": all_concepts,
        "claims": all_claims,
        "status": "concepts_extracted",
        "current_step": "extract_concepts",
        "progress": 0.25,
    }


async def identify_research_gaps(state: HypothesisLabState) -> HypothesisLabState:
    """Identify research gaps from the extracted concepts and claims."""
    logger.info("Identifying research gaps...")
    
    concepts_summary = "\n".join([
        f"- {c['name']} ({c['type']}): {c['description']}"
        for c in state['concepts'][:30]  # Limit for context
    ])
    
    claims_summary = "\n".join([
        f"- {c['text'][:200]}"
        for c in state['claims'][:20]
    ])
    
    prompt = f"""Based on these concepts and claims from academic papers, identify research gaps.

CONCEPTS:
{concepts_summary}

CLAIMS:
{claims_summary}

{f"Focus Area: {state['focus_area']}" if state.get('focus_area') else ""}

Identify 3-5 research gaps - areas that need more investigation, unexplored connections, or contradictions.

Return a JSON array:
[
    {{
        "id": "gap_1",
        "title": "Brief title for the gap",
        "description": "Detailed description of the research gap",
        "related_concepts": ["concept1", "concept2"],
        "importance_score": 0.0-1.0,
        "suggested_approaches": ["approach1", "approach2"]
    }}
]

Return ONLY valid JSON array."""

    try:
        response = call_openai(
            prompt,
            system_prompt="You are a research strategist skilled at identifying gaps and opportunities in academic literature.",
            max_tokens=2000,
        )
        
        gaps = parse_json_response(response)
        
    except Exception as e:
        logger.error(f"Error identifying gaps: {e}")
        gaps = []
    
    return {
        **state,
        "research_gaps": gaps,
        "status": "gaps_identified",
        "current_step": "identify_gaps",
        "progress": 0.5,
    }


async def generate_hypotheses(state: HypothesisLabState) -> HypothesisLabState:
    """Generate novel research hypotheses based on gaps and concepts."""
    logger.info("Generating hypotheses...")
    
    # Create cross-paper concept pairs
    concept_pairs = []
    concepts = state['concepts']
    
    for i, c1 in enumerate(concepts):
        for c2 in concepts[i+1:]:
            # Prefer cross-paper or cross-domain pairs
            if (c1.get('source_paper_id') != c2.get('source_paper_id') or 
                c1.get('domain') != c2.get('domain')):
                score = (c1.get('importance', 0.5) + c2.get('importance', 0.5)) / 2
                concept_pairs.append((c1, c2, score))
    
    # Sort by score and take top pairs
    concept_pairs.sort(key=lambda x: x[2], reverse=True)
    top_pairs = concept_pairs[:5]
    
    gaps_summary = "\n".join([
        f"- {g['title']}: {g['description']}"
        for g in state['research_gaps']
    ])
    
    hypotheses = []
    
    for idx, (c1, c2, _) in enumerate(top_pairs):
        prompt = f"""Generate a novel, testable research hypothesis connecting these two concepts.

CONCEPT 1:
Name: {c1['name']}
Type: {c1['type']}
Description: {c1.get('description', 'N/A')}
From paper: {c1.get('source_paper_title', 'Unknown')}

CONCEPT 2:
Name: {c2['name']}
Type: {c2['type']}
Description: {c2.get('description', 'N/A')}
From paper: {c2.get('source_paper_title', 'Unknown')}

IDENTIFIED RESEARCH GAPS:
{gaps_summary}

{f"Focus Area: {state['focus_area']}" if state.get('focus_area') else ""}

Generate a hypothesis that:
1. Connects these concepts in a novel way
2. Addresses one of the research gaps if possible
3. Is specific and testable
4. Would be meaningful if proven true

Return a JSON object:
{{
    "title": "Clear, compelling hypothesis title (max 20 words)",
    "description": "Detailed hypothesis explanation (150-250 words)",
    "rationale": "Why this hypothesis is worth investigating",
    "methodology_hints": ["method1", "method2", "method3"],
    "testability_score": 0.0-1.0,
    "novelty_score": 0.0-1.0,
    "significance_score": 0.0-1.0
}}

Return ONLY valid JSON."""

        try:
            response = call_openai(
                prompt,
                system_prompt="You are a creative research hypothesis generator skilled at finding novel connections.",
                max_tokens=1500,
                temperature=0.8,  # Higher creativity
            )
            
            hyp = parse_json_response(response)
            hyp['id'] = f"hyp_{idx}"
            hyp['source_concepts'] = [c1['name'], c2['name']]
            hyp['supporting_claims'] = []  # Will be filled in validation
            hyp['confidence'] = (
                hyp.get('testability_score', 0.5) * 0.35 +
                hyp.get('novelty_score', 0.5) * 0.35 +
                hyp.get('significance_score', 0.5) * 0.3
            )
            hyp['status'] = 'generated'
            
            hypotheses.append(hyp)
            
        except Exception as e:
            logger.error(f"Error generating hypothesis: {e}")
            continue
    
    return {
        **state,
        "hypotheses": hypotheses,
        "status": "hypotheses_generated",
        "current_step": "generate_hypotheses",
        "progress": 0.75,
    }


async def validate_and_link_citations(state: HypothesisLabState) -> HypothesisLabState:
    """Validate hypotheses and link supporting claims as citations."""
    logger.info("Validating hypotheses and linking citations...")
    
    validated_hypotheses = []
    all_citations = []
    
    claims_text = "\n".join([
        f"[{c['id']}] {c['text']}"
        for c in state['claims']
    ])
    
    for hyp in state['hypotheses']:
        prompt = f"""Validate this research hypothesis and find supporting evidence from the claims.

HYPOTHESIS:
Title: {hyp['title']}
Description: {hyp['description']}

AVAILABLE CLAIMS FROM PAPERS:
{claims_text}

Evaluate the hypothesis and find supporting claims.

Return a JSON object:
{{
    "is_valid": true/false,
    "validation_feedback": "Brief feedback on the hypothesis quality",
    "adjusted_scores": {{
        "testability_score": 0.0-1.0,
        "novelty_score": 0.0-1.0,
        "significance_score": 0.0-1.0
    }},
    "supporting_claim_ids": ["claim_id1", "claim_id2"],
    "relevance_scores": {{
        "claim_id1": 0.0-1.0,
        "claim_id2": 0.0-1.0
    }}
}}

Return ONLY valid JSON."""

        try:
            response = call_openai(
                prompt,
                system_prompt="You are a rigorous research validator skilled at evaluating hypotheses.",
                max_tokens=1000,
            )
            
            validation = parse_json_response(response)
            
            if validation.get('is_valid', False):
                # Update hypothesis scores
                adj = validation.get('adjusted_scores', {})
                hyp['testability_score'] = adj.get('testability_score', hyp.get('testability_score', 0.5))
                hyp['novelty_score'] = adj.get('novelty_score', hyp.get('novelty_score', 0.5))
                hyp['significance_score'] = adj.get('significance_score', hyp.get('significance_score', 0.5))
                hyp['confidence'] = (
                    hyp['testability_score'] * 0.35 +
                    hyp['novelty_score'] * 0.35 +
                    hyp['significance_score'] * 0.3
                )
                hyp['supporting_claims'] = validation.get('supporting_claim_ids', [])
                hyp['status'] = 'validated'
                hyp['validation_feedback'] = validation.get('validation_feedback', '')
                
                # Create citations
                for claim_id in validation.get('supporting_claim_ids', []):
                    relevance = validation.get('relevance_scores', {}).get(claim_id, 0.5)
                    claim = next((c for c in state['claims'] if c['id'] == claim_id), None)
                    if claim:
                        all_citations.append({
                            'hypothesis_id': hyp['id'],
                            'claim_id': claim_id,
                            'evidence_text': claim['text'],
                            'source_paper_id': claim['source_paper_id'],
                            'relevance_score': relevance,
                        })
                
                validated_hypotheses.append(hyp)
            
        except Exception as e:
            logger.error(f"Error validating hypothesis: {e}")
            # Keep hypothesis but mark as unvalidated
            hyp['status'] = 'unvalidated'
            validated_hypotheses.append(hyp)
    
    # Sort by confidence
    validated_hypotheses.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    
    return {
        **state,
        "hypotheses": validated_hypotheses,
        "citations": all_citations,
        "status": "completed",
        "current_step": "validate",
        "progress": 1.0,
    }


def create_hypothesis_lab_graph() -> StateGraph:
    """Create the hypothesis generation workflow graph."""
    workflow = StateGraph(HypothesisLabState)
    
    # Add nodes
    workflow.add_node("extract", extract_concepts_and_claims)
    workflow.add_node("gaps", identify_research_gaps)
    workflow.add_node("generate", generate_hypotheses)
    workflow.add_node("validate", validate_and_link_citations)
    
    # Add edges
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "gaps")
    workflow.add_edge("gaps", "generate")
    workflow.add_edge("generate", "validate")
    workflow.add_edge("validate", END)
    
    return workflow.compile()


class HypothesisLabAgent:
    """Production-level agent for generating research hypotheses."""
    
    def __init__(self):
        self.graph = create_hypothesis_lab_graph()
        self.pdf_processor = MambaPDFProcessor()
    
    async def generate(
        self,
        paper_contents: List[Dict[str, Any]],
        focus_area: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate hypotheses from multiple papers."""
        
        initial_state: HypothesisLabState = {
            "papers": paper_contents,
            "focus_area": focus_area,
            "concepts": [],
            "claims": [],
            "hypotheses": [],
            "research_gaps": [],
            "citations": [],
            "error": None,
            "status": "started",
            "current_step": "initialize",
            "progress": 0.0,
        }
        
        try:
            result = await self.graph.ainvoke(initial_state)
            
            return {
                "success": True,
                "hypotheses": result.get("hypotheses", []),
                "research_gaps": result.get("research_gaps", []),
                "claims": result.get("claims", []),
                "citations": result.get("citations", []),
                "concepts": result.get("concepts", []),
                "status": result.get("status"),
            }
        
        except Exception as e:
            logger.error(f"Hypothesis generation failed: {e}")
            return {
                "success": False,
                "hypotheses": [],
                "research_gaps": [],
                "claims": [],
                "citations": [],
                "concepts": [],
                "status": "failed",
                "error": str(e),
            }
    
    async def extract_from_pdf(self, pdf_bytes: bytes, title: str = "Unknown") -> Dict[str, Any]:
        """Extract content from PDF for hypothesis generation."""
        content = await self.pdf_processor.extract_text(pdf_bytes)
        concepts = self.pdf_processor.extract_key_concepts(content, top_k=10)
        
        return {
            "title": title,
            "content": content,
            "key_concepts": concepts,
        }


def get_hypothesis_lab_agent() -> HypothesisLabAgent:
    """Get hypothesis lab agent instance."""
    return HypothesisLabAgent()
