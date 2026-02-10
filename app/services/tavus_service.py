import httpx
from app.core.config import get_settings
from typing import Optional

settings = get_settings()

TAVUS_BASE_URL = "https://tavusapi.com/v2"

# Use the user's existing Tavus persona (AI Interviewer)
EXISTING_PERSONA_ID = "pd968c80d651"
EXISTING_REPLICA_ID = "r4317e64d25a"

# Cache for created personas to avoid recreating them
_persona_cache: dict = {}


async def create_interview_persona(interview_type: str, target_role: str) -> dict:
    """
    Returns the existing Tavus persona for mock interviews.
    Uses the pre-created AI Interviewer persona.
    """
    if not settings.TAVUS_API_KEY or settings.TAVUS_API_KEY == "your_tavus_key":
        return {"persona_id": None, "name": f"{interview_type} Interviewer", "demo": True}
    
    # Return the existing persona - no need to create a new one
    return {
        "persona_id": EXISTING_PERSONA_ID,
        "name": "AI Interviewer",
        "demo": False
    }


async def create_conversation(persona_id: Optional[str], user_name: str, interview_type: str = "behavioral") -> dict:
    """
    Create a Tavus conversation (video interview session).
    
    Based on: https://docs.tavus.io/api-reference/conversations/create-conversation
    
    Returns a conversation_url that can be embedded in an iframe or opened directly.
    """
    if not settings.TAVUS_API_KEY or settings.TAVUS_API_KEY == "your_tavus_key" or not persona_id:
        # Return demo mode - user can still see the UI but without live video
        return {
            "conversation_id": "demo-conversation",
            "conversation_url": None,
            "status": "demo",
            "message": "Demo mode - Configure a valid Tavus API key for live AI video interviews.",
        }
    
    headers = {
        "x-api-key": settings.TAVUS_API_KEY,
        "Content-Type": "application/json",
    }
    
    # Custom greetings based on interview type
    greetings = {
        "behavioral": f"Hello {user_name}! I'm your behavioral interviewer today. Let's practice some common interview questions. When you're ready, tell me a bit about yourself and your background.",
        "technical": f"Hi {user_name}! I'm your technical interviewer. Today we'll work through some coding problems together. Don't worry about getting everything perfect - this is practice! Ready to start with a warm-up question?",
        "system-design": f"Welcome {user_name}! I'm here to help you practice system design interviews. We'll walk through designing a scalable system together. Let's start - what kind of systems have you worked with before?",
    }
    
    payload = {
        "persona_id": persona_id,
        "conversation_name": f"Cognito Interview - {user_name}",
        "conversational_context": f"""This is a mock interview practice session for {user_name}.
Help them prepare for real interviews by:
- Asking relevant, role-appropriate questions
- Providing hints when they get stuck (but not immediately)
- Giving constructive, actionable feedback
- Being encouraging while maintaining professional standards""",
        "custom_greeting": greetings.get(interview_type, greetings["behavioral"]),
        "properties": {
            "max_call_duration": 900,  # 15 minutes max
            "participant_left_timeout": 60,  # End call 60s after participant leaves
            "participant_absent_timeout": 120,  # End call if no one joins in 2 min
            "enable_recording": False,  # Disable to save costs
            "apply_greenscreen": False,
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{TAVUS_BASE_URL}/conversations",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "conversation_id": data.get("conversation_id"),
                "conversation_url": data.get("conversation_url"),
                "conversation_name": data.get("conversation_name"),
                "status": data.get("status", "active"),
            }
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            print(f"Tavus API HTTP error creating conversation: {e.response.status_code} - {error_detail}")
            return {
                "conversation_id": "demo-conversation",
                "conversation_url": None,
                "status": "error",
                "message": f"Tavus API error: {e.response.status_code}. Please check your API key and account limits.",
            }
        except Exception as e:
            print(f"Tavus API error creating conversation: {e}")
            return {
                "conversation_id": "demo-conversation",
                "conversation_url": None,
                "status": "error",
                "message": str(e),
            }


async def get_conversation(conversation_id: str) -> dict:
    """
    Get conversation details from Tavus.
    """
    if not settings.TAVUS_API_KEY or settings.TAVUS_API_KEY == "your_tavus_key" or conversation_id == "demo-conversation":
        return {
            "conversation_id": "demo-conversation",
            "status": "demo",
            "duration": 0,
        }
    
    headers = {
        "x-api-key": settings.TAVUS_API_KEY,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TAVUS_BASE_URL}/conversations/{conversation_id}",
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Tavus API error: {e}")
            return {"conversation_id": conversation_id, "status": "error"}


async def end_conversation(conversation_id: str) -> dict:
    """
    End a Tavus conversation.
    """
    if not settings.TAVUS_API_KEY or settings.TAVUS_API_KEY == "your_tavus_key" or conversation_id == "demo-conversation":
        return {"status": "ended", "conversation_id": conversation_id}
    
    headers = {
        "x-api-key": settings.TAVUS_API_KEY,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{TAVUS_BASE_URL}/conversations/{conversation_id}",
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return {"status": "ended", "conversation_id": conversation_id}
        except Exception as e:
            print(f"Tavus API error: {e}")
            return {"status": "error", "message": str(e)}


async def list_personas() -> list:
    """
    List all created personas for cleanup/reuse.
    """
    if not settings.TAVUS_API_KEY or settings.TAVUS_API_KEY == "your_tavus_key":
        return []
    
    headers = {
        "x-api-key": settings.TAVUS_API_KEY,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TAVUS_BASE_URL}/personas",
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            print(f"Tavus API error listing personas: {e}")
            return []
