from typing import TypedDict, List, Annotated, Optional
from langgraph.graph import StateGraph, END
import operator
from app.core import get_openai_service
from app.services import get_pdf_processor, get_elevenlabs_service
import logging

logger = logging.getLogger(__name__)


class PodcastState(TypedDict):
    """State for the podcast generation workflow."""
    pdf_content: str
    pdf_metadata: dict
    summary: str
    script: List[dict]
    audio_segments: List[bytes]
    final_audio: Optional[bytes]
    error: Optional[str]
    status: str


async def extract_content(state: PodcastState) -> PodcastState:
    """Extract and summarize content from PDF."""
    llm = get_openai_service()
    
    prompt = f"""Analyze the following academic content and create a comprehensive summary 
    that captures the key concepts, arguments, and insights. Focus on making it engaging 
    and educational.
    
    Content:
    {state['pdf_content'][:50000]}  # Limit to avoid token limits
    
    Provide a detailed summary that would work well as the basis for an educational podcast episode."""
    
    summary = await llm.invoke(
        prompt,
        system_prompt="You are an expert academic content summarizer. Create engaging, educational summaries.",
        max_tokens=4000,
    )
    
    return {**state, "summary": summary, "status": "summarized"}


async def generate_script(state: PodcastState) -> PodcastState:
    """Generate a two-person podcast script from the summary."""
    llm = get_openai_service()
    
    prompt = f"""Create an engaging two-person podcast script based on this academic summary.
    
    Summary:
    {state['summary']}
    
    Guidelines:
    - Create a natural conversation between two hosts: Alex (curious learner) and Sam (knowledgeable expert)
    - Make it educational but entertaining
    - Include relevant examples and analogies
    - Break down complex concepts
    - The script should be 5-10 minutes when read aloud
    - Format each line as JSON: {{"speaker": 1 or 2, "text": "dialogue"}}
    
    Return ONLY a JSON array of dialogue lines, no other text."""
    
    script_text = await llm.invoke(
        prompt,
        system_prompt="You are a podcast scriptwriter. Create engaging educational dialogue.",
        max_tokens=8000,
    )
    
    # Parse the script
    import json
    try:
        # Clean up the response
        script_text = script_text.strip()
        if script_text.startswith("```"):
            script_text = script_text.split("```")[1]
            if script_text.startswith("json"):
                script_text = script_text[4:]
        
        script = json.loads(script_text)
    except json.JSONDecodeError:
        # Fallback: create a simple script
        script = [
            {"speaker": 1, "text": f"Welcome to our podcast! Today we're discussing an interesting topic."},
            {"speaker": 2, "text": state['summary'][:500]},
            {"speaker": 1, "text": "That's fascinating! Thanks for listening."},
        ]
    
    return {**state, "script": script, "status": "scripted"}


async def generate_audio(state: PodcastState) -> PodcastState:
    """Generate audio from the script using ElevenLabs."""
    tts = get_elevenlabs_service()
    
    try:
        audio = await tts.generate_dialogue(state['script'])
        return {**state, "final_audio": audio, "status": "completed"}
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


def should_continue(state: PodcastState) -> str:
    """Determine if we should continue or end."""
    if state.get("error"):
        return "end"
    return "continue"


def create_podcast_graph() -> StateGraph:
    """Create the podcast generation workflow graph."""
    workflow = StateGraph(PodcastState)
    
    # Add nodes
    workflow.add_node("extract", extract_content)
    workflow.add_node("script", generate_script)
    workflow.add_node("audio", generate_audio)
    
    # Add edges
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "script")
    workflow.add_edge("script", "audio")
    workflow.add_edge("audio", END)
    
    return workflow.compile()


class PodcastAgent:
    """Agent for generating podcasts from PDFs using Mamba-enhanced processing."""
    
    def __init__(self, use_mamba: bool = True):
        self.graph = create_podcast_graph()
        # Use Mamba-enhanced processor for intelligent extraction
        self.pdf_processor = get_pdf_processor(use_mamba=use_mamba)
        self.use_mamba = use_mamba
    
    async def generate(self, pdf_bytes: bytes) -> dict:
        """Generate a podcast from PDF bytes with Mamba intelligence."""
        logger.info(f"Starting podcast generation with Mamba={'enabled' if self.use_mamba else 'disabled'}")
        
        # Extract text from PDF with intelligent filtering
        content = await self.pdf_processor.extract_text(pdf_bytes)
        metadata = await self.pdf_processor.extract_metadata(pdf_bytes)
        
        # Extract key concepts if using Mamba
        if self.use_mamba:
            try:
                key_concepts = await self.pdf_processor.extract_key_concepts(pdf_bytes, top_k=10)
                logger.info(f"Extracted key concepts: {key_concepts[:5]}")
                metadata['key_concepts'] = key_concepts
            except Exception as e:
                logger.warning(f"Could not extract concepts: {e}")
        
        # Initial state
        initial_state: PodcastState = {
            "pdf_content": content,
            "pdf_metadata": metadata,
            "summary": "",
            "script": [],
            "audio_segments": [],
            "final_audio": None,
            "error": None,
            "status": "started",
        }
        
        # Run the workflow
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "audio": result.get("final_audio"),
            "script": result.get("script"),
            "summary": result.get("summary"),
            "status": result.get("status"),
            "error": result.get("error"),
        }


def get_podcast_agent() -> PodcastAgent:
    """Get podcast agent instance."""
    return PodcastAgent()
