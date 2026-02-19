"""
Production-level Hypothesis Lab API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.core import get_supabase_service
from app.agents.hypothesis_agent_v2 import get_hypothesis_lab_agent, HypothesisLabAgent
from app.agents.hypothesis_agent_agentic import generate_hypotheses_agentic
from app.api.deps import get_current_user
import fitz  # PyMuPDF for simple PDF extraction
import uuid
from datetime import datetime
import logging
import asyncio
import traceback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hypothesis", tags=["Hypothesis Lab"])


# Request/Response Models
class HypothesisGenerateRequest(BaseModel):
    paper_ids: Optional[List[str]] = None  # Legacy: from materials table
    space_pdf_ids: Optional[List[str]] = None  # New: from space pdfs table
    focus_area: Optional[str] = None
    use_agentic: bool = False  # Toggle between simple and agentic mode


class HypothesisStatusResponse(BaseModel):
    status: str
    progress: float
    current_step: str
    message: Optional[str] = None


class ClaimResponse(BaseModel):
    id: str
    text: str
    source_paper_id: str
    source_paper_title: str
    claim_type: str
    confidence: float


class CitationResponse(BaseModel):
    hypothesis_id: str
    claim_id: str
    evidence_text: str
    source_paper_id: str
    relevance_score: float


class ResearchGapResponse(BaseModel):
    id: str
    title: str
    description: str
    related_concepts: List[str]
    importance_score: float
    suggested_approaches: List[str]


class HypothesisResponse(BaseModel):
    id: str
    title: str
    description: str
    rationale: str
    source_concepts: List[str]
    methodology_hints: List[str]
    testability_score: float
    novelty_score: float
    significance_score: float
    confidence: float
    status: str
    supporting_claims: List[str]
    validation_feedback: Optional[str] = None


class HypothesisFullResult(BaseModel):
    id: str
    hypotheses: List[HypothesisResponse]
    research_gaps: List[ResearchGapResponse]
    claims: List[ClaimResponse]
    citations: List[CitationResponse]
    concepts: List[Dict[str, Any]]
    status: str
    created_at: datetime


# In-memory task storage (use Redis in production)
hypothesis_tasks: Dict[str, dict] = {}


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Simple PDF text extraction using PyMuPDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return ""


def extract_key_concepts(text: str, top_k: int = 15) -> List[str]:
    """Extract key concepts from text (simple keyword extraction)."""
    import re
    # Simple extraction: find capitalized phrases and important terms
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    # Count frequency
    from collections import Counter
    word_counts = Counter(words)
    # Return top concepts
    return [word for word, count in word_counts.most_common(top_k)]


async def process_hypothesis_generation(
    task_id: str,
    paper_ids: List[str],
    user_id: str,
    focus_area: Optional[str] = None,
    space_pdf_ids: Optional[List[str]] = None,
):
    """Background task to generate hypotheses."""
    logger.info(f"[{task_id}] Starting hypothesis generation...")
    
    try:
        hypothesis_tasks[task_id]["status"] = "processing"
        hypothesis_tasks[task_id]["current_step"] = "downloading_papers"
        hypothesis_tasks[task_id]["progress"] = 0.05
        
        supabase = get_supabase_service()
        agent = get_hypothesis_lab_agent()
        
        papers = []
        
        # Process Space PDFs (new method)
        if space_pdf_ids and len(space_pdf_ids) > 0:
            logger.info(f"[{task_id}] Processing {len(space_pdf_ids)} Space PDFs")
            for i, pdf_id in enumerate(space_pdf_ids):
                hypothesis_tasks[task_id]["progress"] = 0.05 + (0.15 * (i / len(space_pdf_ids)))
                hypothesis_tasks[task_id]["message"] = f"Processing PDF {i+1}/{len(space_pdf_ids)}"
                
                # Get PDF info from space_pdfs table
                result = supabase.admin_client.table("space_pdfs").select("*").eq("id", pdf_id).execute()
                
                if result.data:
                    pdf_doc = result.data[0]
                    
                    try:
                        # Download PDF from storage (course-materials bucket)
                        pdf_bytes = supabase.download_file("course-materials", pdf_doc["file_path"])
                        logger.info(f"[{task_id}] Downloaded PDF: {pdf_doc['name']}, {len(pdf_bytes)} bytes")
                        
                        # Extract text using simple PyMuPDF
                        content = extract_pdf_text(pdf_bytes)
                        logger.info(f"[{task_id}] Extracted {len(content)} chars from PDF")
                        
                        if not content:
                            logger.warning(f"[{task_id}] No text extracted from PDF {pdf_id}")
                            continue
                        
                        key_concepts = extract_key_concepts(content, top_k=15)
                        
                        papers.append({
                            "id": pdf_id,
                            "title": pdf_doc.get("name", "Unknown"),
                            "content": content,
                            "key_concepts": key_concepts,
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing Space PDF {pdf_id}: {e}")
                        continue
        
        # Process legacy materials (old method)
        elif paper_ids and len(paper_ids) > 0:
            logger.info(f"[{task_id}] Processing {len(paper_ids)} legacy papers from materials")
            for i, paper_id in enumerate(paper_ids):
                hypothesis_tasks[task_id]["progress"] = 0.05 + (0.15 * (i / len(paper_ids)))
                hypothesis_tasks[task_id]["message"] = f"Processing paper {i+1}/{len(paper_ids)}"
                
                # Get material info from materials table
                result = supabase.client.table("materials").select("*").eq("id", paper_id).execute()
                
                if result.data:
                    material = result.data[0]
                    
                    # Download PDF
                    try:
                        pdf_bytes = supabase.download_file("course-materials", material["file_path"])
                        logger.info(f"[{task_id}] Downloaded material: {material.get('title')}, {len(pdf_bytes)} bytes")
                        
                        # Extract text using simple PyMuPDF
                        content = extract_pdf_text(pdf_bytes)
                        
                        if not content:
                            logger.warning(f"[{task_id}] No text extracted from material {paper_id}")
                            continue
                        
                        key_concepts = extract_key_concepts(content, top_k=15)
                        
                        papers.append({
                            "id": paper_id,
                            "title": material.get("title", "Unknown"),
                            "content": content,
                            "key_concepts": key_concepts,
                        })
                        
                    except Exception as e:
                        logger.error(f"Error downloading paper {paper_id}: {e}")
                        continue
        
        if len(papers) < 1:
            raise ValueError("Need at least 1 paper for hypothesis generation")
        
        hypothesis_tasks[task_id]["current_step"] = "generating_hypotheses"
        hypothesis_tasks[task_id]["progress"] = 0.2
        hypothesis_tasks[task_id]["message"] = "Analyzing papers and generating hypotheses..."
        
        # Check if using agentic mode
        use_agentic = hypothesis_tasks[task_id].get("use_agentic", False)
        
        if use_agentic:
            logger.info(f"[{task_id}] Using AGENTIC multi-agent system with tools")
            result = await generate_hypotheses_agentic(papers, focus_area)
        else:
            logger.info(f"[{task_id}] Using standard hypothesis generation")
            agent = get_hypothesis_lab_agent()
            result = await agent.generate(papers, focus_area)
        
        if not result.get("success", False):
            raise ValueError(result.get("error", "Unknown error during generation"))
        
        hypothesis_tasks[task_id]["progress"] = 0.9
        hypothesis_tasks[task_id]["message"] = "Saving results..."
        
        # Save hypothesis session to database
        session_id = str(uuid.uuid4())
        
        # Combine paper_ids and space_pdf_ids for storage
        all_paper_ids = []
        if space_pdf_ids:
            all_paper_ids.extend(space_pdf_ids)
        if paper_ids:
            all_paper_ids.extend(paper_ids)
        
        # Convert hypotheses to proper format if needed
        hypotheses_data = result.get("hypotheses", [])
        if hypotheses_data and isinstance(hypotheses_data, list):
            # Ensure each hypothesis has an id
            for i, h in enumerate(hypotheses_data):
                if isinstance(h, dict) and "id" not in h:
                    h["id"] = str(i + 1)
        
        session_data = {
            "id": session_id,
            "task_id": task_id,
            "user_id": user_id,
            "paper_ids": all_paper_ids if all_paper_ids else [],
            "focus_area": focus_area,
            "hypotheses": hypotheses_data,
            "research_gaps": result.get("research_gaps", []),
            "claims": result.get("claims", []),
            "citations": result.get("citations", []),
            "concepts": result.get("concepts", []),
            "status": "completed",
            # Let database handle created_at with default NOW()
        }
        
        # Save to Supabase (use admin_client to bypass RLS in background task)
        try:
            logger.info(f"[{task_id}] Saving session to database: {session_id}")
            try:
                # Attempt with task_id column (requires migration 005 to be applied)
                supabase.admin_client.table("hypothesis_sessions").insert(session_data).execute()
                logger.info(f"[{task_id}] Session saved with task_id: {session_id}")
            except Exception as col_err:
                # PGRST204 = column not found; fall back to inserting without task_id
                if "PGRST204" in str(col_err) or "task_id" in str(col_err):
                    logger.warning(f"[{task_id}] task_id column missing in DB, saving without it. Run migration 005_hypothesis_task_id.sql.")
                    session_data_no_task = {k: v for k, v in session_data.items() if k != "task_id"}
                    supabase.admin_client.table("hypothesis_sessions").insert(session_data_no_task).execute()
                    logger.info(f"[{task_id}] Session saved (without task_id): {session_id}")
                else:
                    raise
        except Exception as e:
            logger.error(f"[{task_id}] Error saving session: {e}")
            logger.error(f"[{task_id}] Traceback: {traceback.format_exc()}")
            # Continue anyway, we have the results in memory
        
        hypothesis_tasks[task_id]["status"] = "completed"
        hypothesis_tasks[task_id]["progress"] = 1.0
        hypothesis_tasks[task_id]["current_step"] = "done"
        hypothesis_tasks[task_id]["message"] = "Hypothesis generation complete!"
        hypothesis_tasks[task_id]["result"] = {
            "session_id": session_id,
            **result,
        }
        
        logger.info(f"[{task_id}] Hypothesis generation completed successfully!")
        
    except Exception as e:
        logger.error(f"[{task_id}] Error: {e}")
        hypothesis_tasks[task_id]["status"] = "failed"
        hypothesis_tasks[task_id]["error"] = str(e)
        hypothesis_tasks[task_id]["message"] = f"Error: {str(e)}"


@router.post("/generate")
async def generate_hypotheses(
    request: HypothesisGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate research hypotheses from multiple papers.
    
    Supports both Space PDFs (space_pdf_ids) and legacy materials (paper_ids).
    Requires at least 1 paper (2+ recommended for cross-paper insights).
    Returns a task_id for tracking progress.
    """
    # Check if at least one paper source is provided
    paper_ids = request.paper_ids or []
    space_pdf_ids = request.space_pdf_ids or []
    
    total_papers = len(paper_ids) + len(space_pdf_ids)
    if total_papers < 1:
        raise HTTPException(
            status_code=400,
            detail="At least 1 paper is required (provide paper_ids or space_pdf_ids)"
        )
    
    task_id = str(uuid.uuid4())
    
    hypothesis_tasks[task_id] = {
        "status": "pending",
        "progress": 0.0,
        "current_step": "queued",
        "message": "Starting hypothesis generation...",
        "error": None,
        "result": None,
        "use_agentic": request.use_agentic,  # Store agentic mode flag
    }
    
    background_tasks.add_task(
        process_hypothesis_generation,
        task_id,
        paper_ids,
        current_user["id"],
        request.focus_area,
        space_pdf_ids,
    )
    
    mode = "agentic (tool-using agents)" if request.use_agentic else "standard"
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": f"Hypothesis generation started ({mode})",
        "mode": mode,
    }


