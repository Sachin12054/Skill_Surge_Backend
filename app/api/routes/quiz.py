from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core import get_supabase_service
from app.api.deps import get_current_user
import uuid
import json
import random
import boto3
import math
from openai import OpenAI
from app.core.config import get_settings

router = APIRouter(prefix="/quiz", tags=["Study Quiz"])
settings = get_settings()


# ============ Pydantic Models ============

class QuizConfig(BaseModel):
    pdf_ids: List[str]
    quiz_type: str  # "mcq", "true_false", "short_answer", "mixed"
    difficulty: str  # "easy", "medium", "hard", "adaptive"
    num_questions: int = 10
    time_limit: Optional[int] = None  # minutes
    topics: Optional[List[str]] = None
    adaptive_mode: bool = False


class QuizQuestion(BaseModel):
    id: str
    type: str  # "mcq", "true_false", "short_answer"
    question: str
    options: Optional[List[str]] = None  # For MCQ
    correct_answer: str
    explanation: str
    difficulty: int  # 1-5 scale
    topic: str
    points: int = 10


class QuizSubmission(BaseModel):
    quiz_id: str
    answers: Dict[str, str]  # question_id -> user_answer
    time_taken: int  # seconds


class AdaptiveResponse(BaseModel):
    question: QuizQuestion
    previous_performance: Dict[str, Any]
    recommended_topics: List[str]


# ============ Helper Functions ============

def get_bedrock_client():
    """Get AWS Bedrock client for AI generation."""
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def get_openai_client():
    """Get OpenAI client for embeddings."""
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def calculate_semantic_similarity(text1: str, text2: str, threshold: float = 0.80) -> tuple[bool, float]:
    """
    Calculate semantic similarity between two texts using OpenAI embeddings.
    Returns (is_similar, similarity_score).
    """
    try:
        client = get_openai_client()
        
        # Get embeddings for both texts
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=[text1.strip().lower(), text2.strip().lower()]
        )
        
        # Extract embeddings
        embedding1 = response.data[0].embedding
        embedding2 = response.data[1].embedding
        
        # Calculate cosine similarity (pure Python, no numpy needed)
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = math.sqrt(sum(a * a for a in embedding1))
        norm2 = math.sqrt(sum(b * b for b in embedding2))
        similarity = dot_product / (norm1 * norm2) if norm1 and norm2 else 0.0
        
        return similarity >= threshold, float(similarity)
    except Exception as e:
        print(f"Error calculating semantic similarity: {e}")
        # Fallback to simple string matching
        return text1.lower() in text2.lower() or text2.lower() in text1.lower(), 0.0


async def extract_text_from_pdfs(pdf_ids: List[str], user_id: str) -> tuple[str, Optional[str], Optional[str]]:
    """Extract text content from PDFs for quiz generation. Returns (content, subject_id, subject_name)."""
    supabase = get_supabase_service()
    
    combined_text = ""
    subject_id = None
    subject_name = None
    
    for pdf_id in pdf_ids:
        result = supabase.admin_client.table("space_pdfs").select("*, subjects(id, name)").eq(
            "id", pdf_id
        ).eq("user_id", user_id).execute()
        
        if result.data:
            pdf = result.data[0]
            # Get subject info from first PDF that has it
            if not subject_id and pdf.get("subjects"):
                subject_id = pdf["subjects"]["id"]
                subject_name = pdf["subjects"]["name"]
            elif not subject_id and pdf.get("subject_id"):
                # Fallback to just subject_id if join didn't work
                subject_id = pdf["subject_id"]
            
            try:
                # Download PDF content
                content = supabase.download_file("course-materials", pdf["file_path"])
                # For now, we'll use the filename as context
                # In production, use PyPDF2 or similar to extract text
                combined_text += f"\n\n--- Content from: {pdf['name']} ---\n"
                # Placeholder: actual PDF text extraction would go here
                combined_text += f"[PDF content from {pdf['name']}]"
            except Exception as e:
                print(f"Error extracting PDF {pdf_id}: {e}")
    
    return combined_text, subject_id, subject_name


