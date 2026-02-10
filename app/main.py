from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
from app.core.config import get_settings
from app.api.routes import podcast, hypothesis, scribe, study, graph, memory, mock_interview, space, quiz, flashcards, study_timer, notes_scanner

settings = get_settings()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Cognito Backend", version=settings.APP_VERSION)
    
    # Warm up ML models on startup to avoid cold start delays
    try:
        logger.info("Warming up Mamba model...")
        from app.services.mamba_pdf_processor import MambaPDFProcessor
        processor = MambaPDFProcessor()
        logger.info("Model warming complete")
    except Exception as e:
        logger.error("Model warming failed", error=str(e))
    
    yield
    logger.info("Shutting down Cognito Backend")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Cognito - Autonomous Academic Operating System Backend",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": settings.APP_NAME,
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Cognito API",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "Disabled in production",
    }


# Register API routes
app.include_router(podcast.router, prefix="/api/v1")
app.include_router(hypothesis.router, prefix="/api/v1")
app.include_router(scribe.router, prefix="/api/v1")
app.include_router(study.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(memory.router, prefix="/api/v1")
app.include_router(mock_interview.router, prefix="/api/v1")
app.include_router(space.router, prefix="/api/v1")
app.include_router(quiz.router, prefix="/api/v1")
app.include_router(flashcards.router, prefix="/api/v1")
app.include_router(study_timer.router, prefix="/api/v1")
app.include_router(notes_scanner.router, prefix="/api/v1")

# Import and register v2 hypothesis routes
from app.api.routes import hypothesis_v2
app.include_router(hypothesis_v2.router, prefix="/api/v2")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
