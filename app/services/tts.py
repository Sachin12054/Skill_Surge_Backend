import httpx
from typing import List
from app.core.config import get_settings
import base64
import io
# from pydub import AudioSegment  # Commented out - requires audioop not available in Python 3.13

settings = get_settings()


class ElevenLabsService:
    """Service for text-to-speech using Sarvam AI API."""
    
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.base_url = "https://api.sarvam.ai"
        # Sarvam speakers: anushka, manisha, vidya, arya (female), abhilash, karun, hitesh (male)
        self.voice_1 = "anushka"  # Female voice
        self.voice_2 = "abhilash"  # Male voice
    
    async def generate_speech(
        self,
        text: str,
        voice_id: str = None,
        model_id: str = "bulbul:v2",
    ) -> bytes:
        """Generate speech from text using Sarvam AI."""
        speaker = voice_id or self.voice_1
        
        # Truncate text if too long (Sarvam limit is 1500 chars)
        if len(text) > 1500:
            text = text[:1497] + "..."
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/text-to-speech",
                headers={
                    "api-subscription-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "target_language_code": "en-IN",
                    "speaker": speaker,
                    "model": model_id,
                    "pitch": 0,
                    "pace": 1.0,
                    "loudness": 1.0,
                    "speech_sample_rate": 22050,
                    "enable_preprocessing": True,
                },
                timeout=120.0,
            )
            
            if response.status_code != 200:
                raise Exception(f"Sarvam API error: {response.text}")
            
            data = response.json()
            # Sarvam returns base64 encoded audio
            audio_base64 = data.get("audios", [None])[0]
            if not audio_base64:
                raise Exception("No audio returned from Sarvam API")
            
            # Decode base64 to bytes
            return base64.b64decode(audio_base64)
    
    async def generate_dialogue(
        self,
        script: List[dict],
    ) -> bytes:
        """
        Generate a dialogue audio from a script.
        
        Script format:
        [
            {"speaker": 1, "text": "Hello!"},
            {"speaker": 2, "text": "Hi there!"},
        ]
        """
        audio_segments = []
        
        for line in script:
            voice = self.voice_1 if line["speaker"] == 1 else self.voice_2
            try:
                audio = await self.generate_speech(line["text"], voice)
                audio_segments.append(audio)
            except Exception as e:
                print(f"Error generating speech for line: {e}")
                continue
        
        if not audio_segments:
            raise Exception("No audio segments generated")
        
        # Combine audio segments
        return self._combine_audio(audio_segments)
    
    def _combine_audio(self, segments: List[bytes]) -> bytes:
        """Combine multiple audio segments into one using pydub."""
        if not segments:
            return b""
        
        if len(segments) == 1:
            return segments[0]
        
        # TODO: Requires pydub with audioop support or Python < 3.13
        # For now, return the first segment as fallback
        # Full implementation requires: pip install pydub (Python 3.12) or alternative audio library
        print("WARNING: Audio combining disabled - pydub requires audioop (Python 3.13 incompatible)")
        return segments[0]
        
        # # Load first segment
        # combined = AudioSegment.from_file(io.BytesIO(segments[0]), format="wav")
        # 
        # # Append remaining segments
        # for segment_bytes in segments[1:]:
        #     audio_segment = AudioSegment.from_file(io.BytesIO(segment_bytes), format="wav")
        #     combined += audio_segment
        # 
        # # Export as MP3
        # output_buffer = io.BytesIO()
        # combined.export(output_buffer, format="mp3", bitrate="128k")
        # output_buffer.seek(0)
        # return output_buffer.read()
    
    async def get_voices(self) -> List[dict]:
        """Get available voices."""
        return [
            {"name": "Anushka", "voice_id": "Anushka", "gender": "female"},
            {"name": "Manisha", "voice_id": "Manisha", "gender": "female"},
            {"name": "Vidya", "voice_id": "Vidya", "gender": "female"},
            {"name": "Arya", "voice_id": "Arya", "gender": "female"},
            {"name": "Abhilash", "voice_id": "Abhilash", "gender": "male"},
            {"name": "Karun", "voice_id": "Karun", "gender": "male"},
            {"name": "Hitesh", "voice_id": "Hitesh", "gender": "male"},
        ]


def get_elevenlabs_service() -> ElevenLabsService:
    """Get ElevenLabs service instance."""
    return ElevenLabsService()
