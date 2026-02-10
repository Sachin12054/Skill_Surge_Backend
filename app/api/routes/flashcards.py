from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.core import get_supabase_service
from app.api.deps import get_current_user
import uuid
import json
import math
import boto3
from app.core.config import get_settings

router = APIRouter(prefix="/flashcards", tags=["Flashcards"])
settings = get_settings()


# ============ Pydantic Models ============

class FlashcardCreate(BaseModel):
    front: str
    back: str
    hint: Optional[str] = None
    tags: Optional[List[str]] = []


class FlashcardUpdate(BaseModel):
    front: Optional[str] = None
    back: Optional[str] = None
    hint: Optional[str] = None
    tags: Optional[List[str]] = None


class DeckCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subject_id: Optional[str] = None
    color: Optional[str] = "#6366F1"


class DeckUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class GenerateFlashcardsRequest(BaseModel):
    pdf_ids: List[str]
    deck_name: str
    num_cards: int = 20
    difficulty: str = "mixed"  # easy, medium, hard, mixed
    focus_topics: Optional[List[str]] = None


class ReviewSubmission(BaseModel):
    flashcard_id: str
    quality: int  # 0-5 SM-2 scale
    response_time_ms: Optional[int] = None


class StudySessionStart(BaseModel):
    deck_id: Optional[str] = None


class StudySessionEnd(BaseModel):
    session_id: str
    cards_studied: int
    cards_correct: int
    total_time_seconds: int


# ============ SM-2 Spaced Repetition Algorithm ============

def calculate_sm2(quality: int, repetitions: int, ease_factor: float, interval: int) -> tuple:
    """
    SM-2 Algorithm Implementation
    
    Quality responses:
    0 - Complete blackout
    1 - Incorrect but upon seeing answer, remembered
    2 - Incorrect but easy to recall
    3 - Correct with serious difficulty
    4 - Correct with some hesitation
    5 - Perfect response
    
    Returns: (new_repetitions, new_ease_factor, new_interval, status)
    """
    # Minimum ease factor
    MIN_EASE = 1.3
    
    if quality < 3:
        # Failed - reset repetitions
        new_repetitions = 0
        new_interval = 1
        new_ease = max(MIN_EASE, ease_factor - 0.2)
        status = 'learning'
    else:
        # Successful review
        new_repetitions = repetitions + 1
        
        # Update ease factor
        new_ease = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ease = max(MIN_EASE, new_ease)
        
        # Calculate new interval
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = int(interval * new_ease)
        
        # Determine status
        if new_interval >= 21:
            status = 'mastered'
        elif new_repetitions >= 2:
            status = 'reviewing'
        else:
            status = 'learning'
    
    return new_repetitions, new_ease, new_interval, status


# ============ AI Flashcard Generation ============

def get_bedrock_client():
    """Get AWS Bedrock client."""
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


async def generate_flashcards_from_content(
    content: str,
    num_cards: int,
    difficulty: str,
    focus_topics: Optional[List[str]] = None
) -> List[Dict]:
    """Generate flashcards using Claude AI."""
    
    difficulty_instructions = {
        "easy": "basic definitions, simple facts, and key terms",
        "medium": "concepts requiring understanding, relationships between ideas",
        "hard": "application, analysis, and synthesis questions",
        "mixed": "a mix of easy (30%), medium (50%), and hard (20%) questions"
    }
    
    topics_instruction = ""
    if focus_topics:
        topics_instruction = f"\nFocus especially on these topics: {', '.join(focus_topics)}"
    
    prompt = f"""Based on the following study material, generate exactly {num_cards} high-quality flashcards.

Difficulty level: {difficulty_instructions.get(difficulty, difficulty_instructions['mixed'])}
{topics_instruction}

Study Material:
{content[:30000]}

Generate flashcards that will help students memorize and understand the key concepts.
Each flashcard should have:
- "front": A clear question or term (be specific, avoid vague questions)
- "back": A concise but complete answer (include key details)
- "hint": An optional hint to help recall (can be null)
- "tags": 1-3 relevant topic tags

Return ONLY a valid JSON array of flashcard objects. Example format:
[
  {{"front": "What is photosynthesis?", "back": "The process by which plants convert sunlight, water, and CO2 into glucose and oxygen", "hint": "Think about what plants need to survive", "tags": ["biology", "plants"]}},
  ...
]

Important:
- Make questions specific and testable
- Answers should be complete but concise
- Avoid yes/no questions
- Include key terms, formulas, and definitions
- Generate exactly {num_cards} cards"""

    try:
        client = get_bedrock_client()
        
        response = client.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8000,
                "temperature": 0.7,
                "messages": [{"role": "user", "content": prompt}],
                "system": "You are an expert educator creating flashcards. Always return valid JSON arrays only, no other text."
            })
        )
        
        response_body = json.loads(response["body"].read())
        result_text = response_body["content"][0]["text"]
        
        # Parse JSON from response
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        flashcards = json.loads(result_text)
        return flashcards[:num_cards]
        
    except Exception as e:
        print(f"Error generating flashcards: {e}")
        # Return sample flashcards on error
        return [
            {
                "front": "What is the main topic of this material?",
                "back": "Review the uploaded content for key concepts",
                "hint": "Check the introduction",
                "tags": ["general"]
            }
        ]


