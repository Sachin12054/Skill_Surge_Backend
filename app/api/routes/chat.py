from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.core import get_supabase_service
from app.core.config import get_settings
from app.api.deps import get_current_user
from openai import AsyncOpenAI
import httpx
import fitz  # PyMuPDF

router = APIRouter(prefix="/chat", tags=["Multilingual Chatbot"])

settings = get_settings()

# Supported Indian languages for Sarvam translation
SUPPORTED_LANGUAGES = {
    "en-IN": "English",
    "hi-IN": "Hindi",
    "bn-IN": "Bengali",
    "gu-IN": "Gujarati",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "mr-IN": "Marathi",
    "od-IN": "Odia",
    "pa-IN": "Punjabi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "ur-IN": "Urdu",
    "as-IN": "Assamese",
    "kok-IN": "Konkani",
    "mai-IN": "Maithili",
    "ne-IN": "Nepali",
    "sa-IN": "Sanskrit",
    "sd-IN": "Sindhi",
    "doi-IN": "Dogri",
    "ks-IN": "Kashmiri",
    "mni-IN": "Manipuri",
    "sat-IN": "Santali",
}


class ChatRequest(BaseModel):
    message: str
    pdf_id: Optional[str] = None
    target_language: str = "en-IN"  # Default English (no translation needed)
    conversation_history: List[dict] = []


class ChatResponse(BaseModel):
    reply: str
    translated_reply: Optional[str] = None
    language: str
    language_name: str


@router.get("/languages")
async def get_supported_languages():
    """Return list of supported Indian languages for translation."""
    languages = [
        {"code": code, "name": name}
        for code, name in SUPPORTED_LANGUAGES.items()
    ]
    return {"languages": languages}


@router.post("/send", response_model=ChatResponse)
async def chat_with_pdf(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
):
    """
    Chat with GPT-4o-mini, optionally grounded on a selected PDF.
    The English response is translated to the target Indian language via Sarvam API.
    """
    supabase = get_supabase_service()

    # Build system prompt
    system_prompt = (
        "You are Cognito, an intelligent academic assistant. "
        "You help students understand their study materials clearly and concisely. "
        "When PDF context is provided, answer based on that content. "
        "If you don't know the answer from the provided context, say so honestly. "
        "Keep answers well-structured, use bullet points where helpful."
    )

    pdf_context = ""
    if request.pdf_id:
        try:
            # Fetch PDF metadata
            result = supabase.admin_client.table("space_pdfs").select("*").eq(
                "id", request.pdf_id
            ).eq("user_id", user["id"]).execute()

            if not result.data:
                raise HTTPException(status_code=404, detail="PDF not found")

            pdf = result.data[0]

            # Download and extract text from PDF
            content = supabase.download_file("course-materials", pdf["file_path"])
            doc = fitz.open(stream=content, filetype="pdf")
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            doc.close()

            # Truncate to stay within token limits (~12k chars ≈ 3k tokens)
            if len(full_text) > 12000:
                full_text = full_text[:12000] + "\n\n[...content truncated for length]"

            pdf_context = f"\n\n--- PDF Content: {pdf['name']} ---\n{full_text}\n--- End of PDF ---"
            system_prompt += (
                "\n\nYou have been given the content of a PDF document. "
                "Use it to answer the user's questions accurately. "
                "Reference specific parts of the document when relevant."
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error loading PDF for chat: {e}")
            # Continue without PDF context if loading fails
            pdf_context = ""

    # Build message history for OpenAI
    messages = [{"role": "system", "content": system_prompt + pdf_context}]

    # Add conversation history (limit to last 10 messages to stay within limits)
    for msg in request.conversation_history[-10:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": request.message})

    # Call GPT-4o-mini
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
        )
        english_reply = response.choices[0].message.content or "I couldn't generate a response."
    except Exception as e:
        print(f"OpenAI error: {e}")
        raise HTTPException(status_code=502, detail="Failed to generate AI response")

    # Translate if target language is not English
    translated_reply = None
    lang_code = request.target_language
    lang_name = SUPPORTED_LANGUAGES.get(lang_code, "English")

    if lang_code and lang_code != "en-IN":
        try:
            translated_reply = await translate_with_sarvam(english_reply, lang_code)
        except Exception as e:
            print(f"Sarvam translation error: {e}")
            # Return English reply even if translation fails
            translated_reply = None

    return ChatResponse(
        reply=english_reply,
        translated_reply=translated_reply,
        language=lang_code,
        language_name=lang_name,
    )


async def translate_with_sarvam(text: str, target_language_code: str) -> str:
    """Translate text from English to an Indian language using Sarvam API."""
    if not settings.SARVAM_API_KEY:
        raise ValueError("SARVAM_API_KEY not configured")

    # Sarvam mayura:v1 has a 1000 char limit per request, so chunk if needed
    chunks = _split_text_for_translation(text, max_chars=900)
    translated_chunks = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for chunk in chunks:
            payload = {
                "input": chunk,
                "source_language_code": "en-IN",
                "target_language_code": target_language_code,
                "model": "mayura:v1",
                "mode": "formal",
            }

            response = await client.post(
                "https://api.sarvam.ai/translate",
                json=payload,
                headers={
                    "api-subscription-key": settings.SARVAM_API_KEY,
                    "Content-Type": "application/json",
                },
            )

            if response.status_code != 200:
                error_detail = response.text
                print(f"Sarvam API error ({response.status_code}): {error_detail}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Translation failed: {response.status_code}",
                )

            data = response.json()
            translated_chunks.append(data.get("translated_text", chunk))

    return " ".join(translated_chunks)


def _split_text_for_translation(text: str, max_chars: int = 900) -> list[str]:
    """Split text into chunks that respect sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current = ""
    sentences = text.replace("\n", " \n ").split(". ")

    for sentence in sentences:
        candidate = (current + ". " + sentence).strip(". ") if current else sentence
        if len(candidate) > max_chars:
            if current:
                chunks.append(current.strip())
            current = sentence
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text[:max_chars]]