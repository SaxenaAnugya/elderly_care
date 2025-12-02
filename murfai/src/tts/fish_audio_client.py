"""Fish Audio TTS client for voice cloning."""
import asyncio
import logging
from typing import Optional, Dict, List
import aiohttp
import base64

from ..config import Config

logger = logging.getLogger(__name__)


class FishAudioClient:
    """TTS client using Fish Audio API for voice cloning."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.fish.audio"
        self._voices_cache: Dict[str, List[Dict]] = {"voices": [], "ts": 0}
        
        # Set default headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def synthesize(
        self,
        text: str,
        reference_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bytes:
        """
        Synthesize speech using Fish Audio API.
        
        Args:
            text: Text to synthesize
            reference_id: Voice model ID from fish.audio (for voice cloning)
            language: Language code (e.g., 'en', 'hi')
            
        Returns:
            Audio bytes (MP3 format)
        """
        if not text or not text.strip():
            raise ValueError("Text is empty for TTS")

        if not self.api_key:
            raise ValueError("Fish Audio API key not configured")

        url = f"{self.base_url}/v1/tts/convert"
        
        headers = self.headers.copy()

        payload = {
            "text": text,
        }

        if reference_id:
            payload["reference_id"] = reference_id

        if language:
            payload["language"] = language

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(
                            f"Fish Audio API error: {response.status} - {error_text}"
                        )

                    # Fish Audio returns audio as base64 string or direct bytes
                    content_type = response.headers.get("Content-Type", "")
                    
                    if "application/json" in content_type:
                        # JSON response with base64 audio
                        data = await response.json()
                        audio_b64 = data.get("audio") or data.get("data") or data.get("audioData")
                        if isinstance(audio_b64, str):
                            audio_bytes = base64.b64decode(audio_b64)
                        elif isinstance(audio_b64, (bytes, bytearray)):
                            audio_bytes = bytes(audio_b64)
                        else:
                            raise RuntimeError("Fish Audio returned invalid audio format")
                    else:
                        # Direct audio bytes
                        audio_bytes = await response.read()

                    if not audio_bytes or len(audio_bytes) == 0:
                        raise RuntimeError("Fish Audio returned empty audio")

                    logger.info(f"Fish Audio generated {len(audio_bytes)} bytes of audio")
                    return audio_bytes

        except aiohttp.ClientError as e:
            logger.error(f"Fish Audio HTTP error: {e}")
            raise RuntimeError(f"Fish Audio HTTP error: {e}") from e
        except Exception as e:
            logger.error(f"Fish Audio synthesis error: {e}")
            raise

    async def list_voices(self, limit: int = 50) -> List[Dict]:
        """
        List available voices from Fish Audio.
        
        Args:
            limit: Maximum number of voices to return
            
        Returns:
            List of voice dictionaries with id, name, description, etc.
        """
        url = f"{self.base_url}/v1/voices"
        
        headers = self.headers.copy()

        params = {
            "limit": limit,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(
                            f"Fish Audio API error: {response.status} - {error_text}"
                        )

                    data = await response.json()
                    
                    # Handle different response formats
                    if isinstance(data, list):
                        voices = data
                    elif isinstance(data, dict):
                        voices = data.get("voices") or data.get("data") or []
                    else:
                        voices = []

                    logger.info(f"Retrieved {len(voices)} voices from Fish Audio")
                    return voices

        except aiohttp.ClientError as e:
            logger.error(f"Fish Audio HTTP error: {e}")
            raise RuntimeError(f"Fish Audio HTTP error: {e}") from e
        except Exception as e:
            logger.error(f"Fish Audio list voices error: {e}")
            raise

    async def get_voice_info(self, reference_id: str) -> Dict:
        """
        Get information about a specific voice.
        
        Args:
            reference_id: Voice model ID
            
        Returns:
            Voice information dictionary
        """
        url = f"{self.base_url}/v1/voices/{reference_id}"
        
        headers = self.headers.copy()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(
                            f"Fish Audio API error: {response.status} - {error_text}"
                        )

                    data = await response.json()
                    return data

        except aiohttp.ClientError as e:
            logger.error(f"Fish Audio HTTP error: {e}")
            raise RuntimeError(f"Fish Audio HTTP error: {e}") from e
        except Exception as e:
            logger.error(f"Fish Audio get voice info error: {e}")
            raise

    async def close(self):
        """Close underlying resources if any."""
        # No persistent connections to close
        return

