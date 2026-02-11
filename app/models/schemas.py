from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Base models
class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    status: ProcessingStatus


class StatusResponse(BaseModel):
    status: ProcessingStatus
    progress: float = 0.0
    message: Optional[str] = None


# Podcast models
class PodcastCreateRequest(BaseModel):
    pdf_path: str
    user_id: str
    title: Optional[str] = None


class PodcastStatusResponse(StatusResponse):
    audio_url: Optional[str] = None
    duration: Optional[int] = None


class PodcastResponse(BaseModel):
    id: str
    title: str
    audio_path: str
    duration: int
    transcript: Optional[str] = None
    status: ProcessingStatus
    created_at: datetime


# Hypothesis models
class HypothesisGenerateRequest(BaseModel):
    paper_ids: List[str]
    user_id: str
    focus_area: Optional[str] = None


class Hypothesis(BaseModel):
    title: str
    description: str
    confidence: float
    source_concepts: List[str]
    methodology_hints: List[str]


class HypothesisResultResponse(BaseModel):
    hypotheses: List[Hypothesis]
    processing_time: float


# Neuro-Scribe models
class ScribeAnalyzeRequest(BaseModel):
    image: str  # Base64 encoded
    type: str = Field(..., pattern="^(math|code|diagram)$")


class ScribeResponse(BaseModel):
    result: str
    format: str  # latex, python, mermaid, etc.
    confidence: float
    suggestions: Optional[List[str]] = None


# Study Loop models
class QuizGenerateRequest(BaseModel):
    course_id: str
    topic_id: Optional[str] = None
    difficulty: str = "medium"
    count: int = 5


class QuizQuestion(BaseModel):
    id: str
    question: str
    options: List[str]
    correct: int
    difficulty: str
    topic: str


class QuizGenerateResponse(BaseModel):
    questions: List[QuizQuestion]


class AnswerSubmitRequest(BaseModel):
    question_id: str
    answer: int


class AnswerResponse(BaseModel):
    correct: bool
    explanation: str
    next_action: str  # "continue", "reteach", "advance"
    memory_updated: bool


# Graph Navigator models
class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    size: float
    color: Optional[str] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float
    label: Optional[str] = None


class KnowledgeGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# Memory models
class MemoryUpdateRequest(BaseModel):
    user_id: str
    memory: Dict[str, Any]


class MemoryResponse(BaseModel):
    memory: Dict[str, Any]
    last_updated: datetime


# Notes Scanner models
class NotesScanRequest(BaseModel):
    image: str  # Base64 encoded image
    subject_id: Optional[str] = None
    title: Optional[str] = None


class NotesScanResponse(BaseModel):
    id: str
    text: str
    keywords: List[str]
    confidence: float
    language: str
    created_at: datetime


class ScannedNoteResponse(BaseModel):
    id: str
    title: str
    text: str
    keywords: List[str]
    subject_id: Optional[str] = None
    subject_name: Optional[str] = None
    confidence: float
    image_path: Optional[str] = None
    created_at: datetime


class SummarizeRequest(BaseModel):
    text: str
    style: Optional[str] = "structured"  # structured, bullet, outline, cornell


class SummarizeResponse(BaseModel):
    summary: str
    title: str
    sections: List[dict]  # [{heading, content}]
    key_points: List[str]


# User models
class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
