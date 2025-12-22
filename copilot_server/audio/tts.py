"""
Text-to-Speech (TTS)
Text-to-Speech using OpenAI TTS API.
"""

from openai import OpenAI
from typing import Optional
import logging

from ..config import OPENAI_API_KEY, TTS_MODEL, TTS_VOICE

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Handles text-to-speech using OpenAI TTS API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        voice: Optional[str] = None
    ):
        """
        Initialize TTS.

        Args:
            api_key: OpenAI API key
            model: TTS model to use
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        """
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or TTS_MODEL
        self.voice = voice or TTS_VOICE
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

        if not self.client:
            logger.warning("No OpenAI API key - TTS will not work")

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> bytes:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            voice: Voice to use (overrides default)
            speed: Speech speed (0.25 to 4.0)

        Returns:
            Audio data as bytes
        """
        if not self.client:
            logger.error("OpenAI API key not configured")
            return b""

        try:
            response = self.client.audio.speech.create(
                model=self.model,
                voice=voice or self.voice,
                input=text,
                speed=speed
            )

            # Read audio bytes
            audio_data = response.read()
            logger.info(f"Synthesized {len(audio_data)} bytes of audio")
            return audio_data

        except Exception as e:
            logger.error(f"TTS failed: {e}")
            return b""

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None
    ) -> bool:
        """
        Synthesize speech and save to file.

        Args:
            text: Text to synthesize
            output_path: Output file path
            voice: Voice to use

        Returns:
            True if successful
        """
        try:
            audio_data = await self.synthesize(text, voice=voice)
            if audio_data:
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                logger.info(f"Saved TTS audio to {output_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save TTS: {e}")
            return False
