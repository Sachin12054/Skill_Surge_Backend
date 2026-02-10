"""
Google Cloud Vision API service for handwriting recognition and document analysis.
Uses service account authentication.
"""
import httpx
import json
import time
import base64
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
from app.core.config import get_settings


@dataclass
class TextBlock:
    """Represents a block of detected text."""
    text: str
    confidence: float
    bounding_box: Optional[Dict[str, Any]] = None


@dataclass
class ScanResult:
    """Result from document/handwriting scan."""
    full_text: str
    blocks: List[TextBlock]
    language: str
    confidence: float
    page_count: int
    detected_keywords: List[str]


class VisionService:
    """Service for Google Cloud Vision API operations using service account."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://vision.googleapis.com/v1"
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0
        
        # Load service account credentials
        creds_path = Path(self.settings.GOOGLE_APPLICATION_CREDENTIALS)
        if not creds_path.is_absolute():
            # Resolve relative to backend directory
            creds_path = Path(__file__).parent.parent.parent / creds_path
        
        if not creds_path.exists():
            raise FileNotFoundError(
                f"Service account file not found: {creds_path}. "
                "Place your GCP service account JSON in backend/credentials/"
            )
        
        with open(creds_path) as f:
            self._credentials = json.load(f)
    
    async def _get_access_token(self) -> str:
        """Get OAuth2 access token from service account using JWT."""
        import jwt as pyjwt
        
        # Return cached token if still valid
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token
        
        now = int(time.time())
        payload = {
            "iss": self._credentials["client_email"],
            "scope": "https://www.googleapis.com/auth/cloud-vision",
            "aud": self._credentials["token_uri"],
            "iat": now,
            "exp": now + 3600,
        }
        
        signed_jwt = pyjwt.encode(
            payload,
            self._credentials["private_key"],
            algorithm="RS256"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._credentials["token_uri"],
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": signed_jwt,
                },
                timeout=15.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get access token: {response.text}")
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            self._token_expiry = now + token_data.get("expires_in", 3600)
        
        return self._access_token
    
    async def _make_vision_request(self, request_body: dict) -> dict:
        """Make an authenticated request to Vision API."""
        token = await self._get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/images:annotate",
                headers={"Authorization": f"Bearer {token}"},
                json=request_body,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Vision API error: {response.text}")
            
            return response.json()
    
    async def scan_handwritten_notes(
        self, 
        image_base64: str,
        extract_keywords: bool = True
    ) -> ScanResult:
        """
        Scan handwritten notes and extract text using Google Vision API.
        
        Args:
            image_base64: Base64 encoded image (with or without data URI prefix)
            extract_keywords: Whether to extract key terms/concepts
            
        Returns:
            ScanResult with extracted text and metadata
        """
        # Clean base64 string (remove data URI prefix if present)
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        
        # Build request for document text detection (best for handwriting)
        request_body = {
            "requests": [{
                "image": {
                    "content": image_base64
                },
                "features": [
                    {"type": "DOCUMENT_TEXT_DETECTION"},
                    {"type": "TEXT_DETECTION"}
                ],
                "imageContext": {
                    "languageHints": ["en"]
                }
            }]
        }
        
        result = await self._make_vision_request(request_body)
        
        # Parse response
        annotations = result.get("responses", [{}])[0]
        
        # Get full text from document detection
        full_text_annotation = annotations.get("fullTextAnnotation", {})
        full_text = full_text_annotation.get("text", "")
        
        # Get text blocks with confidence
        blocks = []
        pages = full_text_annotation.get("pages", [])
        
        for page in pages:
            for block in page.get("blocks", []):
                block_text = ""
                block_confidence = 0.0
                paragraph_count = 0
                
                for paragraph in block.get("paragraphs", []):
                    for word in paragraph.get("words", []):
                        word_text = "".join(
                            symbol.get("text", "") 
                            for symbol in word.get("symbols", [])
                        )
                        block_text += word_text + " "
                        block_confidence += word.get("confidence", 0.0)
                        paragraph_count += 1
                
                if block_text.strip():
                    avg_confidence = block_confidence / max(paragraph_count, 1)
                    blocks.append(TextBlock(
                        text=block_text.strip(),
                        confidence=avg_confidence,
                        bounding_box=block.get("boundingBox")
                    ))
        
        # Detect language
        detected_language = "en"
        if pages and pages[0].get("property", {}).get("detectedLanguages"):
            detected_language = pages[0]["property"]["detectedLanguages"][0].get(
                "languageCode", "en"
            )
        
        # Calculate overall confidence
        overall_confidence = 0.0
        if blocks:
            overall_confidence = sum(b.confidence for b in blocks) / len(blocks)
        
        # Extract keywords if requested
        keywords = []
        if extract_keywords and full_text:
            keywords = self._extract_keywords(full_text)
        
        return ScanResult(
            full_text=full_text.strip(),
            blocks=blocks,
            language=detected_language,
            confidence=overall_confidence,
            page_count=len(pages) or 1,
            detected_keywords=keywords
        )
    
    async def scan_document_image(
        self,
        image_base64: str
    ) -> Dict[str, Any]:
        """
        Scan a document image (printed text, diagrams, etc.).
        
        Args:
            image_base64: Base64 encoded image
            
        Returns:
            Dict with text and detected features
        """
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        
        request_body = {
            "requests": [{
                "image": {
                    "content": image_base64
                },
                "features": [
                    {"type": "DOCUMENT_TEXT_DETECTION"},
                    {"type": "LABEL_DETECTION", "maxResults": 10},
                ]
            }]
        }
        
        result = await self._make_vision_request(request_body)
        
        annotations = result.get("responses", [{}])[0]
        
        full_text = annotations.get("fullTextAnnotation", {}).get("text", "")
        labels = [
            label.get("description", "") 
            for label in annotations.get("labelAnnotations", [])
        ]
        
        return {
            "text": full_text.strip(),
            "labels": labels,
            "is_handwritten": "handwriting" in [l.lower() for l in labels]
        }
    
    def _extract_keywords(self, text: str, max_keywords: int = 15) -> List[str]:
        """
        Extract key terms and concepts from text.
        Uses simple frequency-based extraction with academic term detection.
        """
        import re
        from collections import Counter
        
        # Common stop words to filter
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "shall", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "under", "again",
            "further", "then", "once", "here", "there", "when", "where", "why",
            "how", "all", "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
            "just", "and", "but", "if", "or", "because", "until", "while", "this",
            "that", "these", "those", "it", "its", "i", "me", "my", "we", "our",
            "you", "your", "he", "him", "his", "she", "her", "they", "them", "their"
        }
        
        # Clean and tokenize
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter stop words
        filtered_words = [w for w in words if w not in stop_words]
        
        # Count frequencies
        word_counts = Counter(filtered_words)
        
        # Get top keywords
        keywords = [word for word, count in word_counts.most_common(max_keywords)]
        
        # Also look for multi-word terms (simple n-gram detection)
        # Find capitalized sequences that might be proper nouns or terms
        proper_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        for term in proper_terms[:5]:
            if term.lower() not in [k.lower() for k in keywords]:
                keywords.append(term)
        
        return keywords[:max_keywords]


# Singleton instance
_vision_service: Optional[VisionService] = None


def get_vision_service() -> VisionService:
    """Get or create vision service instance."""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
