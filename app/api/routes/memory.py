from fastapi import APIRouter, HTTPException, Depends
from app.models import MemoryUpdateRequest, MemoryResponse
from app.core import get_supabase_service
from app.api.deps import get_current_user
from datetime import datetime

router = APIRouter(prefix="/memory", tags=["Total Recall"])


@router.get("/{user_id}", response_model=MemoryResponse)
async def get_user_memory(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get user's learning memory."""
    # Verify user is accessing their own memory
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    supabase = get_supabase_service()
    
    result = await supabase.select(
        "user_memory",
        "*",
        {"user_id": user_id}
    )
    
    memory = {}
    last_updated = datetime.now()
    
    for record in result.data:
        memory[record["memory_type"]] = record["content"]
        record_time = datetime.fromisoformat(record["updated_at"].replace("Z", "+00:00"))
        if record_time > last_updated:
            last_updated = record_time
    
    return MemoryResponse(memory=memory, last_updated=last_updated)


@router.post("/update")
async def update_user_memory(
    request: MemoryUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update user's learning memory."""
    if current_user["id"] != request.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    supabase = get_supabase_service()
    
    for memory_type, content in request.memory.items():
        await supabase.admin_client.table("user_memory").upsert({
            "user_id": request.user_id,
            "memory_type": memory_type,
            "content": content,
            "updated_at": datetime.now().isoformat(),
        }).execute()
    
    return {"success": True}


@router.get("/{user_id}/insights")
async def get_learning_insights(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get AI-generated insights from user's learning memory."""
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    supabase = get_supabase_service()
    
    # Get all memory
    result = await supabase.select(
        "user_memory",
        "*",
        {"user_id": user_id}
    )
    
    if not result.data:
        return {"insights": [], "recommendations": []}
    
    # Compile memory data
    memory = {}
    for record in result.data:
        memory[record["memory_type"]] = record["content"]
    
    # Generate insights using AI
    from app.core import get_bedrock_service
    bedrock = get_bedrock_service()
    
    prompt = f"""Analyze this student's learning data and provide insights.

Memory Data:
- Struggle areas: {memory.get('struggle', {})}
- Strength areas: {memory.get('strength', {})}
- Preferences: {memory.get('preference', {})}
- Goals: {memory.get('goal', {})}

Provide:
1. Key insights about the student's learning patterns
2. Specific recommendations for improvement
3. Suggested study strategies

Return a JSON object with:
- insights: array of insight strings
- recommendations: array of recommendation strings
- study_plan: brief suggested study approach

Return ONLY the JSON object."""

    response = await bedrock.invoke_claude(prompt, max_tokens=1000)
    
    try:
        import json
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        insights_data = json.loads(response)
        return insights_data
    except:
        return {
            "insights": ["Unable to generate insights at this time"],
            "recommendations": ["Continue studying consistently"],
            "study_plan": "Review materials regularly"
        }


@router.delete("/{user_id}")
async def clear_user_memory(
    user_id: str,
    memory_type: str = None,
    current_user: dict = Depends(get_current_user),
):
    """Clear user's learning memory (all or specific type)."""
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    supabase = get_supabase_service()
    
    if memory_type:
        await supabase.admin_client.table("user_memory").delete().eq(
            "user_id", user_id
        ).eq("memory_type", memory_type).execute()
    else:
        await supabase.admin_client.table("user_memory").delete().eq(
            "user_id", user_id
        ).execute()
    
    return {"success": True, "cleared": memory_type or "all"}
