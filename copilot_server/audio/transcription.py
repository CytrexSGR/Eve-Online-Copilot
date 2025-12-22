"""
Audio Transcription (STT)
Speech-to-Text using OpenAI Whisper API.
"""

from openai import OpenAI
from typing import Optional, BinaryIO
import logging
import io

from ..config import OPENAI_API_KEY, WHISPER_MODEL

logger = logging.getLogger(__name__)


class AudioTranscriber:
    """Handles speech-to-text transcription using Whisper API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize transcriber.

        Args:
            api_key: OpenAI API key
            model: Whisper model to use
        """
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or WHISPER_MODEL
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

        if not self.client:
            logger.warning("No OpenAI API key - transcription will not work")

    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio to text.

        Args:
            audio_data: Audio file bytes
            language: Language code (e.g., 'en', 'de')
            prompt: Optional context prompt

        Returns:
            Transcription result
        """
        if not self.client:
            return {
                "error": "OpenAI API key not configured",
                "text": ""
            }

        try:
            # Create file-like object
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.webm"  # Whisper needs a filename

            # Call Whisper API
            params = {
                "model": self.model,
                "file": audio_file
            }

            if language:
                params["language"] = language

            if prompt:
                params["prompt"] = prompt

            transcript = self.client.audio.transcriptions.create(**params)

            logger.info("Audio transcribed successfully")
            return {
                "text": transcript.text,
                "language": language or "auto"
            }

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "error": str(e),
                "text": ""
            }

    async def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio from file path.

        Args:
            file_path: Path to audio file
            language: Language code

        Returns:
            Transcription result
        """
        try:
            with open(file_path, "rb") as f:
                audio_data = f.read()
            return await self.transcribe(audio_data, language=language)
        except Exception as e:
            logger.error(f"File transcription failed: {e}")
            return {
                "error": str(e),
                "text": ""
            }
