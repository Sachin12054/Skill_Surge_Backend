from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    APP_NAME: str = "Cognito Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str
    
    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # AWS Bedrock
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    BEDROCK_LLAMA_MODEL_ID: str = "meta.llama3-70b-instruct-v1:0"
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    
    # ElevenLabs
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_1: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    ELEVENLABS_VOICE_2: str = "AZnzlk1XvdvUeBnXmlld"  # Domi
    
    # Sarvam AI
    SARVAM_API_KEY: str = ""
    
    # Tavus Video API
    TAVUS_API_KEY: str = ""
    
    # Google Cloud Vision API
    GOOGLE_APPLICATION_CREDENTIALS: str = "credentials/gcp-service-account.json"
    
    # Processing
    MAX_PDF_SIZE_MB: int = 50
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
