from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from app.core import get_bedrock_service, get_supabase_service
import json
import random


class StudyState(TypedDict):
    """State for the study loop workflow."""
    user_id: str
    course_id: str
    topic: str
    difficulty: str
    user_memory: Dict[str, Any]
    questions: List[Dict[str, Any]]
    current_question_idx: int
    user_answer: Optional[int]
    is_correct: Optional[bool]
    explanation: str
    next_action: str
    error: Optional[str]
    status: str


async def load_user_memory(state: StudyState) -> StudyState:
    """Load user's learning memory from database."""
    supabase = get_supabase_service()
    
    try:
        result = await supabase.select(
            "user_memory",
            "*",
            {"user_id": state['user_id']}
        )
        
        memory = {}
        for record in result.data:
            memory[record['memory_type']] = record['content']
        
        return {**state, "user_memory": memory, "status": "memory_loaded"}
    except Exception as e:
        return {**state, "user_memory": {}, "status": "memory_loaded"}


async def generate_questions(state: StudyState) -> StudyState:
    """Generate quiz questions based on course content and user memory."""
    bedrock = get_bedrock_service()
    
    # Get struggle points from memory
    struggles = state['user_memory'].get('struggle', {}).get('topics', [])
    strengths = state['user_memory'].get('strength', {}).get('topics', [])
    
    difficulty_multiplier = {
        "easy": 0.7,
        "medium": 1.0,
        "hard": 1.3,
    }
    
    prompt = f"""Generate 5 quiz questions for a student studying.
    
    Topic: {state['topic']}
    Course ID: {state['course_id']}
    Difficulty: {state['difficulty']}
    
    Student struggles with: {', '.join(struggles[:3]) if struggles else 'No data'}
    Student is strong in: {', '.join(strengths[:3]) if strengths else 'No data'}
    
    Create questions that:
    - Focus more on struggle areas (if any)
    - Provide appropriate difficulty
    - Cover key concepts
    - Are clear and unambiguous
    
    Return a JSON array where each question has:
    - id: unique identifier (q1, q2, etc.)
    - question: the question text
    - options: array of 4 answer options
    - correct: index of correct answer (0-3)
    - difficulty: easy/medium/hard
    - topic: specific subtopic
    - explanation: why the correct answer is correct
    
    Return ONLY the JSON array."""
    
    response = await bedrock.invoke_claude(
        prompt,
        system_prompt="You are an expert educational quiz generator.",
        max_tokens=3000,
    )
    
    try:
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        questions = json.loads(response)
    except json.JSONDecodeError:
        questions = [
            {
                "id": "q1",
                "question": "What is the main concept?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct": 0,
                "difficulty": "medium",
                "topic": state['topic'],
                "explanation": "This is the correct answer because..."
            }
        ]
    
    return {**state, "questions": questions, "current_question_idx": 0, "status": "questions_generated"}


async def evaluate_answer(state: StudyState) -> StudyState:
    """Evaluate the user's answer and provide feedback."""
    bedrock = get_bedrock_service()
    
    current_q = state['questions'][state['current_question_idx']]
    is_correct = state['user_answer'] == current_q['correct']
    
    if is_correct:
        explanation = current_q.get('explanation', 'Correct!')
        next_action = "continue"
    else:
        # Generate a reteaching explanation
        prompt = f"""A student got this question wrong:
        
        Question: {current_q['question']}
        Their answer: {current_q['options'][state['user_answer']]}
        Correct answer: {current_q['options'][current_q['correct']]}
        
        Provide a clear, encouraging explanation that:
        1. Explains why their answer was incorrect
        2. Explains why the correct answer is right
        3. Provides a memorable way to remember this concept
        4. Suggests what to review
        
        Keep it concise but thorough (100-150 words)."""
        
        explanation = await bedrock.invoke_claude(
            prompt,
            system_prompt="You are a patient, encouraging tutor.",
            max_tokens=500,
        )
        next_action = "reteach"
    
    return {
        **state,
        "is_correct": is_correct,
        "explanation": explanation,
        "next_action": next_action,
        "status": "evaluated"
    }


