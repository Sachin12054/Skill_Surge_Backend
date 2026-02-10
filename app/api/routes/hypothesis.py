from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.models import (
    HypothesisGenerateRequest,
    TaskResponse,
    HypothesisResultResponse,
    Hypothesis,
    ProcessingStatus,
)
from app.core import get_supabase_service
from app.agents import get_hypothesis_agent
from app.services import get_pdf_processor
from app.api.deps import get_current_user
import uuid
from typing import Dict
import time

router = APIRouter(prefix="/hypothesis", tags=["Hypothesis Lab"])

# In-memory task storage (use Redis in production)
tasks: Dict[str, dict] = {}


async def process_hypothesis(
    task_id: str,
    paper_ids: list,
    user_id: str,
    focus_area: str = None,
):
    """Background task to process hypothesis generation."""
    start_time = time.time()
    
    try:
        tasks[task_id]["status"] = ProcessingStatus.PROCESSING
        
        supabase = get_supabase_service()
        pdf_processor = get_pdf_processor()
        
        # Download and extract content from papers
        papers = []
        for paper_id in paper_ids:
            # Get material info
            result = await supabase.select("materials", "*", {"id": paper_id})
            if result.data:
                material = result.data[0]
                
                # Download PDF
                pdf_bytes = await supabase.download_file(
                    "course-materials",
                    material["file_path"]
                )
                
                # Extract text
                content = await pdf_processor.extract_text(pdf_bytes)
                
                papers.append({
                    "id": paper_id,
                    "title": material["title"],
                    "content": content,
                })
        
        if len(papers) < 2:
            raise ValueError("Need at least 2 papers for hypothesis generation")
        
        # Generate hypotheses
        agent = get_hypothesis_agent()
        result = await agent.generate(papers)
        
        processing_time = time.time() - start_time
        
        # Save hypotheses to database
        for hyp in result.get("hypotheses", []):
            await supabase.insert("hypotheses", {
                "user_id": user_id,
                "title": hyp["title"],
                "description": hyp["description"],
                "source_papers": paper_ids,
                "confidence_score": hyp.get("confidence", 0.5),
                "tags": hyp.get("source_concepts", []),
                "status": "draft",
            })
        
        tasks[task_id]["status"] = ProcessingStatus.COMPLETED
        tasks[task_id]["hypotheses"] = result.get("hypotheses", [])
        tasks[task_id]["processing_time"] = processing_time
        
    except Exception as e:
        tasks[task_id]["status"] = ProcessingStatus.FAILED
        tasks[task_id]["error"] = str(e)


@router.post("/generate", response_model=TaskResponse)
async def generate_hypotheses(
    request: HypothesisGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Generate research hypotheses from multiple papers."""
    if len(request.paper_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 papers required for hypothesis generation"
        )
    
    task_id = str(uuid.uuid4())
    
    tasks[task_id] = {
        "status": ProcessingStatus.PENDING,
        "hypotheses": [],
        "processing_time": 0,
        "error": None,
    }
    
    background_tasks.add_task(
        process_hypothesis,
        task_id,
        request.paper_ids,
        request.user_id,
        request.focus_area,
    )
    
    return TaskResponse(task_id=task_id, status=ProcessingStatus.PENDING)


@router.get("/result/{task_id}", response_model=HypothesisResultResponse)
async def get_hypothesis_result(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the result of hypothesis generation."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    if task["status"] == ProcessingStatus.PROCESSING:
        raise HTTPException(status_code=202, detail="Still processing")
    
    if task["status"] == ProcessingStatus.FAILED:
        raise HTTPException(status_code=500, detail=task.get("error", "Unknown error"))
    
    hypotheses = [
        Hypothesis(
            title=h["title"],
            description=h["description"],
            confidence=h.get("confidence", 0.5),
            source_concepts=h.get("source_concepts", []),
            methodology_hints=h.get("methodology_hints", []),
        )
        for h in task.get("hypotheses", [])
    ]
    
    return HypothesisResultResponse(
        hypotheses=hypotheses,
        processing_time=task.get("processing_time", 0),
    )


@router.get("/list")
async def list_hypotheses(
    current_user: dict = Depends(get_current_user),
):
    """List all hypotheses for the current user."""
    supabase = get_supabase_service()
    
    result = await supabase.select(
        "hypotheses",
        "*",
        {"user_id": current_user["id"]}
    )
    
    return {"hypotheses": result.data}
