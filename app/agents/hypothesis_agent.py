from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from app.core import get_bedrock_service, get_neo4j_service
from app.services import get_pdf_processor
import json
import random


class HypothesisState(TypedDict):
    """State for the hypothesis generation workflow."""
    papers: List[Dict[str, Any]]
    concepts: List[Dict[str, str]]
    concept_pairs: List[tuple]
    hypotheses: List[Dict[str, Any]]
    validated_hypotheses: List[Dict[str, Any]]
    error: Optional[str]
    status: str


async def extract_concepts(state: HypothesisState) -> HypothesisState:
    """Extract key concepts from papers."""
    bedrock = get_bedrock_service()
    all_concepts = []
    
    for paper in state['papers']:
        prompt = f"""Extract the key concepts, theories, methods, and findings from this academic content.
        
        Content:
        {paper['content'][:20000]}
        
        Return a JSON array of concepts, each with:
        - name: concept name
        - type: theory, method, finding, or phenomenon
        - description: brief description
        - domain: field of study
        
        Return ONLY the JSON array."""
        
        response = await bedrock.invoke_claude(
            prompt,
            system_prompt="You are an expert academic concept extractor.",
            max_tokens=2000,
        )
        
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            concepts = json.loads(response)
            for c in concepts:
                c['source_paper'] = paper.get('id', 'unknown')
            all_concepts.extend(concepts)
        except json.JSONDecodeError:
            continue
    
    return {**state, "concepts": all_concepts, "status": "concepts_extracted"}


async def create_concept_pairs(state: HypothesisState) -> HypothesisState:
    """Create interesting concept pairs for hypothesis generation."""
    concepts = state['concepts']
    pairs = []
    
    # Create pairs from different papers/domains
    for i, c1 in enumerate(concepts):
        for c2 in concepts[i+1:]:
            # Prefer cross-domain pairs
            if c1.get('domain') != c2.get('domain') or c1.get('source_paper') != c2.get('source_paper'):
                pairs.append((c1, c2))
    
    # Limit to top pairs (can add scoring logic)
    random.shuffle(pairs)
    pairs = pairs[:10]
    
    return {**state, "concept_pairs": pairs, "status": "pairs_created"}


async def generate_hypotheses(state: HypothesisState) -> HypothesisState:
    """Generate novel research hypotheses from concept pairs."""
    bedrock = get_bedrock_service()
    hypotheses = []
    
    for c1, c2 in state['concept_pairs'][:5]:  # Limit for API calls
        prompt = f"""You are a research hypothesis generator using a genetic algorithm-inspired approach.
        
        Concept 1: {c1['name']}
        Description: {c1.get('description', 'N/A')}
        Domain: {c1.get('domain', 'N/A')}
        
        Concept 2: {c2['name']}
        Description: {c2.get('description', 'N/A')}
        Domain: {c2.get('domain', 'N/A')}
        
        Generate a novel, testable research hypothesis that connects these two concepts in an unexpected way.
        Think about:
        - How might these concepts interact?
        - What unexplored relationship might exist?
        - What would be a surprising but plausible connection?
        
        Return a JSON object with:
        - title: A compelling thesis title (max 15 words)
        - description: Detailed hypothesis explanation (100-200 words)
        - methodology_hints: Array of suggested research methods
        - novelty_explanation: Why this is novel
        - confidence: Your confidence score (0-1)
        
        Return ONLY the JSON object."""
        
        response = await bedrock.invoke_claude(
            prompt,
            system_prompt="You are a creative research hypothesis generator.",
            max_tokens=1500,
        )
        
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            hypothesis = json.loads(response)
            hypothesis['source_concepts'] = [c1['name'], c2['name']]
            hypotheses.append(hypothesis)
        except json.JSONDecodeError:
            continue
    
    return {**state, "hypotheses": hypotheses, "status": "hypotheses_generated"}


async def validate_hypotheses(state: HypothesisState) -> HypothesisState:
    """Validate hypotheses for logical consistency and novelty."""
    bedrock = get_bedrock_service()
    validated = []
    
    for hyp in state['hypotheses']:
        prompt = f"""Evaluate this research hypothesis for:
        1. Logical consistency (is it self-contradictory?)
        2. Testability (can it be empirically tested?)
        3. Novelty (is it genuinely new?)
        4. Significance (would it matter if true?)
        
        Hypothesis: {hyp['title']}
        Description: {hyp['description']}
        
        Return a JSON object with:
        - is_valid: boolean
        - logical_score: 0-1
        - testability_score: 0-1
        - novelty_score: 0-1
        - significance_score: 0-1
        - feedback: brief improvement suggestions
        
        Return ONLY the JSON object."""
        
        response = await bedrock.invoke_claude(
            prompt,
            system_prompt="You are a rigorous research hypothesis validator.",
            max_tokens=500,
        )
        
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            validation = json.loads(response)
            
            if validation.get('is_valid', False):
                hyp['validation'] = validation
                hyp['confidence'] = (
                    validation.get('logical_score', 0) * 0.3 +
                    validation.get('testability_score', 0) * 0.3 +
                    validation.get('novelty_score', 0) * 0.2 +
                    validation.get('significance_score', 0) * 0.2
                )
                validated.append(hyp)
        except json.JSONDecodeError:
            # Skip invalid responses
            continue
    
    # Sort by confidence
    validated.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    
    return {**state, "validated_hypotheses": validated, "status": "completed"}


def create_hypothesis_graph() -> StateGraph:
    """Create the hypothesis generation workflow graph."""
    workflow = StateGraph(HypothesisState)
    
    # Add nodes
    workflow.add_node("extract", extract_concepts)
    workflow.add_node("pair", create_concept_pairs)
    workflow.add_node("generate", generate_hypotheses)
    workflow.add_node("validate", validate_hypotheses)
    
    # Add edges
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "pair")
    workflow.add_edge("pair", "generate")
    workflow.add_edge("generate", "validate")
    workflow.add_edge("validate", END)
    
    return workflow.compile()


class HypothesisAgent:
    """Agent for generating research hypotheses from papers."""
    
    def __init__(self):
        self.graph = create_hypothesis_graph()
        self.pdf_processor = get_pdf_processor()
    
    async def generate(self, paper_contents: List[Dict[str, Any]]) -> dict:
        """Generate hypotheses from multiple papers."""
        initial_state: HypothesisState = {
            "papers": paper_contents,
            "concepts": [],
            "concept_pairs": [],
            "hypotheses": [],
            "validated_hypotheses": [],
            "error": None,
            "status": "started",
        }
        
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "hypotheses": result.get("validated_hypotheses", []),
            "all_concepts": result.get("concepts", []),
            "status": result.get("status"),
            "error": result.get("error"),
        }


def get_hypothesis_agent() -> HypothesisAgent:
    """Get hypothesis agent instance."""
    return HypothesisAgent()
