from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel
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
from typing import Dict, List, Optional
import asyncio


class PodcastGenerateRequest(BaseModel):
    space_pdf_ids: Optional[List[str]] = None  # list of space PDF UUIDs
    pdf_id: Optional[str] = None               # single space PDF UUID (convenience)

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
    """Calculate actual audio duration from WAV bytes using Python built-in wave module."""
    import wave, io
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return int(frames / rate) if rate > 0 else 0
    except Exception:
        # Fallback: estimate based on file size (WAV ≈ 176 KB/s at 22050Hz 16-bit mono)
        return int(len(audio_bytes) / 176400)


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
            # Upload audio to Supabase (upload_file is sync, no await)
            supabase = get_supabase_service()
            audio_path = f"{user_id}/podcasts/{task_id}.wav"
            supabase.upload_file(
                "generated-audio",
                audio_path,
                result["audio"],
                "audio/wav"
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


async def process_podcast_from_space_pdfs(
    task_id: str,
    pdf_ids: list,
    user_id: str,
):
    """Background task: download Space PDFs then generate podcast."""
    import traceback
    try:
        tasks[task_id]["status"] = ProcessingStatus.PROCESSING
        tasks[task_id]["progress"] = 10
        tasks[task_id]["message"] = "Downloading PDFs..."

        supabase = get_supabase_service()
        combined_bytes = b""
        for i, pdf_id in enumerate(pdf_ids):
            result = supabase.admin_client.table("space_pdfs") \
                .select("file_path, name") \
                .eq("id", pdf_id) \
                .eq("user_id", user_id) \
                .single() \
                .execute()
            if not result.data:
                raise ValueError(f"PDF {pdf_id} not found or access denied")
            combined_bytes += supabase.download_file("course-materials", result.data["file_path"])
            tasks[task_id]["progress"] = 10 + int(10 * (i + 1) / len(pdf_ids))
            print(f"[{task_id}] Downloaded PDF {i+1}/{len(pdf_ids)}: {result.data['name']}")

        # Reuse the main bytes processor from here
        await _run_podcast_generation(task_id, combined_bytes, user_id)

    except Exception as e:
        print(f"[{task_id}] Exception downloading space PDFs:")
        traceback.print_exc()
        tasks[task_id]["status"] = ProcessingStatus.FAILED
        tasks[task_id]["error"] = str(e)


async def _run_podcast_generation(task_id: str, pdf_bytes: bytes, user_id: str):
    """Core podcast generation logic shared by both entry points."""
    import traceback
    try:
        print(f"[{task_id}] Starting podcast generation...")
        tasks[task_id]["status"] = ProcessingStatus.PROCESSING
        tasks[task_id]["progress"] = 20

        print(f"[{task_id}] Calling podcast agent...")
        agent = get_podcast_agent()
        result = await agent.generate(pdf_bytes)

        print(f"[{task_id}] Agent result status: {result.get('status')}")
        print(f"[{task_id}] Agent result error: {result.get('error')}")

        tasks[task_id]["progress"] = 80

        if result["status"] == "completed" and result.get("audio"):
            print(f"[{task_id}] Audio generated, uploading to Supabase...")
            supabase = get_supabase_service()
            audio_path = f"{user_id}/podcasts/{task_id}.wav"
            supabase.upload_file("generated-audio", audio_path, result["audio"], "audio/wav")

            short_title = await generate_short_title(result.get("summary", ""))
            duration_seconds = get_audio_duration_seconds(result["audio"])
            print(f"[{task_id}] Audio duration: {duration_seconds} seconds")

            await supabase.insert("podcasts", {
                "id": task_id,
                "user_id": user_id,
                "material_id": None,
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


@router.post("/generate", response_model=TaskResponse)
async def generate_podcast_from_space(
    request: PodcastGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Generate a podcast from one or more Space PDFs (already stored in Supabase)."""
    pdf_ids = request.space_pdf_ids or ([request.pdf_id] if request.pdf_id else [])
    if not pdf_ids:
        raise HTTPException(status_code=400, detail="Provide space_pdf_ids or pdf_id")

    user_id = current_user["id"]
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": ProcessingStatus.PENDING,
        "progress": 5,
        "audio_url": None,
        "error": None,
    }

    # Kick off background task immediately — download + generate all happen in background
    background_tasks.add_task(
        process_podcast_from_space_pdfs,
        task_id,
        pdf_ids,
        user_id,
    )

    return TaskResponse(task_id=task_id, status=ProcessingStatus.PENDING)


@router.post("/upload", response_model=TaskResponse)
async def upload_and_create_podcast(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a PDF and create a podcast directly."""
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    pdf_bytes = await file.read()
    user_id = current_user["id"]

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
        
        # Download PDF from Supabase (download_file is sync, no await)
        supabase = get_supabase_service()
        pdf_bytes = supabase.download_file("course-materials", pdf_path)
        
        tasks[task_id]["progress"] = 20
        
        # Generate podcast
        agent = get_podcast_agent()
        result = await agent.generate(pdf_bytes)
        
        tasks[task_id]["progress"] = 80
        
        if result["status"] == "completed" and result["audio"]:
            # Upload audio to Supabase (upload_file is sync, no await)
            audio_path = f"{user_id}/podcasts/{task_id}.wav"
            supabase.upload_file(
                "generated-audio",
                audio_path,
                result["audio"],
                "audio/wav"
            )
            
            # Get title from summary
            title = result.get("summary", "")[:100] + "..."
            duration_seconds = get_audio_duration_seconds(result["audio"])
            
            # Save podcast record
            await supabase.insert("podcasts", {
                "id": task_id,
                "user_id": user_id,
                "material_id": task_id,  # Could link to actual material
                "title": title,
                "audio_path": audio_path,
                "duration": duration_seconds,
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
