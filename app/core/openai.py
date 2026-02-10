from functools import lru_cache
from typing import Optional
from openai import AsyncOpenAI
from app.core.config import get_settings

settings = get_settings()


@lru_cache()
def get_openai_client():
    """Get cached OpenAI client."""
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class OpenAIService:
    """Service class for OpenAI operations."""
    
    def __init__(self):
        self.client = get_openai_client()
        self.model = "gpt-4o-mini"  # Using GPT-4o-mini as requested
    
    async def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Invoke GPT-4o-mini model."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return response.choices[0].message.content
    
    async def invoke_vision(
        self,
        prompt: str,
        image_base64: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> str:
        """Invoke GPT-4o-mini with vision capabilities."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        })
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
        )
        
        return response.choices[0].message.content
    
    async def generate_embeddings(
        self,
        texts: list[str],
        model: str = "text-embedding-3-small"
    ) -> list[list[float]]:
        """Generate embeddings using OpenAI."""
        response = await self.client.embeddings.create(
            model=model,
            input=texts
        )
        
        return [item.embedding for item in response.data]


@lru_cache()
def get_openai_service() -> OpenAIService:
    """Get OpenAI service instance."""
    return OpenAIService()
