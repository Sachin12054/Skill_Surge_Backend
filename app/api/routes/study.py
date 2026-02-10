from fastapi import APIRouter, HTTPException, Depends
from app.models import (
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizQuestion,
    AnswerSubmitRequest,
    AnswerResponse,
)
from app.agents import get_study_agent
from app.api.deps import get_current_user
from typing import Dict, List

router = APIRouter(prefix="/study", tags=["Study Loop"])

# In-memory quiz session storage (use Redis in production)
quiz_sessions: Dict[str, dict] = {}


@router.post("/quiz", response_model=QuizGenerateResponse)
async def generate_quiz(
    request: QuizGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate a quiz for the specified course/topic."""
    agent = get_study_agent()
    
    result = await agent.generate_quiz(
        user_id=current_user["id"],
        course_id=request.course_id,
        topic=request.topic_id or "general",
        difficulty=request.difficulty,
    )
    
    questions = [
        QuizQuestion(
            id=q["id"],
            question=q["question"],
            options=q["options"],
            correct=q["correct"],
            difficulty=q.get("difficulty", "medium"),
            topic=q.get("topic", "general"),
        )
        for q in result.get("questions", [])
    ]
    
    # Store session for answer evaluation
    session_id = f"{current_user['id']}_{request.course_id}"
    quiz_sessions[session_id] = {
        "questions": result.get("questions", []),
        "current_idx": 0,
    }
    
    return QuizGenerateResponse(questions=questions)


@router.post("/answer", response_model=AnswerResponse)
async def submit_answer(
    request: AnswerSubmitRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit an answer to a quiz question."""
    # Find the session containing this question
    session = None
    question_idx = 0
    
    for sid, sess in quiz_sessions.items():
        if sid.startswith(current_user["id"]):
            for idx, q in enumerate(sess["questions"]):
                if q["id"] == request.question_id:
                    session = sess
                    question_idx = idx
                    break
        if session:
            break
    
    if not session:
        raise HTTPException(status_code=404, detail="Question not found in active session")
    
    agent = get_study_agent()
    
    result = await agent.submit_answer(
        user_id=current_user["id"],
        questions=session["questions"],
        question_idx=question_idx,
        answer=request.answer,
    )
    
    return AnswerResponse(
        correct=result["correct"],
        explanation=result["explanation"],
        next_action=result["next_action"],
        memory_updated=result["memory_updated"],
    )


@router.get("/progress/{course_id}")
async def get_study_progress(
    course_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get study progress for a course."""
    from app.core import get_supabase_service
    supabase = get_supabase_service()
    
    # Get quiz sessions
    sessions = await supabase.select(
        "quiz_sessions",
        "*",
        {"user_id": current_user["id"], "course_id": course_id}
    )
    
    total_questions = sum(s["total_questions"] for s in sessions.data)
    correct_answers = sum(s["correct_answers"] for s in sessions.data)
    
    return {
        "total_sessions": len(sessions.data),
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "accuracy": correct_answers / total_questions if total_questions > 0 else 0,
    }


@router.get("/daily-drill")
async def get_daily_drill(
    current_user: dict = Depends(get_current_user),
):
    """Get personalized daily drill questions."""
    from app.core import get_supabase_service
    supabase = get_supabase_service()
    
    # Get user's struggle topics
    memory = await supabase.select(
        "user_memory",
        "*",
        {"user_id": current_user["id"], "memory_type": "struggle"}
    )
    
    struggle_topics = []
    if memory.data:
        struggle_topics = memory.data[0].get("content", {}).get("topics", [])[:5]
    
    agent = get_study_agent()
    
    # Generate questions focused on struggle areas
    all_questions = []
    for topic in struggle_topics[:3]:  # Limit topics
        result = await agent.generate_quiz(
            user_id=current_user["id"],
            course_id="daily_drill",
            topic=topic,
            difficulty="medium",
        )
        all_questions.extend(result.get("questions", [])[:2])  # 2 per topic
    
    return {
        "questions": all_questions[:5],  # Max 5 daily
        "focus_areas": struggle_topics,
    }
