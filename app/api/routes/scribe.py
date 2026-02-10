from fastapi import APIRouter, HTTPException, Depends
from app.models import (
    ScribeAnalyzeRequest,
    ScribeResponse,
)
from app.agents import get_scribe_agent
from app.core import get_supabase_service
from app.api.deps import get_current_user
import uuid

router = APIRouter(prefix="/scribe", tags=["Neuro-Scribe"])


@router.post("/analyze", response_model=ScribeResponse)
async def analyze_image(
    request: ScribeAnalyzeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Analyze an image and convert to code/math/diagram."""
    if request.type not in ["math", "code", "diagram"]:
        raise HTTPException(
            status_code=400,
            detail="Type must be 'math', 'code', or 'diagram'"
        )
    
    agent = get_scribe_agent()
    
    # Detect media type from base64 header if present
    media_type = "image/jpeg"
    if request.image.startswith("data:"):
        media_type = request.image.split(";")[0].split(":")[1]
        request.image = request.image.split(",")[1]
    
    result = await agent.analyze_image(
        request.image,
        request.type,
        media_type,
    )
    
    # Save to database
    supabase = get_supabase_service()
    await supabase.insert("scribe_outputs", {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "image_path": "",  # Could save image to storage
        "output_type": request.type,
        "output_content": result["result"],
        "format": result["format"],
        "confidence": result["confidence"],
    })
    
    return ScribeResponse(
        result=result["result"],
        format=result["format"],
        confidence=result["confidence"],
        suggestions=result.get("suggestions"),
    )


@router.post("/validate-math")
async def validate_math(
    latex: str,
    current_user: dict = Depends(get_current_user),
):
    """Validate LaTeX mathematical expression."""
    agent = get_scribe_agent()
    result = await agent.validate_math(latex)
    return result


@router.get("/history")
async def get_scribe_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """Get history of scribe outputs for the current user."""
    supabase = get_supabase_service()
    
    result = await supabase.select(
        "scribe_outputs",
        "*",
        {"user_id": current_user["id"]}
    )
    
    return {"outputs": result.data[:limit]}