async def update_memory(state: StudyState) -> StudyState:
    """Update user's learning memory based on performance."""
    supabase = get_supabase_service()
    
    current_q = state['questions'][state['current_question_idx']]
    topic = current_q.get('topic', state['topic'])
    
    # Determine memory update
    if state['is_correct']:
        memory_type = "strength"
    else:
        memory_type = "struggle"
    
    # Get existing memory
    existing = state['user_memory'].get(memory_type, {"topics": [], "count": {}})
    
    if topic not in existing['topics']:
        existing['topics'].append(topic)
    
    existing['count'] = existing.get('count', {})
    existing['count'][topic] = existing['count'].get(topic, 0) + 1
    
    try:
        # Upsert memory
        await supabase.admin_client.table("user_memory").upsert({
            "user_id": state['user_id'],
            "memory_type": memory_type,
            "content": existing,
            "importance": existing['count'].get(topic, 1),
        }).execute()
    except Exception:
        pass  # Non-critical operation
    
    return {**state, "status": "memory_updated"}


def create_study_graph() -> StateGraph:
    """Create the study loop workflow graph."""
    workflow = StateGraph(StudyState)
    
    # Add nodes
    workflow.add_node("load_memory", load_user_memory)
    workflow.add_node("generate", generate_questions)
    workflow.add_node("evaluate", evaluate_answer)
    workflow.add_node("update", update_memory)
    
    # Add edges
    workflow.set_entry_point("load_memory")
    workflow.add_edge("load_memory", "generate")
    workflow.add_edge("generate", END)  # Returns questions
    
    return workflow.compile()


def create_answer_graph() -> StateGraph:
    """Create the answer evaluation workflow graph."""
    workflow = StateGraph(StudyState)
    
    workflow.add_node("evaluate", evaluate_answer)
    workflow.add_node("update", update_memory)
    
    workflow.set_entry_point("evaluate")
    workflow.add_edge("evaluate", "update")
    workflow.add_edge("update", END)
    
    return workflow.compile()


class StudyAgent:
    """Agent for adaptive study and quizzing."""
    
    def __init__(self):
        self.study_graph = create_study_graph()
        self.answer_graph = create_answer_graph()
    
    async def generate_quiz(
        self,
        user_id: str,
        course_id: str,
        topic: str = "general",
        difficulty: str = "medium",
    ) -> Dict[str, Any]:
        """Generate a quiz for the user."""
        initial_state: StudyState = {
            "user_id": user_id,
            "course_id": course_id,
            "topic": topic,
            "difficulty": difficulty,
            "user_memory": {},
            "questions": [],
            "current_question_idx": 0,
            "user_answer": None,
            "is_correct": None,
            "explanation": "",
            "next_action": "",
            "error": None,
            "status": "started",
        }
        
        result = await self.study_graph.ainvoke(initial_state)
        
        return {
            "questions": result.get("questions", []),
            "status": result.get("status"),
        }
    
    async def submit_answer(
        self,
        user_id: str,
        questions: List[Dict],
        question_idx: int,
        answer: int,
    ) -> Dict[str, Any]:
        """Submit and evaluate an answer."""
        state: StudyState = {
            "user_id": user_id,
            "course_id": "",
            "topic": "",
            "difficulty": "",
            "user_memory": {},
            "questions": questions,
            "current_question_idx": question_idx,
            "user_answer": answer,
            "is_correct": None,
            "explanation": "",
            "next_action": "",
            "error": None,
            "status": "answering",
        }
        
        result = await self.answer_graph.ainvoke(state)
        
        return {
            "correct": result.get("is_correct"),
            "explanation": result.get("explanation"),
            "next_action": result.get("next_action"),
            "memory_updated": result.get("status") == "memory_updated",
        }


def get_study_agent() -> StudyAgent:
    """Get study agent instance."""
    return StudyAgent()
