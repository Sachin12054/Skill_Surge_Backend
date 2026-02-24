# Cognito Backend — Autonomous Academic Operating System

A production-ready **FastAPI** backend powering Cognito, an AI-driven academic platform. It exposes a rich REST API covering intelligent study tools, document processing, AI agents, and real-time collaboration features — all secured with Supabase JWT authentication.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Environment Variables](#environment-variables)
5. [Getting Started](#getting-started)
6. [API Features](#api-features)
   - [Multilingual Chatbot](#1-multilingual-chatbot--chat)
   - [Study Space](#2-study-space--space)
   - [Study Quiz](#3-study-quiz--quiz)
   - [Flashcards & Spaced Repetition](#4-flashcards--spaced-repetition--flashcards)
   - [Neural Podcast](#5-neural-podcast--podcast)
   - [Hypothesis Lab](#6-hypothesis-lab--hypothesis)
   - [Neuro-Scribe](#7-neuro-scribe--scribe)
   - [Notes Scanner (OCR)](#8-notes-scanner--notes-scanner)
   - [Mock Interview](#9-mock-interview--interviews)
   - [Knowledge Graph Navigator](#10-knowledge-graph-navigator--graph)
   - [Study Timer](#11-study-timer--timer)
   - [Memory & Progress](#12-memory--progress--memory)
   - [Study Loop](#13-study-loop--study)
7. [AI Agents](#ai-agents)
8. [Services](#services)
9. [Database Migrations](#database-migrations)
10. [Deployment](#deployment)
11. [Testing](#testing)

---

## Architecture Overview

```
Client (Frontend)
       │
       ▼
  FastAPI App (main.py)
       │
       ├── Auth Middleware (Supabase JWT)
       │
       ├── API Routes (/api/routes/)
       │      ├── chat, quiz, flashcards, podcast
       │      ├── hypothesis, scribe, notes-scanner
       │      ├── mock-interviews, graph, timer
       │      ├── space, memory, study
       │
       ├── AI Agents (/agents/)
       │      ├── StudyAgent       ← Quiz & adaptive learning
       │      ├── PodcastAgent     ← AI-generated audio podcasts
       │      ├── HypothesisAgent  ← Research hypothesis generation
       │      └── ScribeAgent      ← Image-to-text/code/math
       │
       ├── Services (/services/)
       │      ├── PDFProcessor     ← Standard PDF text extraction
       │      ├── MambaPDFProcessor← Fast State-Space Model PDF processing
       │      ├── VisionService    ← Google Cloud Vision OCR
       │      ├── TTSService       ← ElevenLabs Text-to-Speech
       │      └── TavusService     ← AI video interview sessions
       │
       └── Core (/core/)
              ├── Supabase         ← Database + Auth + File Storage
              ├── OpenAI           ← GPT-4o-mini + Embeddings
              ├── Bedrock          ← AWS Claude 3.5 Sonnet / Llama 3 70B
              └── Neo4j            ← Knowledge Graph Database
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI 0.109+, Uvicorn |
| **Language** | Python 3.10+ |
| **Database & Auth** | Supabase (PostgreSQL + JWT) |
| **AI / LLM** | OpenAI GPT-4o-mini, AWS Bedrock (Claude 3.5 Sonnet, Llama 3 70B) |
| **Agent Orchestration** | LangChain, LangGraph |
| **Vector Search** | OpenAI `text-embedding-3-small` |
| **Knowledge Graph** | Neo4j 5.x |
| **PDF Processing** | PyMuPDF (fitz), pdfplumber, python-docx |
| **OCR** | Google Cloud Vision API |
| **Text-to-Speech** | ElevenLabs API |
| **Video AI** | Tavus Conversational Video Interface (CVI) |
| **Translation** | Sarvam AI (22 Indian languages) |
| **NLP Extras** | Sentence-Transformers, spaCy |
| **Logging** | structlog (JSON-structured) |
| **Containerisation** | Docker, Docker Compose |
| **Deployment** | Google Cloud Run, AWS Fargate (ECS), Railway |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, CORS, lifespan events
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (env-driven)
│   │   ├── supabase.py          # Supabase client wrapper
│   │   ├── openai.py            # OpenAI async client
│   │   ├── bedrock.py           # AWS Bedrock client
│   │   └── neo4j.py             # Neo4j driver
│   ├── api/
│   │   ├── deps.py              # JWT auth dependency
│   │   └── routes/
│   │       ├── chat.py          # Multilingual chatbot
│   │       ├── quiz.py          # AI quiz generation & grading
│   │       ├── flashcards.py    # Flashcard decks + SM-2 reviews
│   │       ├── podcast.py       # Neural podcast generation
│   │       ├── hypothesis.py    # Research hypothesis lab
│   │       ├── hypothesis_v2.py # Agentic hypothesis pipeline
│   │       ├── scribe.py        # Image-to-code/math/diagram
│   │       ├── notes_scanner.py # Handwritten notes OCR
│   │       ├── mock_interview.py# AI video mock interviews
│   │       ├── graph.py         # Knowledge graph navigator
│   │       ├── study_timer.py   # Pomodoro timer + analytics
│   │       ├── space.py         # PDF & subject management
│   │       ├── memory.py        # Study memory & progress
│   │       └── study.py         # Adaptive study loop
│   ├── agents/
│   │   ├── study_agent.py
│   │   ├── podcast_agent.py
│   │   ├── hypothesis_agent.py
│   │   ├── hypothesis_agent_v2.py
│   │   ├── hypothesis_agent_agentic.py
│   │   └── scribe_agent.py
│   ├── models/
│   │   └── schemas.py           # All Pydantic request/response models
│   └── services/
│       ├── pdf_processor.py
│       ├── mamba_pdf_processor.py
│       ├── vision_service.py
│       ├── tts.py
│       └── tavus_service.py
├── migrations/                  # SQL migration files for Supabase
├── deploy/                      # Cloud deployment configs
├── credentials/                 # GCP service account (gitignored in production)
├── Dockerfile / Dockerfile.prod
├── requirements.txt
└── run_server.py
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Application
APP_NAME="Cognito Backend"
APP_VERSION="1.0.0"
DEBUG=True

# Server
HOST=0.0.0.0
PORT=8000

# Supabase (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# OpenAI (required for AI features)
OPENAI_API_KEY=sk-...

# AWS (required for Bedrock & quiz AI)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
BEDROCK_LLAMA_MODEL_ID=meta.llama3-70b-instruct-v1:0

# Neo4j (optional — knowledge graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# ElevenLabs (optional — podcast TTS)
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_1=21m00Tcm4TlvDq8ikWAM   # Host voice (Rachel)
ELEVENLABS_VOICE_2=AZnzlk1XvdvUeBnXmlld   # Guest voice (Domi)

# Sarvam AI (optional — Indian language translation)
SARVAM_API_KEY=...

# Tavus Video AI (optional — mock interviews)
TAVUS_API_KEY=...

# Google Cloud Vision (optional — notes OCR)
GOOGLE_APPLICATION_CREDENTIALS=credentials/gcp-service-account.json
GCP_SERVICE_ACCOUNT_JSON=<json-string-for-cloud-deploy>

# Processing
MAX_PDF_SIZE_MB=50
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

---

## Getting Started

### Local Development

```bash
# 1. Clone and enter directory
git clone <repo-url>
cd backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your .env file (see above)

# 5. Run database migrations (in Supabase SQL editor)
#    Apply files from migrations/ in order (001, 002, 003, ...)

# 6. Start the server
python run_server.py
# OR
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs (Swagger UI): `http://localhost:8000/docs` (only when `DEBUG=True`).

### Docker

```bash
docker build -t cognito-backend .
docker run -p 8000:8000 --env-file .env cognito-backend
```

---

## API Features

All routes (except `/health` and `/`) require a valid Supabase JWT in the `Authorization: Bearer <token>` header.

---

### 1. Multilingual Chatbot — `/chat`

An intelligent academic assistant powered by **GPT-4o-mini**, supporting optional PDF-grounded responses and real-time translation into **22 Indian languages** via the Sarvam AI API.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/chat/languages` | List all supported Indian language codes and names |
| `POST` | `/chat/send` | Send a message; optionally attach a PDF for context |

**Request body (`POST /chat/send`):**
```json
{
  "message": "Explain Newton's second law",
  "pdf_id": "uuid-of-uploaded-pdf",
  "target_language": "hi-IN",
  "conversation_history": []
}
```

**How it works:**
- If `pdf_id` is provided the PDF is downloaded from Supabase Storage, text is extracted with **PyMuPDF**, and injected into the GPT-4o-mini context (up to ~12 000 characters).
- The English response is then translated to the `target_language` by calling the **Sarvam Translate API**.
- Supported languages include Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Marathi, Punjabi, Odia, Urdu, and 11 more.

---

### 2. Study Space — `/space`

Organise uploaded PDFs into colour-coded **subjects/folders**. This is the document management hub that feeds all other AI features.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/space/subjects` | List all subjects with PDF count |
| `POST` | `/space/subjects` | Create a new subject |
| `PUT` | `/space/subjects/{id}` | Update subject name/color/icon |
| `DELETE` | `/space/subjects/{id}` | Delete a subject |
| `GET` | `/space/pdfs` | List all uploaded PDFs (optionally filtered by subject) |
| `POST` | `/space/upload` | Upload a PDF file (multipart/form-data) |
| `DELETE` | `/space/pdfs/{id}` | Delete a PDF and its storage object |
| `POST` | `/space/assign` | Assign/unassign PDFs to a subject |
| `PATCH` | `/space/pdfs/{id}` | Update a PDF's subject assignment |

**Highlights:**
- PDFs are stored in a **Supabase Storage** bucket (`course-materials`).
- Upload endpoint validates file type and enforces the `MAX_PDF_SIZE_MB` limit.
- Subject cards display live PDF counts via a Supabase join.

---

### 3. Study Quiz — `/quiz`

Full-featured AI quiz system backed by **AWS Bedrock (Claude 3.5 Sonnet)**. Generates questions from your own PDFs, evaluates short-answer responses with **semantic similarity** using OpenAI embeddings, and tracks quiz history in Supabase.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/quiz/generate` | Generate a quiz from one or more PDFs |
| `POST` | `/quiz/submit` | Submit all answers and receive a scored report |
| `POST` | `/quiz/adaptive/next` | Get the next adaptive question based on performance |
| `GET` | `/quiz/history` | List past quizzes for the authenticated user |
| `GET` | `/quiz/history/{quiz_id}` | Get full details of a specific quiz attempt |
| `GET` | `/quiz/stats` | Aggregated performance statistics |

**Quiz configuration options:**
```json
{
  "pdf_ids": ["uuid1", "uuid2"],
  "quiz_type": "mcq",        // mcq | true_false | short_answer | mixed
  "difficulty": "adaptive",  // easy | medium | hard | adaptive
  "num_questions": 10,
  "time_limit": 30,
  "topics": ["thermodynamics"],
  "adaptive_mode": true
}
```

**Grading:**
- MCQ / True-False: exact match.
- Short-answer: cosine similarity of **OpenAI `text-embedding-3-small`** vectors with a configurable threshold (default 0.80). Falls back to keyword matching if the API is unavailable.
- Each question has a 1–5 difficulty score and earns configurable points.

---

### 4. Flashcards & Spaced Repetition — `/flashcards`

Create and review flashcard decks manually or **auto-generate them from PDFs** using GPT. Reviews implement the classic **SM-2 spaced-repetition algorithm**.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/flashcards/decks` | List all decks |
| `POST` | `/flashcards/decks` | Create a new deck |
| `PUT` | `/flashcards/decks/{id}` | Update deck metadata |
| `DELETE` | `/flashcards/decks/{id}` | Delete a deck |
| `POST` | `/flashcards/generate` | Auto-generate cards from PDFs |
| `GET` | `/flashcards/decks/{id}/cards` | Get all cards in a deck |
| `POST` | `/flashcards/cards` | Add a card manually |
| `PUT` | `/flashcards/cards/{id}` | Edit a card |
| `DELETE` | `/flashcards/cards/{id}` | Delete a card |
| `GET` | `/flashcards/decks/{id}/due` | Get cards due for review today |
| `POST` | `/flashcards/review` | Submit a review (SM-2 quality 0–5) |
| `POST` | `/flashcards/session/start` | Start a study session |
| `POST` | `/flashcards/session/end` | End a session and save stats |
| `GET` | `/flashcards/stats` | Overall review statistics |

**SM-2 algorithm:**
- Quality 0–2 → card reset to interval = 1 day, ease factor decreases.
- Quality 3–5 → interval grows exponentially, ease factor adjusted.
- Each card maintains `repetitions`, `ease_factor`, `interval`, and `next_review_at`.

---

### 5. Neural Podcast — `/podcast`

Converts a PDF into a two-host **AI-narrated audio podcast** (WAV) using ElevenLabs voices, then stores it in Supabase Storage.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/podcast/create` | Create a podcast from stored space PDFs |
| `POST` | `/podcast/upload` | Upload a new PDF and immediately generate a podcast |
| `GET` | `/podcast/status/{task_id}` | Poll background task progress (0–100%) |
| `GET` | `/podcast/list` | List all podcasts for the current user |
| `GET` | `/podcast/{podcast_id}` | Get metadata + signed audio URL |
| `DELETE` | `/podcast/{podcast_id}` | Delete a podcast |

**Generation pipeline:**
1. PDF text extracted with PyMuPDF.
2. `PodcastAgent` uses GPT to write a conversational two-host script with intro, topic segments, and outro.
3. Each speaker turn is synthesised with a distinct ElevenLabs voice.
4. WAV segments are concatenated into a single file.
5. Audio duration is calculated from WAV headers and stored.
6. A short catchy title is generated via GPT.

---

### 6. Hypothesis Lab — `/hypothesis`

An async research tool that cross-analyses **two or more academic PDFs** and surfaces novel, testable research hypotheses by identifying concept overlaps, contradictions, and knowledge gaps.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/hypothesis/generate` | Start async hypothesis generation (returns `task_id`) |
| `GET` | `/hypothesis/status/{task_id}` | Poll task status |
| `GET` | `/hypothesis/result/{task_id}` | Retrieve generated hypotheses |
| `GET` | `/hypothesis/list` | List saved hypotheses for the user |

**Also available (v2 agentic pipeline):**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/hypothesis/v2/generate` | Agentic pipeline with tool-use and ArXiv search |
| `GET` | `/hypothesis/v2/status/{task_id}` | Poll agentic task |
| `GET` | `/hypothesis/v2/result/{task_id}` | Get agentic hypotheses with validation scores |

**How it works:**
- Papers are downloaded from Supabase Storage and text is extracted.
- The `HypothesisAgent` (backed by Claude 3.5 Sonnet via AWS Bedrock) performs cross-paper analysis.
- The agentic v2 variant uses **LangGraph** with tool-use: it can search **ArXiv**, validate claims, and score hypotheses for novelty and feasibility.
- Hypotheses are saved to the `hypotheses` table with confidence scores and source paper IDs.

---

### 7. Neuro-Scribe — `/scribe`

Analyses a **base64-encoded image** and converts its content into structured digital output.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/scribe/analyze` | Analyse image → code, math (LaTeX), or diagram description |
| `POST` | `/scribe/validate-math` | Validate a LaTeX expression |
| `GET` | `/scribe/history` | Retrieve past scribe outputs |

**Supported output types:**
- `math` — Handwritten equations → LaTeX.
- `code` — Whiteboard / notebook code → syntax-highlighted code block.
- `diagram` — Flowchart / architecture diagram → textual or Mermaid description.

The `ScribeAgent` calls the **OpenAI Vision** endpoint with the image and type-specific prompts. Results are saved to the `scribe_outputs` table.

---

### 8. Notes Scanner — `/notes-scanner`

Digitises **handwritten or printed notes** from a photo using the **Google Cloud Vision API**.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/notes-scanner/scan` | OCR an image; returns text, keywords, confidence |
| `GET` | `/notes-scanner/notes` | List saved scanned notes (paginated) |
| `GET` | `/notes-scanner/notes/{id}` | Get a specific scanned note |
| `DELETE` | `/notes-scanner/notes/{id}` | Delete a scanned note |
| `POST` | `/notes-scanner/summarize` | Summarise saved note text with GPT |
| `GET` | `/notes-scanner/subjects` | List subjects for grouping notes |

**Pipeline:**
1. Accepts a base64-encoded image (JPEG/PNG with optional `data:` prefix).
2. Sends to **Google Vision `DOCUMENT_TEXT_DETECTION`**.
3. Extracts full text, detected language, confidence score, and auto-detected keywords.
4. If no title is provided the first line of text is used as the title.
5. Saved in the `scanned_notes` table, optionally linked to a subject.

---

### 9. Mock Interview — `/interviews`

Runs an AI-powered **video mock interview** session using the **Tavus Conversational Video Interface (CVI)**.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/interviews/start` | Start a new interview session (returns video URL) |
| `GET` | `/interviews/` | List past interview sessions |
| `GET` | `/interviews/{id}` | Get details of a specific session |
| `POST` | `/interviews/{id}/end` | End a session and store feedback |
| `POST` | `/interviews/{id}/feedback` | Save scored feedback report |

**Interview types supported:** `behavioral`, `technical`, `system-design`.

**Flow:**
1. A Tavus persona is created (or reused) for the requested interview type/target role.
2. A Tavus conversation is created and a join URL is returned to the frontend.
3. The frontend embeds the Tavus iframe — the AI interviewer conducts the session.
4. On session end, a feedback object with communication, technical depth, problem-solving, and confidence scores is stored.
5. Falls back to a **demo mode** if the Tavus API key is missing.

---

### 10. Knowledge Graph Navigator — `/graph`

Visualises course concepts and their relationships as an interactive graph, stored in **Neo4j**.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/graph/{course_id}` | Get nodes and edges for a course (configurable depth) |
| `GET` | `/graph/{course_id}/similar/{concept_id}` | Find concepts connected to a given node |

**Response format:**
```json
{
  "nodes": [{ "id": "...", "label": "Thermodynamics", "type": "concept", "size": 1.5 }],
  "edges": [{ "source": "...", "target": "...", "weight": 1.0, "label": "relates_to" }]
}
```

---

### 11. Study Timer — `/timer`

A **Pomodoro-style** focus timer with full analytics, customisable durations, and daily/weekly goal tracking.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/timer/settings` | Get user's timer preferences |
| `PUT` | `/timer/settings` | Update timer preferences |
| `POST` | `/timer/sessions/start` | Start a focus/break session |
| `POST` | `/timer/sessions/end` | End session and record stats |
| `POST` | `/timer/sessions/pause` | Record a pause event |
| `POST` | `/timer/sessions/resume` | Record a resume event |
| `GET` | `/timer/sessions` | List recent sessions |
| `GET` | `/timer/stats/today` | Today's focus time, sessions, goals |
| `GET` | `/timer/stats/weekly` | Weekly breakdown |
| `GET` | `/timer/stats/heatmap` | Activity heatmap data (last 365 days) |
| `GET` | `/timer/achievements` | Earned achievement badges |

**Session types:** `focus`, `short_break`, `long_break`.  
**Activity types:** `flashcards`, `quiz`, `reading`, `notes`, `general`.

Default Pomodoro settings: 25 min focus / 5 min short break / 15 min long break / long break every 4 sessions.

---

### 12. Memory & Progress — `/memory`

Stores and retrieves per-user, per-course learning memory used by the adaptive study agents.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/memory/{course_id}` | Get memory summary for a course |
| `PUT` | `/memory/{course_id}` | Update topic strengths and weak areas |
| `DELETE` | `/memory/{course_id}` | Reset memory for a course |

---

### 13. Study Loop — `/study`

Adaptive quiz loop that integrates with the `StudyAgent` to generate and evaluate questions with real-time memory updates.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/study/quiz` | Generate an adaptive quiz for a course/topic |
| `POST` | `/study/answer` | Submit an answer and get feedback + next action |
| `GET` | `/study/progress/{course_id}` | Get cumulative accuracy statistics |

The `StudyAgent` selects question difficulty based on prior performance stored in memory. After each answer it updates weak-topic flags in the user's memory record.

---

## AI Agents

| Agent | File | Description |
|---|---|---|
| `StudyAgent` | `agents/study_agent.py` | Adaptive quiz generation and answer evaluation |
| `PodcastAgent` | `agents/podcast_agent.py` | Two-host podcast scripting + ElevenLabs TTS synthesis |
| `HypothesisAgent` | `agents/hypothesis_agent.py` | Cross-paper hypothesis generation via Bedrock |
| `HypothesisAgentV2` | `agents/hypothesis_agent_v2.py` | Enhanced agent with validation scoring |
| `HypothesisAgentAgentic` | `agents/hypothesis_agent_agentic.py` | LangGraph agentic pipeline with ArXiv tool-use |
| `ScribeAgent` | `agents/scribe_agent.py` | Vision-based image-to-structured-output conversion |

### Agent Tools (`agents/tools/`)

| Tool | Description |
|---|---|
| `search_tools.py` | ArXiv paper search, web search helpers |
| `validation_tools.py` | Hypothesis novelty and feasibility validation |

---

## Services

| Service | Description |
|---|---|
| `PDFProcessor` | Extracts text from PDFs using pdfplumber + PyMuPDF; chunking with overlap |
| `MambaPDFProcessor` | Experimental fast PDF processing using Mamba State-Space Models (requires CUDA) |
| `VisionService` | Google Cloud Vision API wrapper for handwriting OCR |
| `TTSService` | ElevenLabs Text-to-Speech synthesis with multi-voice support |
| `TavusService` | Tavus CVI persona and conversation management |

---

## Database Migrations

All SQL migrations are in the `migrations/` folder. Apply them **in order** via the Supabase SQL Editor:

| File | Description |
|---|---|
| `001_create_space_tables.sql` | `subjects`, `space_pdfs` tables |
| `002_create_quiz_tables.sql` | `quiz_sessions`, `quiz_questions` tables |
| `002_hypothesis_tables.sql` | `hypotheses`, `hypothesis_tasks` tables |
| `003_mock_interviews.sql` | `interviews` table |
| `004_flashcard_tables.sql` | `flashcard_decks`, `flashcards`, `flashcard_reviews` tables |
| `004_scanned_notes.sql` | `scanned_notes` table |
| `004_study_timer.sql` | `timer_settings`, `timer_sessions` tables |
| `005_hypothesis_task_id.sql` | Adds `task_id` index to hypothesis tasks |

---

## Deployment

### Google Cloud Run

```bash
# Authenticate and deploy
gcloud auth login
./deploy-gcloud.ps1
```

See [deploy/cloud-run.yaml](deploy/cloud-run.yaml) and [deploy/DEPLOYMENT.md](deploy/DEPLOYMENT.md) for full instructions.

### AWS Fargate (ECS)

```bash
./deploy/aws-deploy.sh
```

See [deploy/aws-fargate.yaml](deploy/aws-fargate.yaml) and [deploy/AWS-SETUP.md](deploy/AWS-SETUP.md).

### Railway

Push to the linked repository branch — `railway.json` configures the build and run commands automatically.

### Docker (Production)

```bash
docker build -f Dockerfile.prod -t cognito-backend:prod .
docker run -p 8000:8000 --env-file .env cognito-backend:prod
```

---

## Testing

```powershell
# Run all tests
./run_tests.ps1

# Individual test suites
pytest test_api.py             # Core API smoke tests
pytest test_all_endpoints.py   # Full endpoint coverage
pytest test_agentic_system.py  # Agentic pipeline tests
pytest test_comprehensive.py   # Comprehensive integration tests
```

Additional standalone scripts:
- `check_health.py` — Verify the `/health` endpoint is responding.
- `list_routes.py` — Print all registered routes and their tags.
- `test_openai_key.py` — Validate your OpenAI API key.

---

## Health Check

```
GET /health
```
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "Cognito Backend"
}
```

---

## License

This project is proprietary software developed for the Cognito academic platform.