# ============ Deck Endpoints ============

@router.get("/decks")
async def get_decks(user: dict = Depends(get_current_user)):
    """Get all flashcard decks for the current user."""
    supabase = get_supabase_service()
    
    result = supabase.admin_client.table("flashcard_decks").select(
        "*, subjects(name)"
    ).eq("user_id", user["id"]).order("updated_at", desc=True).execute()
    
    decks = []
    for d in result.data or []:
        # Get due cards count
        due_result = supabase.admin_client.table("flashcards").select(
            "id", count="exact"
        ).eq("deck_id", d["id"]).lte(
            "next_review_date", datetime.utcnow().isoformat()
        ).execute()
        
        decks.append({
            "id": d["id"],
            "name": d["name"],
            "description": d.get("description"),
            "subject_name": d.get("subjects", {}).get("name") if d.get("subjects") else None,
            "color": d.get("color", "#6366F1"),
            "card_count": d.get("card_count", 0),
            "mastered_count": d.get("mastered_count", 0),
            "due_count": due_result.count or 0,
            "created_at": d["created_at"],
            "updated_at": d["updated_at"],
        })
    
    return {"decks": decks}


@router.post("/decks")
async def create_deck(
    data: DeckCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new flashcard deck."""
    supabase = get_supabase_service()
    
    deck_id = str(uuid.uuid4())
    
    result = supabase.admin_client.table("flashcard_decks").insert({
        "id": deck_id,
        "user_id": user["id"],
        "name": data.name,
        "description": data.description,
        "subject_id": data.subject_id,
        "color": data.color,
    }).execute()
    
    return {
        "id": deck_id,
        "name": data.name,
        "description": data.description,
        "color": data.color,
        "card_count": 0,
        "mastered_count": 0,
        "due_count": 0,
    }


@router.get("/decks/{deck_id}")
async def get_deck(deck_id: str, user: dict = Depends(get_current_user)):
    """Get a specific deck with its cards."""
    supabase = get_supabase_service()
    
    # Get deck
    deck_result = supabase.admin_client.table("flashcard_decks").select(
        "*, subjects(name)"
    ).eq("id", deck_id).eq("user_id", user["id"]).single().execute()
    
    if not deck_result.data:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    deck = deck_result.data
    
    # Get cards
    cards_result = supabase.admin_client.table("flashcards").select("*").eq(
        "deck_id", deck_id
    ).order("created_at").execute()
    
    # Get due count
    due_result = supabase.admin_client.table("flashcards").select(
        "id", count="exact"
    ).eq("deck_id", deck_id).lte(
        "next_review_date", datetime.utcnow().isoformat()
    ).execute()
    
    return {
        "deck": {
            "id": deck["id"],
            "name": deck["name"],
            "description": deck.get("description"),
            "subject_name": deck.get("subjects", {}).get("name") if deck.get("subjects") else None,
            "color": deck.get("color", "#6366F1"),
            "card_count": deck.get("card_count", 0),
            "mastered_count": deck.get("mastered_count", 0),
            "due_count": due_result.count or 0,
        },
        "cards": [
            {
                "id": c["id"],
                "front": c["front"],
                "back": c["back"],
                "hint": c.get("hint"),
                "tags": c.get("tags", []),
                "status": c.get("status", "new"),
                "ease_factor": c.get("ease_factor", 2.5),
                "interval_days": c.get("interval_days", 0),
                "next_review_date": c.get("next_review_date"),
                "repetitions": c.get("repetitions", 0),
            }
            for c in cards_result.data or []
        ]
    }


@router.put("/decks/{deck_id}")
async def update_deck(
    deck_id: str,
    data: DeckUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a deck."""
    supabase = get_supabase_service()
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    result = supabase.admin_client.table("flashcard_decks").update(
        update_data
    ).eq("id", deck_id).eq("user_id", user["id"]).execute()
    
    return {"success": True}


@router.delete("/decks/{deck_id}")
async def delete_deck(deck_id: str, user: dict = Depends(get_current_user)):
    """Delete a deck and all its cards."""
    supabase = get_supabase_service()
    
    supabase.admin_client.table("flashcard_decks").delete().eq(
        "id", deck_id
    ).eq("user_id", user["id"]).execute()
    
    return {"success": True}


# ============ Flashcard Endpoints ============

@router.post("/decks/{deck_id}/cards")
async def create_card(
    deck_id: str,
    data: FlashcardCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new flashcard in a deck."""
    supabase = get_supabase_service()
    
    # Verify deck ownership
    deck = supabase.admin_client.table("flashcard_decks").select("id").eq(
        "id", deck_id
    ).eq("user_id", user["id"]).single().execute()
    
    if not deck.data:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    card_id = str(uuid.uuid4())
    
    result = supabase.admin_client.table("flashcards").insert({
        "id": card_id,
        "deck_id": deck_id,
        "user_id": user["id"],
        "front": data.front,
        "back": data.back,
        "hint": data.hint,
        "tags": data.tags or [],
        "next_review_date": datetime.utcnow().isoformat(),
    }).execute()
    
    return {
        "id": card_id,
        "front": data.front,
        "back": data.back,
        "hint": data.hint,
        "tags": data.tags,
        "status": "new",
    }


@router.put("/cards/{card_id}")
async def update_card(
    card_id: str,
    data: FlashcardUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a flashcard."""
    supabase = get_supabase_service()
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    result = supabase.admin_client.table("flashcards").update(
        update_data
    ).eq("id", card_id).eq("user_id", user["id"]).execute()
    
    return {"success": True}


@router.delete("/cards/{card_id}")
async def delete_card(card_id: str, user: dict = Depends(get_current_user)):
    """Delete a flashcard."""
    supabase = get_supabase_service()
    
    supabase.admin_client.table("flashcards").delete().eq(
        "id", card_id
    ).eq("user_id", user["id"]).execute()
    
    return {"success": True}


# ============ AI Generation Endpoint ============

@router.post("/generate")
async def generate_flashcards(
    data: GenerateFlashcardsRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Generate flashcards from PDFs using AI."""
    supabase = get_supabase_service()
    
    # Create the deck first
    deck_id = str(uuid.uuid4())
    
    supabase.admin_client.table("flashcard_decks").insert({
        "id": deck_id,
        "user_id": user["id"],
        "name": data.deck_name,
        "description": f"Auto-generated from {len(data.pdf_ids)} PDF(s)",
        "color": "#EC4899",
    }).execute()
    
    # Get PDF content
    combined_content = ""
    for pdf_id in data.pdf_ids:
        pdf_result = supabase.admin_client.table("space_pdfs").select("*").eq(
            "id", pdf_id
        ).eq("user_id", user["id"]).single().execute()
        
        if pdf_result.data:
            # Get text content if stored, otherwise use filename
            combined_content += f"\n\n--- From: {pdf_result.data['name']} ---\n"
            if pdf_result.data.get("extracted_text"):
                combined_content += pdf_result.data["extracted_text"]
            else:
                # Download and extract PDF text
                try:
                    pdf_bytes = supabase.download_file(
                        "course-materials", 
                        pdf_result.data["file_path"]
                    )
                    import fitz  # PyMuPDF
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    for page in doc:
                        combined_content += page.get_text()
                    doc.close()
                except Exception as e:
                    print(f"Error extracting PDF {pdf_id}: {e}")
                    combined_content += f"[Content from {pdf_result.data['name']}]"
    
    # Generate flashcards using AI
    flashcards = await generate_flashcards_from_content(
        combined_content,
        data.num_cards,
        data.difficulty,
        data.focus_topics
    )
    
    # Insert flashcards into database
    created_cards = []
    for card in flashcards:
        card_id = str(uuid.uuid4())
        supabase.admin_client.table("flashcards").insert({
            "id": card_id,
            "deck_id": deck_id,
            "user_id": user["id"],
            "front": card.get("front", ""),
            "back": card.get("back", ""),
            "hint": card.get("hint"),
            "tags": card.get("tags", []),
            "source_pdf_id": data.pdf_ids[0] if data.pdf_ids else None,
            "next_review_date": datetime.utcnow().isoformat(),
        }).execute()
        created_cards.append({
            "id": card_id,
            **card,
            "status": "new"
        })
    
    return {
        "success": True,
        "deck_id": deck_id,
        "deck_name": data.deck_name,
        "cards_created": len(created_cards),
        "cards": created_cards
    }


# ============ Study Session Endpoints ============

@router.get("/study/due")
async def get_due_cards(
    deck_id: Optional[str] = None,
    limit: int = 20,
    practice_mode: bool = False,
    user: dict = Depends(get_current_user)
):
    """Get cards due for review or all cards for practice mode."""
    supabase = get_supabase_service()
    
    query = supabase.admin_client.table("flashcards").select(
        "*, flashcard_decks(name, color)"
    ).eq("user_id", user["id"])
    
    # If practice_mode is False, only get cards due for review
    if not practice_mode:
        query = query.lte("next_review_date", datetime.utcnow().isoformat())
    
    query = query.order("next_review_date").limit(limit)
    
    if deck_id:
        query = query.eq("deck_id", deck_id)
    
    result = query.execute()
    
    cards = [
        {
            "id": c["id"],
            "deck_id": c["deck_id"],
            "deck_name": c.get("flashcard_decks", {}).get("name") if c.get("flashcard_decks") else None,
            "deck_color": c.get("flashcard_decks", {}).get("color") if c.get("flashcard_decks") else "#6366F1",
            "front": c["front"],
            "back": c["back"],
            "hint": c.get("hint"),
            "tags": c.get("tags", []),
            "status": c.get("status", "new"),
            "ease_factor": c.get("ease_factor", 2.5),
            "interval_days": c.get("interval_days", 0),
            "repetitions": c.get("repetitions", 0),
        }
        for c in result.data or []
    ]
    
    return {
        "due_count": len(cards),
        "cards": cards
    }


@router.post("/study/review")
async def submit_review(
    data: ReviewSubmission,
    user: dict = Depends(get_current_user)
):
    """Submit a review for a flashcard and update spaced repetition data."""
    supabase = get_supabase_service()
    
    # Get current card state
    card_result = supabase.admin_client.table("flashcards").select("*").eq(
        "id", data.flashcard_id
    ).eq("user_id", user["id"]).single().execute()
    
    if not card_result.data:
        raise HTTPException(status_code=404, detail="Card not found")
    
    card = card_result.data
    
    # Calculate new SM-2 values
    new_reps, new_ease, new_interval, new_status = calculate_sm2(
        quality=data.quality,
        repetitions=card.get("repetitions", 0),
        ease_factor=card.get("ease_factor", 2.5),
        interval=card.get("interval_days", 0)
    )
    
    # Calculate next review date
    next_review = datetime.utcnow() + timedelta(days=new_interval)
    
    # Record the review
    supabase.admin_client.table("flashcard_reviews").insert({
        "id": str(uuid.uuid4()),
        "flashcard_id": data.flashcard_id,
        "user_id": user["id"],
        "quality": data.quality,
        "response_time_ms": data.response_time_ms,
        "previous_interval": card.get("interval_days", 0),
        "previous_ease_factor": card.get("ease_factor", 2.5),
    }).execute()
    
    # Update the card
    supabase.admin_client.table("flashcards").update({
        "repetitions": new_reps,
        "ease_factor": new_ease,
        "interval_days": new_interval,
        "status": new_status,
        "next_review_date": next_review.isoformat(),
        "last_reviewed_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", data.flashcard_id).execute()
    
    return {
        "success": True,
        "new_status": new_status,
        "next_review_date": next_review.isoformat(),
        "interval_days": new_interval,
        "ease_factor": round(new_ease, 2),
    }


@router.post("/study/session/start")
async def start_study_session(
    data: StudySessionStart,
    user: dict = Depends(get_current_user)
):
    """Start a new study session."""
    supabase = get_supabase_service()
    
    session_id = str(uuid.uuid4())
    
    supabase.admin_client.table("flashcard_study_sessions").insert({
        "id": session_id,
        "user_id": user["id"],
        "deck_id": data.deck_id,
    }).execute()
    
    return {"session_id": session_id}


@router.post("/study/session/end")
async def end_study_session(
    data: StudySessionEnd,
    user: dict = Depends(get_current_user)
):
    """End a study session and record stats."""
    supabase = get_supabase_service()
    
    supabase.admin_client.table("flashcard_study_sessions").update({
        "cards_studied": data.cards_studied,
        "cards_correct": data.cards_correct,
        "total_time_seconds": data.total_time_seconds,
        "ended_at": datetime.utcnow().isoformat(),
    }).eq("id", data.session_id).eq("user_id", user["id"]).execute()
    
    return {"success": True}


# ============ Statistics Endpoints ============

@router.get("/stats")
async def get_flashcard_stats(user: dict = Depends(get_current_user)):
    """Get overall flashcard statistics."""
    supabase = get_supabase_service()
    
    # Total cards by status
    cards_result = supabase.admin_client.table("flashcards").select(
        "status"
    ).eq("user_id", user["id"]).execute()
    
    status_counts = {"new": 0, "learning": 0, "reviewing": 0, "mastered": 0}
    for card in cards_result.data or []:
        status = card.get("status", "new")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    total_cards = sum(status_counts.values())
    
    # Due today
    due_result = supabase.admin_client.table("flashcards").select(
        "id", count="exact"
    ).eq("user_id", user["id"]).lte(
        "next_review_date", datetime.utcnow().isoformat()
    ).execute()
    
    # Recent reviews (last 7 days)
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    reviews_result = supabase.admin_client.table("flashcard_reviews").select(
        "quality"
    ).eq("user_id", user["id"]).gte("reviewed_at", week_ago).execute()
    
    total_reviews = len(reviews_result.data or [])
    correct_reviews = sum(1 for r in (reviews_result.data or []) if r.get("quality", 0) >= 3)
    
    # Study streak (days with at least one review)
    sessions_result = supabase.admin_client.table("flashcard_study_sessions").select(
        "started_at"
    ).eq("user_id", user["id"]).order("started_at", desc=True).limit(30).execute()
    
    streak = 0
    if sessions_result.data:
        dates = set()
        for s in sessions_result.data:
            date = s["started_at"][:10]
            dates.add(date)
        
        # Count consecutive days from today
        check_date = datetime.utcnow().date()
        while check_date.isoformat() in dates:
            streak += 1
            check_date -= timedelta(days=1)
    
    return {
        "total_cards": total_cards,
        "status_counts": status_counts,
        "due_today": due_result.count or 0,
        "mastery_percentage": round(status_counts["mastered"] / total_cards * 100, 1) if total_cards > 0 else 0,
        "weekly_reviews": total_reviews,
        "weekly_accuracy": round(correct_reviews / total_reviews * 100, 1) if total_reviews > 0 else 0,
        "study_streak": streak,
    }
