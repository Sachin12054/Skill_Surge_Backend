from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.services.tavus_service import (
    create_interview_persona,
    create_conversation,
    get_conversation,
    end_conversation,
)
from app.api.deps import get_current_user
import uuid

router = APIRouter(prefix="/interviews", tags=["Mock Interviews"])

# In-memory storage for demo (use Supabase in production)
interviews_db = {}


class InterviewRequest(BaseModel):
    type: str  # behavioral, technical, system-design
    targetRole: Optional[str] = "Senior Software Engineer"


class InterviewFeedback(BaseModel):
    interviewId: str
    communication: int
    technicalDepth: int
    problemSolving: int
    confidence: int
    overallScore: int
    strengths: list
    improvements: list


@router.post("/start")
async def start_interview(
    request: InterviewRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Start a mock interview session using Tavus CVI.
    
    Flow:
    1. Create (or reuse) a persona for this interview type
    2. Create a conversation with that persona
    3. Return the conversation URL for the frontend to embed
    """
    # Create a persona for this interview type
    persona = await create_interview_persona(request.type, request.targetRole)
    
    # Create a conversation with the persona
    user_name = f"User {current_user['id'][:8]}"
    
    conversation = await create_conversation(
        persona_id=persona.get("persona_id"),
        user_name=user_name,
        interview_type=request.type,
    )
    
    # Determine if this is demo mode
    is_demo = persona.get("demo", False) or conversation.get("status") in ["demo", "error"]
    
    # Store interview data
    interview_id = str(uuid.uuid4())
    
    interview_data = {
        "id": interview_id,
        "user_id": current_user["id"],
        "type": request.type,
        "target_role": request.targetRole,
        "conversation_id": conversation.get("conversation_id"),
        "conversation_url": conversation.get("conversation_url"),
        "status": "demo" if is_demo else "active",
        "created_at": datetime.utcnow().isoformat(),
        "duration": 0,
        "demo": is_demo,
    }
    
    interviews_db[interview_id] = interview_data
    
    return {
        "success": True,
        "interview": {
            "id": interview_id,
            "conversationUrl": conversation.get("conversation_url"),
            "type": request.type,
            "status": "demo" if is_demo else "active",
            "demo": is_demo,
            "message": conversation.get("message") if is_demo else "Interview ready! Click to join the video session.",
        },
    }


@router.get("/")
async def list_interviews(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
):
    """
    List all interviews for the current user.
    """
    # Filter in-memory interviews by user
    user_interviews = [
        interview for interview in interviews_db.values()
        if interview.get("user_id") == current_user["id"]
    ]
    
    # Sort by created_at descending
    user_interviews.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"interviews": user_interviews[:limit]}


@router.get("/{interview_id}")
async def get_interview(
    interview_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get interview details.
    """
    # Check in-memory storage
    if interview_id in interviews_db:
        interview = interviews_db[interview_id]
        if interview.get("user_id") == current_user["id"]:
            return interview
    
    # Not found or unauthorized
    raise HTTPException(status_code=404, detail="Interview not found")


@router.post("/{interview_id}/end")
async def end_interview_session(
    interview_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    End an interview session.
    """
    # Get interview to find conversation_id
    if interview_id not in interviews_db:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    interview = interviews_db[interview_id]
    if interview.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    conversation_id = interview.get("conversation_id", interview_id)
    
    result = await end_conversation(conversation_id)
    
    # Update status in memory
    interviews_db[interview_id]["status"] = "ended"
    
    return {"success": True, "result": result}


# Note: Feedback/analysis would require:
# 1. enable_recording: True in Tavus conversation (costs money)
# 2. Transcript extraction from Tavus API
# 3. LLM analysis of transcript for feedback
# Removed for now to avoid showing fake data