async def generate_quiz_with_ai(
    content: str,
    config: QuizConfig,
    user_performance: Optional[Dict] = None
) -> List[dict]:
    """Generate quiz questions using Claude AI."""
    
    difficulty_prompts = {
        "easy": "basic understanding and recall",
        "medium": "application and analysis",
        "hard": "synthesis and evaluation",
        "adaptive": "varied difficulty based on topic importance"
    }
    
    type_instructions = {
        "mcq": "multiple choice questions with 4 options (A, B, C, D)",
        "true_false": "true/false questions",
        "short_answer": "short answer questions requiring 1-2 sentence responses",
        "mixed": "a mix of multiple choice, true/false, and short answer questions"
    }
    
    adaptive_context = ""
    if user_performance and config.adaptive_mode:
        weak_topics = user_performance.get("weak_topics", [])
        strong_topics = user_performance.get("strong_topics", [])
        subject_specific = user_performance.get("subject_specific", False)
        subject_name = user_performance.get("subject_name", "")
        
        performance_scope = f"in {subject_name}" if subject_specific else "across all subjects"
        
        adaptive_context = f"""
ADAPTIVE LEARNING CONTEXT ({performance_scope}):
- User struggles with: {', '.join(weak_topics) if weak_topics else 'No data yet'}
- User excels at: {', '.join(strong_topics) if strong_topics else 'No data yet'}
- Generate more questions on weak topics and harder questions on strong topics.
"""
    
    prompt = f"""You are an expert educational quiz generator. Generate a quiz based on the following content.

CONTENT:
{content[:15000]}

QUIZ REQUIREMENTS:
- Number of questions: {config.num_questions}
- Question type: {type_instructions.get(config.quiz_type, type_instructions['mixed'])}
- Difficulty level: {difficulty_prompts.get(config.difficulty, 'medium')}
{adaptive_context}

OUTPUT FORMAT (JSON array):
[
  {{
    "type": "mcq" | "true_false" | "short_answer",
    "question": "The question text",
    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],  // only for mcq
    "correct_answer": "A" | "True" | "The short answer",
    "explanation": "Why this is the correct answer",
    "difficulty": 1-5,
    "topic": "Topic/concept being tested",
    "points": 10
  }}
]

Generate exactly {config.num_questions} questions. Return ONLY valid JSON, no other text."""

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert educational quiz generator. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4096
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON from response
        questions = json.loads(content)
        
        # Add IDs to questions
        for q in questions:
            q["id"] = str(uuid.uuid4())
        
        return questions
        
    except Exception as e:
        print(f"AI generation error: {e}")
        # Return fallback questions if AI fails
        return generate_fallback_questions(config)


def generate_fallback_questions(config: QuizConfig) -> List[dict]:
    """Generate fallback questions if AI fails."""
    questions = []
    for i in range(config.num_questions):
        questions.append({
            "id": str(uuid.uuid4()),
            "type": "mcq",
            "question": f"Sample question {i+1} from your study materials",
            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
            "correct_answer": "A",
            "explanation": "This is a fallback question. Please try again.",
            "difficulty": 2,
            "topic": "General",
            "points": 10
        })
    return questions


def calculate_adaptive_difficulty(user_performance: Dict) -> int:
    """Calculate next question difficulty based on performance."""
    recent_correct = user_performance.get("recent_correct", 0)
    recent_total = user_performance.get("recent_total", 0)
    
    if recent_total == 0:
        return 3  # Start at medium
    
    accuracy = recent_correct / recent_total
    
    if accuracy >= 0.8:
        return min(5, user_performance.get("current_difficulty", 3) + 1)
    elif accuracy <= 0.4:
        return max(1, user_performance.get("current_difficulty", 3) - 1)
    else:
        return user_performance.get("current_difficulty", 3)


