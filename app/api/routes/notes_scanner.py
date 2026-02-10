"""
Notes Scanner API routes - Handwritten notes OCR using Google Vision API.
"""
from fastapi import APIRouter, HTTPException, Depends
from app.models import (
    NotesScanRequest,
    NotesScanResponse,
    ScannedNoteResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from app.services.vision_service import get_vision_service
from app.core import get_supabase_service
from app.core.openai import get_openai_service
from app.api.deps import get_current_user
from datetime import datetime
import uuid
import json

router = APIRouter(prefix="/notes-scanner", tags=["Notes Scanner"])


@router.post("/scan", response_model=NotesScanResponse)
async def scan_notes(
    request: NotesScanRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Scan handwritten notes from an image and extract text.
    
    - Accepts base64 encoded image (with or without data URI prefix)
    - Uses Google Vision API for handwriting recognition
    - Extracts keywords automatically
    - Saves to database with optional subject association
    """
    vision_service = get_vision_service()
    
    try:
        # Scan the image
        result = await vision_service.scan_handwritten_notes(
            image_base64=request.image,
            extract_keywords=True
        )
        
        if not result.full_text:
            raise HTTPException(
                status_code=400,
                detail="No text detected in the image. Please ensure the image contains readable handwritten or printed text."
            )
        
        # Generate ID and timestamp
        note_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        # Generate title if not provided
        title = request.title
        if not title:
            # Use first line or first few words as title
            first_line = result.full_text.split('\n')[0][:50]
            title = first_line if first_line else "Scanned Note"
        
        # Save to database
        supabase = get_supabase_service()
        await supabase.insert("scanned_notes", {
            "id": note_id,
            "user_id": current_user["id"],
            "title": title,
            "text": result.full_text,
            "keywords": result.detected_keywords,
            "subject_id": request.subject_id,
            "confidence": result.confidence,
            "language": result.language,
            "created_at": created_at.isoformat(),
        })
        
        return NotesScanResponse(
            id=note_id,
            text=result.full_text,
            keywords=result.detected_keywords,
            confidence=result.confidence,
            language=result.language,
            created_at=created_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan notes: {str(e)}"
        )


@router.get("/notes", response_model=dict)
async def get_scanned_notes(
    subject_id: str = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Get all scanned notes for the current user."""
    supabase = get_supabase_service()
    
    # Build query filters
    filters = {"user_id": current_user["id"]}
    if subject_id:
        filters["subject_id"] = subject_id
    
    result = await supabase.select(
        "scanned_notes",
        "*",
        filters
    )
    
    # Sort by created_at descending and apply pagination
    notes = sorted(
        result.data if result.data else [],
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )[offset:offset + limit]
    
    return {
        "notes": notes,
        "total": len(result.data) if result.data else 0
    }


@router.get("/notes/{note_id}", response_model=ScannedNoteResponse)
async def get_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific scanned note by ID."""
    supabase = get_supabase_service()
    
    result = await supabase.select(
        "scanned_notes",
        "*",
        {"id": note_id, "user_id": current_user["id"]}
    )
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Note not found")
    
    note = result.data[0]
    
    # Get subject name if subject_id exists
    subject_name = None
    if note.get("subject_id"):
        subject_result = await supabase.select(
            "subjects",
            "name",
            {"id": note["subject_id"]}
        )
        if subject_result.data:
            subject_name = subject_result.data[0].get("name")
    
    return ScannedNoteResponse(
        id=note["id"],
        title=note["title"],
        text=note["text"],
        keywords=note.get("keywords", []),
        subject_id=note.get("subject_id"),
        subject_name=subject_name,
        confidence=note.get("confidence", 0.0),
        image_path=note.get("image_path"),
        created_at=note["created_at"],
    )


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a scanned note."""
    supabase = get_supabase_service()
    
    # Verify ownership
    result = await supabase.select(
        "scanned_notes",
        "id",
        {"id": note_id, "user_id": current_user["id"]}
    )
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Note not found")
    
    await supabase.delete("scanned_notes", {"id": note_id})
    
    return {"success": True, "message": "Note deleted"}


@router.put("/notes/{note_id}")
async def update_note(
    note_id: str,
    title: str = None,
    text: str = None,
    subject_id: str = None,
    current_user: dict = Depends(get_current_user),
):
    """Update a scanned note (title, text, or subject)."""
    supabase = get_supabase_service()
    
    # Verify ownership
    result = await supabase.select(
        "scanned_notes",
        "id",
        {"id": note_id, "user_id": current_user["id"]}
    )
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Build update data
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if text is not None:
        update_data["text"] = text
    if subject_id is not None:
        update_data["subject_id"] = subject_id
    
    if update_data:
        await supabase.update("scanned_notes", update_data, {"id": note_id})
    
    return {"success": True, "message": "Note updated"}


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_notes(
    request: SummarizeRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Summarize and restructure scanned notes using AI.
    
    Styles:
    - structured: Clean sections with headings
    - bullet: Bullet point summary
    - outline: Hierarchical outline
    - cornell: Cornell note-taking format
    """
    if not request.text or len(request.text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Text is too short to summarize")
    
    openai = get_openai_service()
    
    style_instructions = {
        "structured": "Organize into clear sections with descriptive headings. Each section should have a heading and detailed content.",
        "bullet": "Create a concise bullet-point summary grouping related ideas under headings.",
        "outline": "Create a hierarchical outline with main topics, subtopics, and supporting details.",
        "cornell": "Format using the Cornell method: main notes section, cue/question column points, and a summary at the bottom.",
    }
    
    style = request.style if request.style in style_instructions else "structured"
    
    system_prompt = """You are an expert academic note organizer. Your task is to take raw scanned handwritten notes and restructure them into clean, well-organized notes.

Rules:
- Fix any OCR errors or garbled text
- Preserve all important information
- Add structure and clarity
- Keep academic terminology intact
- Be thorough but concise

You MUST respond with valid JSON only, no markdown fences."""
    
    user_prompt = f"""Restructure these scanned notes into well-organized study material.

Style: {style_instructions[style]}

Raw scanned text:
\"\"\"
{request.text}
\"\"\"

Respond in this exact JSON format:
{{
  "title": "A descriptive title for these notes",
  "sections": [
    {{
      "heading": "Section heading",
      "content": "Section content with proper formatting"
    }}
  ],
  "key_points": ["Key point 1", "Key point 2", "Key point 3"]
}}"""
    
    try:
        response = await openai.invoke(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=4096,
        )
        
        # Parse JSON response
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        
        data = json.loads(cleaned)
        
        # Build full summary text
        summary_parts = [f"# {data.get('title', 'Notes Summary')}\n"]
        for section in data.get("sections", []):
            summary_parts.append(f"\n## {section['heading']}\n{section['content']}")
        if data.get("key_points"):
            summary_parts.append("\n## Key Points")
            for point in data["key_points"]:
                summary_parts.append(f"• {point}")
        
        return SummarizeResponse(
            summary="\n".join(summary_parts),
            title=data.get("title", "Notes Summary"),
            sections=data.get("sections", []),
            key_points=data.get("key_points", []),
        )
        
    except json.JSONDecodeError:
        # Fallback: return raw AI response as single section
        return SummarizeResponse(
            summary=response,
            title="Notes Summary",
            sections=[{"heading": "Summary", "content": response}],
            key_points=[],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI summarization failed: {str(e)}")