@router.post("/generate/upload")
async def generate_hypotheses_from_upload(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    focus_area: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate hypotheses from uploaded PDF files directly.
    """
    logger.info(f"Upload endpoint called with {len(files)} files")
    for i, f in enumerate(files):
        logger.info(f"File {i}: {f.filename}, content_type: {f.content_type}, size: {f.size if hasattr(f, 'size') else 'unknown'}")
    
    if len(files) < 1:
        logger.error("No files received in upload request")
        raise HTTPException(status_code=400, detail=f"At least 1 PDF file is required (received {len(files)} files)")
    
    task_id = str(uuid.uuid4())
    
    hypothesis_tasks[task_id] = {
        "status": "pending",
        "progress": 0.0,
        "current_step": "uploading",
        "message": "Processing uploaded files...",
        "error": None,
        "result": None,
    }
    
    # Read files
    papers = []
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            logger.warning(f"Skipping non-PDF file: {file.filename}")
            continue
            
        try:
            content_bytes = await file.read()
            
            # Ensure we have bytes, not string
            if isinstance(content_bytes, str):
                logger.error(f"File {file.filename} content is string, not bytes. Length: {len(content_bytes)}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"File upload error: {file.filename} was not uploaded correctly. Please try again."
                )
            
            logger.info(f"Processing {file.filename}: {len(content_bytes)} bytes")
            
            # Use simple PDF extraction
            text_content = extract_pdf_text(content_bytes)
            key_concepts = extract_key_concepts(text_content, top_k=15)
            
            papers.append({
                "id": str(uuid.uuid4()),
                "title": file.filename.replace('.pdf', ''),
                "content": text_content,
                "key_concepts": key_concepts,
            })
            logger.info(f"Successfully processed {file.filename}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process {file.filename}: {str(e)}"
            )
    
    if len(papers) < 1:
        raise HTTPException(status_code=400, detail="Could not process any PDF files")
    
    # Store user_id for the background task
    user_id = current_user["id"]
    
    # Start generation in background
    async def generate_from_papers():
        try:
            hypothesis_tasks[task_id]["status"] = "processing"
            hypothesis_tasks[task_id]["current_step"] = "generating"
            hypothesis_tasks[task_id]["progress"] = 0.2
            hypothesis_tasks[task_id]["message"] = "Analyzing papers and generating hypotheses..."
            
            agent = get_hypothesis_lab_agent()
            result = await agent.generate(papers, focus_area)
            
            hypothesis_tasks[task_id]["progress"] = 0.9
            hypothesis_tasks[task_id]["message"] = "Saving results..."
            
            # Save to database
            session_id = str(uuid.uuid4())
            supabase = get_supabase_service()
            
            session_data = {
                "id": session_id,
                "user_id": user_id,
                "paper_ids": [p["id"] for p in papers],
                "focus_area": focus_area,
                "hypotheses": result.get("hypotheses", []),
                "research_gaps": result.get("research_gaps", []),
                "claims": result.get("claims", []),
                "citations": result.get("citations", []),
                "concepts": result.get("concepts", []),
                "status": "completed",
                "created_at": datetime.utcnow().isoformat(),
            }
            
            try:
                supabase.admin_client.table("hypothesis_sessions").insert(session_data).execute()
                logger.info(f"[{task_id}] Saved session {session_id} to database")
            except Exception as e:
                logger.error(f"Error saving upload session: {e}")
            
            hypothesis_tasks[task_id]["status"] = "completed"
            hypothesis_tasks[task_id]["progress"] = 1.0
            hypothesis_tasks[task_id]["result"] = {
                "session_id": session_id,
                **result,
            }
            hypothesis_tasks[task_id]["message"] = "Complete!"
            
        except Exception as e:
            logger.error(f"[{task_id}] Upload generation error: {e}")
            hypothesis_tasks[task_id]["status"] = "failed"
            hypothesis_tasks[task_id]["error"] = str(e)
    
    background_tasks.add_task(generate_from_papers)
    
    return {
        "task_id": task_id,
        "status": "pending",
        "papers_processed": len(papers),
    }


@router.get("/status/{task_id}")
async def get_hypothesis_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the status of a hypothesis generation task."""
    if task_id in hypothesis_tasks:
        task = hypothesis_tasks[task_id]
        return {
            "task_id": task_id,
            "status": task["status"],
            "progress": task["progress"],
            "current_step": task["current_step"],
            "message": task.get("message"),
            "error": task.get("error"),
        }

    # Not in memory — check if session was already saved to DB (e.g. after server restart)
    try:
        supabase = get_supabase_service()
        db_result = supabase.admin_client.table("hypothesis_sessions") \
            .select("id, status") \
            .eq("task_id", task_id) \
            .eq("user_id", current_user["id"]) \
            .limit(1) \
            .execute()
        if db_result.data:
            session = db_result.data[0]
            return {
                "task_id": task_id,
                "status": session.get("status", "completed"),
                "progress": 1.0,
                "current_step": "done",
                "message": "Session already completed. Fetch results via /result/{task_id}.",
                "error": None,
            }
    except Exception as e:
        logger.warning(f"DB lookup for task_id {task_id} failed: {e}")

    # Task not found anywhere — return 'expired' so the frontend stops polling
    return {
        "task_id": task_id,
        "status": "expired",
        "progress": 0.0,
        "current_step": "not_found",
        "message": "Task no longer available (server may have restarted). Please start a new generation.",
        "error": None,
    }


@router.get("/result/{task_id}")
async def get_hypothesis_result(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the result of hypothesis generation."""
    if task_id not in hypothesis_tasks:
        # Try to fetch the completed session from DB (covers server-restart case)
        try:
            supabase = get_supabase_service()
            db_result = supabase.admin_client.table("hypothesis_sessions") \
                .select("*") \
                .eq("task_id", task_id) \
                .eq("user_id", current_user["id"]) \
                .limit(1) \
                .execute()
            if db_result.data:
                session = db_result.data[0]
                return {
                    "success": True,
                    "session_id": session["id"],
                    "hypotheses": session.get("hypotheses", []),
                    "research_gaps": session.get("research_gaps", []),
                    "claims": session.get("claims", []),
                    "citations": session.get("citations", []),
                    "concepts": session.get("concepts", []),
                }
        except Exception as e:
            logger.warning(f"DB result lookup for task_id {task_id} failed: {e}")
        raise HTTPException(status_code=404, detail="Task not found and no saved session exists for this task")
    
    task = hypothesis_tasks[task_id]
    
    if task["status"] == "processing":
        raise HTTPException(
            status_code=202,
            detail={
                "message": "Still processing",
                "progress": task["progress"],
                "current_step": task["current_step"],
            }
        )
    
    if task["status"] == "failed":
        raise HTTPException(
            status_code=500,
            detail=task.get("error", "Unknown error")
        )
    
    return task.get("result", {})


@router.get("/sessions")
async def list_hypothesis_sessions(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    """List all hypothesis sessions for the current user."""
    supabase = get_supabase_service()
    
    try:
        result = supabase.client.table("hypothesis_sessions")\
            .select("id, focus_area, status, created_at, hypotheses")\
            .eq("user_id", current_user["id"])\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        # Simplify hypotheses for list view
        sessions = []
        for session in result.data:
            hypotheses = session.get("hypotheses", [])
            sessions.append({
                "id": session["id"],
                "focus_area": session.get("focus_area"),
                "status": session["status"],
                "created_at": session["created_at"],
                "hypothesis_count": len(hypotheses),
                "top_hypothesis": hypotheses[0] if hypotheses else None,
            })
        
        return {"sessions": sessions}
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return {"sessions": []}


@router.get("/sessions/{session_id}")
async def get_hypothesis_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get full details of a hypothesis session."""
    supabase = get_supabase_service()
    
    try:
        result = supabase.client.table("hypothesis_sessions")\
            .select("*")\
            .eq("id", session_id)\
            .eq("user_id", current_user["id"])\
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_hypothesis_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a hypothesis session."""
    supabase = get_supabase_service()
    
    try:
        supabase.client.table("hypothesis_sessions")\
            .delete()\
            .eq("id", session_id)\
            .eq("user_id", current_user["id"])\
            .execute()
        
        return {"success": True, "message": "Session deleted"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/hypotheses/{hypothesis_id}/save")
async def save_hypothesis(
    session_id: str,
    hypothesis_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Save a specific hypothesis to user's collection."""
    supabase = get_supabase_service()
    
    try:
        # Get the session
        result = supabase.client.table("hypothesis_sessions")\
            .select("hypotheses")\
            .eq("id", session_id)\
            .eq("user_id", current_user["id"])\
            .single()\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Find the hypothesis
        hypothesis = next(
            (h for h in result.data["hypotheses"] if h["id"] == hypothesis_id),
            None
        )
        
        if not hypothesis:
            raise HTTPException(status_code=404, detail="Hypothesis not found")
        
        # Save to user's saved hypotheses
        saved = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "session_id": session_id,
            "hypothesis": hypothesis,
            "saved_at": datetime.utcnow().isoformat(),
            "notes": "",
        }
        
        supabase.client.table("saved_hypotheses").insert(saved).execute()
        
        return {"success": True, "saved_id": saved["id"]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/saved")
async def list_saved_hypotheses(
    current_user: dict = Depends(get_current_user),
):
    """List all saved hypotheses for the current user."""
    supabase = get_supabase_service()
    
    try:
        result = supabase.client.table("saved_hypotheses")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .order("saved_at", desc=True)\
            .execute()
        
        return {"saved_hypotheses": result.data}
        
    except Exception as e:
        logger.error(f"Error listing saved hypotheses: {e}")
        return {"saved_hypotheses": []}