def analyze_performance(answers: Dict, questions: List[dict]) -> Dict:
    """Analyze quiz performance and identify weak/strong areas."""
    topic_scores = {}
    total_correct = 0
    total_points = 0
    earned_points = 0
    
    for q in questions:
        qid = q["id"]
        topic = q.get("topic", "General")
        points = q.get("points", 10)
        total_points += points
        
        if topic not in topic_scores:
            topic_scores[topic] = {"correct": 0, "total": 0, "points": 0}
        
        topic_scores[topic]["total"] += 1
        
        user_answer = answers.get(qid, "").strip().upper()
        correct_answer = str(q["correct_answer"]).strip().upper()
        
        # Handle different answer formats
        is_correct = False
        if q["type"] == "mcq":
            is_correct = user_answer == correct_answer[0] if correct_answer else False
        elif q["type"] == "true_false":
            is_correct = user_answer.lower() in ["true", "t", "yes"] if correct_answer.lower() in ["true", "t", "yes"] else user_answer.lower() in ["false", "f", "no"]
        else:
            # For short answer, use semantic similarity with OpenAI embeddings
            is_correct, similarity_score = calculate_semantic_similarity(user_answer, correct_answer)
            # Also accept if similarity is above 0.7 for partial matches
            if not is_correct and similarity_score >= 0.7:
                is_correct = True
        
        if is_correct:
            total_correct += 1
            topic_scores[topic]["correct"] += 1
            topic_scores[topic]["points"] += points
            earned_points += points
    
    # Identify weak and strong topics
    weak_topics = []
    strong_topics = []
    
    for topic, scores in topic_scores.items():
        accuracy = scores["correct"] / scores["total"] if scores["total"] > 0 else 0
        if accuracy < 0.5:
            weak_topics.append(topic)
        elif accuracy >= 0.8:
            strong_topics.append(topic)
    
    return {
        "total_correct": total_correct,
        "total_questions": len(questions),
        "accuracy": total_correct / len(questions) if questions else 0,
        "earned_points": earned_points,
        "total_points": total_points,
        "percentage": (earned_points / total_points * 100) if total_points > 0 else 0,
        "topic_scores": topic_scores,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
    }


# ============ In-memory storage for active quizzes ============
active_quizzes = {}


# ============ API Endpoints ============

