from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from app.models import (
    PodcastCreateRequest,
    TaskResponse,
    PodcastStatusResponse,
    ProcessingStatus,
)
from app.core import get_supabase_service
from app.agents import get_podcast_agent
from app.api.deps import get_current_user
import uuid
from typing import Dict
import asyncio

router = APIRouter(prefix="/podcast", tags=["Neural Podcast"])

# In-memory task storage (use Redis in production)
tasks: Dict[str, dict] = {}


async def generate_short_title(summary: str) -> str:
    """Generate a short catchy podcast title from summary."""
    from app.core import get_openai_service
    
    try:
        llm = get_openai_service()
        title = await llm.invoke(
            f"Generate a short, catchy podcast title (max 5 words) for content about: {summary[:500]}",
            system_prompt="You are a podcast title generator. Create short, engaging titles. Return ONLY the title, nothing else.",
            max_tokens=50,
        )
        return title.strip().strip('"').strip("'")[:50]
    except:
        return "Study Session"


def get_audio_duration_seconds(audio_bytes: bytes) -> int:
    """Calculate actual audio duration from MP3 bytes."""
    try:
        # from pydub import AudioSegment  # Requires audioop - not available in Python 3.13
        # import io
        # audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        # return int(len(audio) / 1000)  # Duration in seconds
        
        # Fallback: estimate based on file size (rough estimate: 1 minute ≈ 1MB at 128kbps)
        estimated_minutes = len(audio_bytes) / (1024 * 1024)
        return int(estimated_minutes * 60)
    except:
        return 0


async def process_podcast_from_bytes(
    task_id: str,
    pdf_bytes: bytes,
    user_id: str,
):
    """Background task to process podcast generation from PDF bytes."""
    import traceback
    
    try:
        print(f"[{task_id}] Starting podcast generation...")
        tasks[task_id]["status"] = ProcessingStatus.PROCESSING
        tasks[task_id]["progress"] = 20
        
        # Generate podcast
        print(f"[{task_id}] Calling podcast agent...")
        agent = get_podcast_agent()
        result = await agent.generate(pdf_bytes)
        
        print(f"[{task_id}] Agent result status: {result.get('status')}")
        print(f"[{task_id}] Agent result error: {result.get('error')}")
        
        tasks[task_id]["progress"] = 80
        
        if result["status"] == "completed" and result.get("audio"):
            print(f"[{task_id}] Audio generated, uploading to Supabase...")
            # Upload audio to Supabase
            supabase = get_supabase_service()
            audio_path = f"{user_id}/podcasts/{task_id}.mp3"
            await supabase.upload_file(
                "generated-audio",
                audio_path,
                result["audio"],
                "audio/mpeg"
            )
            
            # Generate short catchy title
            short_title = await generate_short_title(result.get("summary", ""))
            
            # Calculate actual audio duration
            duration_seconds = get_audio_duration_seconds(result["audio"])
            print(f"[{task_id}] Audio duration: {duration_seconds} seconds")
            
            # Save podcast record
            await supabase.insert("podcasts", {
                "id": task_id,
                "user_id": user_id,
                "material_id": None,  # Set to null since we don't have a material record
                "title": short_title if short_title else "Study Session",
                "audio_path": audio_path,
                "duration": duration_seconds,
                "transcript": str(result.get("script", [])),
                "status": "completed",
            })
            
            tasks[task_id]["status"] = ProcessingStatus.COMPLETED
            tasks[task_id]["progress"] = 100
            tasks[task_id]["audio_url"] = audio_path
            print(f"[{task_id}] Podcast generation completed successfully!")
        else:
            error_msg = result.get("error", "Unknown error during podcast generation")
            print(f"[{task_id}] Podcast generation failed: {error_msg}")
            tasks[task_id]["status"] = ProcessingStatus.FAILED
            tasks[task_id]["error"] = error_msg
            
    except Exception as e:
        print(f"[{task_id}] Exception during podcast generation:")
        traceback.print_exc()
        tasks[task_id]["status"] = ProcessingStatus.FAILED
        tasks[task_id]["error"] = str(e)


@router.post("/upload", response_model=TaskResponse)
async def upload_and_create_podcast(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
):
    """Upload a PDF and create a podcast directly."""
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Read file content
    pdf_bytes = await file.read()
    
    task_id = str(uuid.uuid4())
    
    tasks[task_id] = {
        "status": ProcessingStatus.PENDING,
        "progress": 10,
        "audio_url": None,
        "error": None,
    }
    
    background_tasks.add_task(
        process_podcast_from_bytes,
        task_id,
        pdf_bytes,
        user_id,
    )
    
    return TaskResponse(task_id=task_id, status=ProcessingStatus.PENDING)


async def process_podcast(
    task_id: str,
    pdf_path: str,
    user_id: str,
):
    """Background task to process podcast generation."""
    try:
        tasks[task_id]["status"] = ProcessingStatus.PROCESSING
        tasks[task_id]["progress"] = 10
        
        # Download PDF from Supabase
        supabase = get_supabase_service()
        pdf_bytes = await supabase.download_file("course-materials", pdf_path)
        
        tasks[task_id]["progress"] = 20
        
        # Generate podcast
        agent = get_podcast_agent()
        result = await agent.generate(pdf_bytes)
        
        tasks[task_id]["progress"] = 80
        
        if result["status"] == "completed" and result["audio"]:
            # Upload audio to Supabase
            audio_path = f"{user_id}/podcasts/{task_id}.mp3"
            await supabase.upload_file(
                "generated-audio",
                audio_path,
                result["audio"],
                "audio/mpeg"
            )
            
            # Get title from summary
            title = result.get("summary", "")[:100] + "..."
            
            # Save podcast record
            await supabase.insert("podcasts", {
                "id": task_id,
                "user_id": user_id,
                "material_id": task_id,  # Could link to actual material
                "title": title,
                "audio_path": audio_path,
                "duration": len(result.get("script", [])) * 30,  # Estimate
                "transcript": str(result.get("script", [])),
                "status": "completed",
            })
            
            tasks[task_id]["status"] = ProcessingStatus.COMPLETED
            tasks[task_id]["progress"] = 100
            tasks[task_id]["audio_url"] = audio_path
        else:
            tasks[task_id]["status"] = ProcessingStatus.FAILED
            tasks[task_id]["error"] = result.get("error", "Unknown error")
            
    except Exception as e:
        tasks[task_id]["status"] = ProcessingStatus.FAILED
        tasks[task_id]["error"] = str(e)


@router.post("/create", response_model=TaskResponse)
async def create_podcast(
    request: PodcastCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Create a new podcast from a PDF."""
    task_id = str(uuid.uuid4())
    
    tasks[task_id] = {
        "status": ProcessingStatus.PENDING,
        "progress": 0,
        "audio_url": None,
        "error": None,
    }
    
    background_tasks.add_task(
        process_podcast,
        task_id,
        request.pdf_path,
        request.user_id,
    )
    
    return TaskResponse(task_id=task_id, status=ProcessingStatus.PENDING)


@router.get("/status/{task_id}", response_model=PodcastStatusResponse)
async def get_podcast_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the status of a podcast generation task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    return PodcastStatusResponse(
        status=task["status"],
        progress=task["progress"],
        audio_url=task.get("audio_url"),
        message=task.get("error"),
    )


@router.get("/list")
async def list_podcasts(
    current_user: dict = Depends(get_current_user),
):
    """List all podcasts for the current user."""
    supabase = get_supabase_service()
    
    result = await supabase.select(
        "podcasts",
        "*",
        {"user_id": current_user["id"]}
    )
    
    return {"podcasts": result.data}
