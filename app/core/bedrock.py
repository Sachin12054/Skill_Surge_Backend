import boto3
from functools import lru_cache
from typing import Optional, List, Dict, Any
import json
from app.core.config import get_settings

settings = get_settings()


@lru_cache()
def get_bedrock_client():
    """Get cached Bedrock client."""
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


class BedrockService:
    """Service class for AWS Bedrock operations."""
    
    def __init__(self):
        self.client = get_bedrock_client()
    
    async def invoke_claude(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Invoke Claude model on Bedrock."""
        messages = [{"role": "user", "content": prompt}]
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        
        if system_prompt:
            body["system"] = system_prompt
        
        response = self.client.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps(body),
        )
        
        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]
    
    async def invoke_claude_vision(
        self,
        prompt: str,
        image_base64: str,
        image_media_type: str = "image/jpeg",
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> str:
        """Invoke Claude with vision capabilities."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_media_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
        }
        
        if system_prompt:
            body["system"] = system_prompt
        
        response = self.client.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps(body),
        )
        
        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]
    
    async def invoke_llama(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Invoke Llama model on Bedrock."""
        body = {
            "prompt": prompt,
            "max_gen_len": max_tokens,
            "temperature": temperature,
        }
        
        response = self.client.invoke_model(
            modelId=settings.BEDROCK_LLAMA_MODEL_ID,
            body=json.dumps(body),
        )
        
        response_body = json.loads(response["body"].read())
        return response_body["generation"]
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings using Titan Embeddings model."""
        embeddings = []
        
        for text in texts:
            body = {"inputText": text}
            response = self.client.invoke_model(
                modelId="amazon.titan-embed-text-v1",
                body=json.dumps(body),
            )
            response_body = json.loads(response["body"].read())
            embeddings.append(response_body["embedding"])
        
        return embeddings


def get_bedrock_service() -> BedrockService:
    """Get Bedrock service instance."""
    return BedrockService()