@router.post("/generate")
async def generate_quiz(
    config: QuizConfig,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Generate a new quiz based on selected PDFs and configuration."""
    supabase = get_supabase_service()
    
    # Extract text from PDFs first to get subject info
    content, subject_id, subject_name = await extract_text_from_pdfs(config.pdf_ids, user["id"])
    
    # Get user's historical performance for adaptive mode
    user_performance = None
    if config.adaptive_mode:
        # First try to get subject-specific performance
        query = supabase.admin_client.table("quiz_performance").select(
            "quiz_performance.*, quizzes!inner(subject_id, subject_name)"
        ).eq("user_id", user["id"]).order("created_at", desc=True)
        
        # Filter by subject if available
        if subject_id:
            query = query.eq("quizzes.subject_id", subject_id)
            perf_result = query.limit(10).execute()
            
            # Fall back to overall performance if no subject-specific history
            if not perf_result.data or len(perf_result.data) < 3:
                perf_result = supabase.admin_client.table("quiz_performance").select("*").eq(
                    "user_id", user["id"]
                ).order("created_at", desc=True).limit(10).execute()
        else:
            # No subject info, use overall performance
            perf_result = supabase.admin_client.table("quiz_performance").select("*").eq(
                "user_id", user["id"]
            ).order("created_at", desc=True).limit(10).execute()
        
        if perf_result.data:
            # Aggregate performance data
            all_weak = []
            all_strong = []
            for p in perf_result.data:
                all_weak.extend(p.get("weak_topics", []))
                all_strong.extend(p.get("strong_topics", []))
            
            user_performance = {
                "weak_topics": list(set(all_weak)),
                "strong_topics": list(set(all_strong)),
                "subject_specific": bool(subject_id and len(perf_result.data) >= 3),
                "subject_name": subject_name,
            }
    
    # Generate quiz with AI
    questions = await generate_quiz_with_ai(content, config, user_performance)
    
    # Create quiz record
    quiz_id = str(uuid.uuid4())
    quiz_data = {
        "id": quiz_id,
        "user_id": user["id"],
        "pdf_ids": config.pdf_ids,
        "quiz_type": config.quiz_type,
        "difficulty": config.difficulty,
        "num_questions": len(questions),
        "time_limit": config.time_limit,
        "adaptive_mode": config.adaptive_mode,
        "questions": questions,
        "status": "active",
        "subject_id": subject_id,
        "subject_name": subject_name,
        "user_answers": {},
        "detailed_results": [],
        "current_question_index": 0,
        "time_spent": 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Store in database
    supabase.admin_client.table("quizzes").insert(quiz_data).execute()
    
    # Store in memory for quick access
    active_quizzes[quiz_id] = quiz_data
    
    # Return quiz without correct answers
    safe_questions = []
    for q in questions:
        safe_q = {k: v for k, v in q.items() if k not in ["correct_answer", "explanation"]}
        safe_questions.append(safe_q)
    
    return {
        "quiz_id": quiz_id,
        "questions": safe_questions,
        "time_limit": config.time_limit,
        "total_points": sum(q.get("points", 10) for q in questions),
    }


@router.post("/submit")
async def submit_quiz(
    submission: QuizSubmission,
    user: dict = Depends(get_current_user),
):
    """Submit quiz answers and get results with adaptive feedback."""
    supabase = get_supabase_service()
    
    # Get quiz data
    quiz = active_quizzes.get(submission.quiz_id)
    if not quiz:
        result = supabase.admin_client.table("quizzes").select("*").eq(
            "id", submission.quiz_id
        ).eq("user_id", user["id"]).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Quiz not found")
        quiz = result.data[0]
    
    questions = quiz["questions"]
    
    # Analyze performance
    performance = analyze_performance(submission.answers, questions)
    
    # Generate detailed results
    detailed_results = []
    for q in questions:
        qid = q["id"]
        user_answer = submission.answers.get(qid, "")
        correct_answer = q["correct_answer"]
        
        # Check if correct
        is_correct = False
        if q["type"] == "mcq":
            is_correct = user_answer.upper() == correct_answer[0].upper()
        elif q["type"] == "true_false":
            is_correct = user_answer.lower() == correct_answer.lower()
        else:
            # For short answer, use semantic similarity with OpenAI embeddings
            is_correct, _ = calculate_semantic_similarity(user_answer, correct_answer)
        
        detailed_results.append({
            "question_id": qid,
            "question": q["question"],
            "type": q["type"],
            "options": q.get("options"),
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": q["explanation"],
            "topic": q.get("topic", "General"),
            "points_earned": q.get("points", 10) if is_correct else 0,
            "points_possible": q.get("points", 10),
        })
    
    # Save performance record
    perf_record = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "quiz_id": submission.quiz_id,
        "accuracy": performance["accuracy"],
        "percentage": performance["percentage"],
        "earned_points": performance["earned_points"],
        "total_points": performance["total_points"],
        "time_taken": submission.time_taken,
        "weak_topics": performance["weak_topics"],
        "strong_topics": performance["strong_topics"],
        "topic_scores": performance["topic_scores"],
        "created_at": datetime.utcnow().isoformat(),
    }
    
    supabase.admin_client.table("quiz_performance").insert(perf_record).execute()
    
    # Update quiz status and save full quiz data
    supabase.admin_client.table("quizzes").update({
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat(),
        "user_answers": submission.answers,
        "detailed_results": detailed_results,
        "time_spent": submission.time_taken,
    }).eq("id", submission.quiz_id).execute()
    
    # Generate adaptive recommendations
    recommendations = generate_recommendations(performance)
    
    return {
        "quiz_id": submission.quiz_id,
        "score": {
            "correct": performance["total_correct"],
            "total": performance["total_questions"],
            "percentage": round(performance["percentage"], 1),
            "earned_points": performance["earned_points"],
            "total_points": performance["total_points"],
        },
        "time_taken": submission.time_taken,
        "detailed_results": detailed_results,
        "performance": {
            "weak_topics": performance["weak_topics"],
            "strong_topics": performance["strong_topics"],
            "topic_breakdown": performance["topic_scores"],
        },
        "recommendations": recommendations,
    }


def generate_recommendations(performance: Dict) -> Dict:
    """Generate AI-powered learning recommendations."""
    weak_topics = performance.get("weak_topics", [])
    strong_topics = performance.get("strong_topics", [])
    accuracy = performance.get("accuracy", 0)
    
    recommendations = {
        "focus_areas": weak_topics,
        "mastered_areas": strong_topics,
        "suggested_actions": [],
        "next_difficulty": "medium",
    }
    
    if accuracy < 0.5:
        recommendations["suggested_actions"] = [
            "Review the source materials for weak topics",
            "Try an easier quiz to build confidence",
            "Focus on one topic at a time",
        ]
        recommendations["next_difficulty"] = "easy"
    elif accuracy < 0.7:
        recommendations["suggested_actions"] = [
            "Good progress! Focus on understanding weak areas",
            "Try explaining concepts in your own words",
            "Take another quiz with adaptive mode enabled",
        ]
        recommendations["next_difficulty"] = "medium"
    elif accuracy < 0.9:
        recommendations["suggested_actions"] = [
            "Great job! Challenge yourself with harder questions",
            "Try teaching these concepts to solidify understanding",
            "Explore advanced topics in your strong areas",
        ]
        recommendations["next_difficulty"] = "hard"
    else:
        recommendations["suggested_actions"] = [
            "Excellent! You've mastered this material",
            "Consider moving to new topics",
            "Help others learn these concepts",
        ]
        recommendations["next_difficulty"] = "hard"
    
    return recommendations


@router.get("/next-adaptive")
async def get_next_adaptive_question(
    quiz_id: str,
    current_question_index: int,
    user: dict = Depends(get_current_user),
):
    """Get next question in adaptive mode based on current performance."""
    supabase = get_supabase_service()
    
    # Get quiz
    result = supabase.admin_client.table("quizzes").select("*").eq(
        "id", quiz_id
    ).eq("user_id", user["id"]).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz = result.data[0]
    questions = quiz["questions"]
    
    if current_question_index >= len(questions):
        return {"completed": True, "message": "Quiz completed"}
    
    # Get current session performance
    session_result = supabase.admin_client.table("quiz_sessions").select("*").eq(
        "quiz_id", quiz_id
    ).eq("user_id", user["id"]).execute()
    
    current_difficulty = 3
    if session_result.data:
        session = session_result.data[0]
        performance = {
            "recent_correct": session.get("correct_count", 0),
            "recent_total": session.get("total_answered", 0),
            "current_difficulty": session.get("current_difficulty", 3),
        }
        current_difficulty = calculate_adaptive_difficulty(performance)
    
    # Select next question based on difficulty
    available_questions = [q for q in questions[current_question_index:] if q.get("difficulty", 3) == current_difficulty]
    
    if not available_questions:
        available_questions = questions[current_question_index:]
    
    next_question = available_questions[0] if available_questions else None
    
    if not next_question:
        return {"completed": True, "message": "No more questions"}
    
    # Return question without answer
    safe_question = {k: v for k, v in next_question.items() if k not in ["correct_answer", "explanation"]}
    
    return {
        "question": safe_question,
        "question_number": current_question_index + 1,
        "total_questions": len(questions),
        "current_difficulty": current_difficulty,
    }


@router.post("/answer-adaptive")
async def submit_adaptive_answer(
    quiz_id: str,
    question_id: str,
    answer: str,
    user: dict = Depends(get_current_user),
):
    """Submit answer for adaptive quiz and get immediate feedback."""
    supabase = get_supabase_service()
    
    # Get quiz
    result = supabase.admin_client.table("quizzes").select("*").eq(
        "id", quiz_id
    ).eq("user_id", user["id"]).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz = result.data[0]
    question = next((q for q in quiz["questions"] if q["id"] == question_id), None)
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Check answer
    is_correct = False
    if question["type"] == "mcq":
        is_correct = answer.upper() == question["correct_answer"][0].upper()
    elif question["type"] == "true_false":
        is_correct = answer.lower() == question["correct_answer"].lower()
    else:
        # For short answer, use semantic similarity with OpenAI embeddings
        is_correct, _ = calculate_semantic_similarity(answer, question["correct_answer"])
    
    # Update session performance
    session_result = supabase.admin_client.table("quiz_sessions").select("*").eq(
        "quiz_id", quiz_id
    ).eq("user_id", user["id"]).execute()
    
    if session_result.data:
        session = session_result.data[0]
        supabase.admin_client.table("quiz_sessions").update({
            "correct_count": session.get("correct_count", 0) + (1 if is_correct else 0),
            "total_answered": session.get("total_answered", 0) + 1,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", session["id"]).execute()
    else:
        supabase.admin_client.table("quiz_sessions").insert({
            "id": str(uuid.uuid4()),
            "quiz_id": quiz_id,
            "user_id": user["id"],
            "correct_count": 1 if is_correct else 0,
            "total_answered": 1,
            "current_difficulty": question.get("difficulty", 3),
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    
    return {
        "is_correct": is_correct,
        "correct_answer": question["correct_answer"],
        "explanation": question["explanation"],
        "points_earned": question.get("points", 10) if is_correct else 0,
        "topic": question.get("topic", "General"),
    }


@router.get("/history")
async def get_quiz_history(
    limit: int = 10,
    user: dict = Depends(get_current_user),
):
    """Get user's quiz history and performance trends."""
    supabase = get_supabase_service()
    
    # Get recent quizzes
    quizzes = supabase.admin_client.table("quizzes").select(
        "id, quiz_type, difficulty, num_questions, status, subject_name, created_at, completed_at"
    ).eq("user_id", user["id"]).order("created_at", desc=True).limit(limit).execute()
    
    # Get performance records
    performance = supabase.admin_client.table("quiz_performance").select("*").eq(
        "user_id", user["id"]
    ).order("created_at", desc=True).limit(limit).execute()
    
    # Calculate overall stats
    total_quizzes = len(performance.data) if performance.data else 0
    avg_accuracy = 0
    all_weak_topics = []
    all_strong_topics = []
    
    if performance.data:
        avg_accuracy = sum(p.get("accuracy", 0) for p in performance.data) / total_quizzes
        for p in performance.data:
            all_weak_topics.extend(p.get("weak_topics", []))
            all_strong_topics.extend(p.get("strong_topics", []))
    
    # Count topic frequencies
    weak_topic_counts = {}
    strong_topic_counts = {}
    
    for t in all_weak_topics:
        weak_topic_counts[t] = weak_topic_counts.get(t, 0) + 1
    for t in all_strong_topics:
        strong_topic_counts[t] = strong_topic_counts.get(t, 0) + 1
    
    return {
        "quizzes": quizzes.data or [],
        "performance_history": performance.data or [],
        "overall_stats": {
            "total_quizzes": total_quizzes,
            "average_accuracy": round(avg_accuracy * 100, 1),
            "persistent_weak_topics": sorted(weak_topic_counts.items(), key=lambda x: -x[1])[:5],
            "persistent_strong_topics": sorted(strong_topic_counts.items(), key=lambda x: -x[1])[:5],
        },
    }


@router.get("/topics")
async def get_available_topics(
    pdf_ids: str,  # Comma-separated
    user: dict = Depends(get_current_user),
):
    """Get available topics from selected PDFs for quiz customization."""
    pdf_id_list = pdf_ids.split(",")
    
    # For now, return common educational topics
    # In production, this would extract topics from PDF content using NLP
    topics = [
        "Key Concepts",
        "Definitions",
        "Applications",
        "Theory",
        "Examples",
        "Formulas",
        "History",
        "Comparisons",
    ]
    
    return {"topics": topics, "pdf_count": len(pdf_id_list)}


@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a quiz and all associated data."""
    supabase = get_supabase_service()
    
    # Verify quiz exists and belongs to user
    result = supabase.admin_client.table("quizzes").select("id").eq(
        "id", quiz_id
    ).eq("user_id", user["id"]).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Delete in order: sessions, performance, then quiz
    supabase.admin_client.table("quiz_sessions").delete().eq("quiz_id", quiz_id).execute()
    supabase.admin_client.table("quiz_performance").delete().eq("quiz_id", quiz_id).execute()
    supabase.admin_client.table("quizzes").delete().eq("id", quiz_id).execute()
    
    # Remove from active quizzes cache
    if quiz_id in active_quizzes:
        del active_quizzes[quiz_id]
    
    return {"success": True, "message": "Quiz deleted successfully"}


@router.get("/{quiz_id}/resume")
async def resume_quiz(
    quiz_id: str,
    user: dict = Depends(get_current_user),
):
    """Resume an incomplete quiz from where user left off."""
    supabase = get_supabase_service()
    
    # Get quiz with full data
    result = supabase.admin_client.table("quizzes").select("*").eq(
        "id", quiz_id
    ).eq("user_id", user["id"]).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz = result.data[0]
    
    if quiz.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Quiz already completed")
    
    questions = quiz.get("questions", [])
    user_answers = quiz.get("user_answers", {})
    current_index = quiz.get("current_question_index", 0)
    time_spent = quiz.get("time_spent", 0)
    
    # Prepare safe questions (without answers)
    safe_questions = []
    for q in questions:
        safe_q = {k: v for k, v in q.items() if k not in ["correct_answer", "explanation"]}
        safe_questions.append(safe_q)
    
    return {
        "quiz_id": quiz_id,
        "questions": safe_questions,
        "user_answers": user_answers,
        "current_question_index": current_index,
        "time_spent": time_spent,
        "time_limit": quiz.get("time_limit"),
        "total_points": sum(q.get("points", 10) for q in questions),
        "status": quiz.get("status", "active"),
    }


@router.post("/{quiz_id}/save-progress")
async def save_quiz_progress(
    quiz_id: str,
    current_question_index: int,
    time_spent: int,
    user_answers: Dict[str, str],
    user: dict = Depends(get_current_user),
):
    """Save quiz progress for later resumption."""
    supabase = get_supabase_service()
    
    # Verify quiz exists and belongs to user
    result = supabase.admin_client.table("quizzes").select("id, status").eq(
        "id", quiz_id
    ).eq("user_id", user["id"]).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    if result.data[0].get("status") == "completed":
        raise HTTPException(status_code=400, detail="Cannot save progress for completed quiz")
    
    # Update quiz with progress
    supabase.admin_client.table("quizzes").update({
        "current_question_index": current_question_index,
        "time_spent": time_spent,
        "user_answers": user_answers,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", quiz_id).execute()
    
    return {"success": True, "message": "Progress saved"}


@router.get("/subjects/insights")
async def get_subject_insights(
    user: dict = Depends(get_current_user),
):
    """Get subject-wise quiz performance insights."""
    supabase = get_supabase_service()
    
    # Get all quizzes with performance data grouped by subject
    quizzes = supabase.admin_client.table("quizzes").select(
        "id, subject_id, subject_name, status, created_at, completed_at"
    ).eq("user_id", user["id"]).order("created_at", desc=True).execute()
    
    performance = supabase.admin_client.table("quiz_performance").select("*").eq(
        "user_id", user["id"]
    ).execute()
    
    # Create a map of quiz_id to performance
    perf_map = {p["quiz_id"]: p for p in (performance.data or [])}
    
    # Group by subject
    subject_data = {}
    
    for quiz in (quizzes.data or []):
        subject_name = quiz.get("subject_name") or "General"
        subject_id = quiz.get("subject_id")
        
        if subject_name not in subject_data:
            subject_data[subject_name] = {
                "subject_id": subject_id,
                "subject_name": subject_name,
                "total_quizzes": 0,
                "completed_quizzes": 0,
                "in_progress_quizzes": 0,
                "total_accuracy": 0,
                "total_points_earned": 0,
                "total_points_possible": 0,
                "weak_topics": [],
                "strong_topics": [],
                "quizzes": [],
            }
        
        subject_data[subject_name]["total_quizzes"] += 1
        
        if quiz.get("status") == "completed":
            subject_data[subject_name]["completed_quizzes"] += 1
            
            # Add performance data if available
            perf = perf_map.get(quiz["id"])
            if perf:
                subject_data[subject_name]["total_accuracy"] += perf.get("accuracy", 0)
                subject_data[subject_name]["total_points_earned"] += perf.get("earned_points", 0)
                subject_data[subject_name]["total_points_possible"] += perf.get("total_points", 0)
                subject_data[subject_name]["weak_topics"].extend(perf.get("weak_topics", []))
                subject_data[subject_name]["strong_topics"].extend(perf.get("strong_topics", []))
        else:
            subject_data[subject_name]["in_progress_quizzes"] += 1
        
        subject_data[subject_name]["quizzes"].append({
            "id": quiz["id"],
            "status": quiz.get("status"),
            "created_at": quiz.get("created_at"),
            "completed_at": quiz.get("completed_at"),
            "performance": perf_map.get(quiz["id"]),
        })
    
    # Calculate averages and get top topics
    subjects = []
    for name, data in subject_data.items():
        completed = data["completed_quizzes"]
        avg_accuracy = (data["total_accuracy"] / completed * 100) if completed > 0 else 0
        
        # Count topic frequencies
        weak_counts = {}
        strong_counts = {}
        for t in data["weak_topics"]:
            weak_counts[t] = weak_counts.get(t, 0) + 1
        for t in data["strong_topics"]:
            strong_counts[t] = strong_counts.get(t, 0) + 1
        
        subjects.append({
            "subject_id": data["subject_id"],
            "subject_name": name,
            "total_quizzes": data["total_quizzes"],
            "completed_quizzes": completed,
            "in_progress_quizzes": data["in_progress_quizzes"],
            "average_accuracy": round(avg_accuracy, 1),
            "total_points_earned": data["total_points_earned"],
            "total_points_possible": data["total_points_possible"],
            "top_weak_topics": sorted(weak_counts.items(), key=lambda x: -x[1])[:3],
            "top_strong_topics": sorted(strong_counts.items(), key=lambda x: -x[1])[:3],
            "recent_quizzes": data["quizzes"][:5],
        })
    
    # Sort by total quizzes
    subjects.sort(key=lambda x: -x["total_quizzes"])
    
    return {
        "subjects": subjects,
        "total_subjects": len(subjects),
    }


@router.get("/{quiz_id}/full")
async def get_full_quiz_details(
    quiz_id: str,
    user: dict = Depends(get_current_user),
):
    """Get full quiz details including all questions, answers, and results."""
    supabase = get_supabase_service()
    
    # Get quiz with all data
    result = supabase.admin_client.table("quizzes").select("*").eq(
        "id", quiz_id
    ).eq("user_id", user["id"]).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz = result.data[0]
    
    # Get performance if completed
    performance = None
    if quiz.get("status") == "completed":
        perf_result = supabase.admin_client.table("quiz_performance").select("*").eq(
            "quiz_id", quiz_id
        ).execute()
        if perf_result.data:
            performance = perf_result.data[0]
    
    return {
        "quiz_id": quiz_id,
        "status": quiz.get("status"),
        "quiz_type": quiz.get("quiz_type"),
        "difficulty": quiz.get("difficulty"),
        "subject_name": quiz.get("subject_name"),
        "questions": quiz.get("questions", []),
        "user_answers": quiz.get("user_answers", {}),
        "detailed_results": quiz.get("detailed_results", []),
        "time_limit": quiz.get("time_limit"),
        "time_spent": quiz.get("time_spent", 0),
        "created_at": quiz.get("created_at"),
        "completed_at": quiz.get("completed_at"),
        "performance": performance,
    }
