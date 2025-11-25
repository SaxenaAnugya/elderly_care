"""Murf Falcon TTS client with dynamic voice style switching."""
import aiohttp
import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime
from ..config import Config

logger = logging.getLogger(__name__)

class MurfTTSClient:
    """TTS client using Murf Falcon API with emotion-based voice styles."""
    
    def __init__(self, api_key: str, api_url: str):
        """
        Initialize Murf TTS client.
        
        Args:
            api_key: Murf API key
            api_url: Murf API base URL
        """
        self.api_key = api_key
        self.api_url = api_url
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self):
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _get_voice_style(self, sentiment: str, time_of_day: Optional[datetime] = None) -> Dict:
        """
        Determine voice style based on sentiment and time of day.
        
        Args:
            sentiment: Detected sentiment (happy, sad, neutral)
            time_of_day: Current datetime for Sundowning detection
            
        Returns:
            Dict with voice parameters
        """
        # Check for Sundowning (after 5 PM)
        is_sundowning = False
        if time_of_day:
            current_hour = time_of_day.hour
            is_sundowning = current_hour >= Config.SUNDOWNING_HOUR
        
        # Base style from sentiment
        style_name = Config.VOICE_STYLES.get(sentiment, "Conversational")
        
        # Adjust for Sundowning
        if is_sundowning:
            speech_rate = Config.CALM_SPEECH_RATE
            pitch = Config.CALM_PITCH
            style_name = "Soft"  # Override with calming style
        else:
            speech_rate = Config.DEFAULT_SPEECH_RATE
            pitch = Config.DEFAULT_PITCH
        
        # Special handling for sad sentiment
        if sentiment == "sad":
            style_name = "Whisper"
            speech_rate = Config.CALM_SPEECH_RATE
            pitch = Config.CALM_PITCH
        
        return {
            "style": style_name,
            "rate": speech_rate,
            "pitch": pitch
        }
    
    async def synthesize(
        self,
        text: str,
        sentiment: str = "neutral",
        voice_id: Optional[str] = None
    ) -> bytes:
        """
        Synthesize speech from text with emotion-based styling.
        
        Args:
            text: Text to synthesize
            sentiment: Detected sentiment (happy, sad, neutral)
            voice_id: Optional voice ID override
            
        Returns:
            bytes: Audio data (WAV format)
        """
        if not self.api_key:
            raise ValueError("Murf API key not configured")
        
        session = await self._get_session()
        
        # Get voice parameters based on sentiment and time
        voice_params = self._get_voice_style(sentiment, datetime.now())
        
        # Prepare request payload
        # NOTE: Adjust payload structure based on actual Murf Falcon API documentation
        # The structure below is a placeholder - verify with Murf API docs:
        # https://developers.murf.ai/ or your Murf dashboard API documentation
        payload = {
            "text": text,
            "voiceId": voice_id or Config.MURF_VOICE_ID,
            "style": voice_params["style"],
            "rate": voice_params["rate"],
            "pitch": voice_params["pitch"],
            "format": "wav",
            "sampleRate": 24000
        }
        
        # NOTE: Verify authentication method with Murf API docs
        # May be "Bearer", "X-API-Key", or other header format
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # NOTE: Verify endpoint path - may be "/v1/tts", "/api/tts", or other
        try:
            async with session.post(
                f"{self.api_url}/tts",  # Adjust endpoint as per Murf API docs
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    logger.info(f"Synthesized speech: {text[:50]}... (style: {voice_params['style']})")
                    return audio_data
                else:
                    error_text = await response.text()
                    logger.error(f"Murf API error {response.status}: {error_text}")
                    raise Exception(f"Murf API error: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            raise
    
    async def play_audio(self, audio_data: bytes):
        """
        Play audio data (placeholder - implement with pyaudio or similar).
        
        Args:
            audio_data: Audio bytes to play
        """
        # This would typically use pyaudio or another audio library
        # For now, we'll return the audio data for external playback
        logger.info("Audio ready for playback")
        return audio_data
    
    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

