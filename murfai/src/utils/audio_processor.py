"""Audio processing utilities for ASR and TTS."""
import aiohttp
import logging
from typing import Optional
from ..config import Config

logger = logging.getLogger(__name__)

async def transcribe_audio_with_deepgram(audio_data: bytes, api_key: str, content_type: str = "audio/webm") -> str:
    """
    Transcribe audio using Deepgram REST API.
    
    Args:
        audio_data: Audio file bytes
        api_key: Deepgram API key
        content_type: Audio MIME type (webm, wav, mp3, etc.)
        
    Returns:
        Transcribed text
    """
    try:
        # Deepgram API endpoint with parameters
        url = f"https://api.deepgram.com/v1/listen?model={Config.ASR_MODEL}&language=en-US&punctuate=true&interim_results=false&endpointing={Config.PATIENCE_MODE_SILENCE_MS}"
        
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": content_type
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=audio_data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    # Parse Deepgram response
                    transcript = ""
                    if "results" in result and "channels" in result["results"]:
                        channels = result["results"]["channels"]
                        if channels and len(channels) > 0:
                            alternatives = channels[0].get("alternatives", [])
                            if alternatives and len(alternatives) > 0:
                                transcript = alternatives[0].get("transcript", "")
                    
                    if transcript:
                        logger.info(f"Transcribed: {transcript}")
                        return transcript
                    else:
                        logger.warning("No transcript found in Deepgram response")
                        return ""
                else:
                    error_text = await response.text()
                    logger.error(f"Deepgram API error {response.status}: {error_text}")
                    raise Exception(f"Deepgram API error {response.status}: {error_text}")
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise

async def synthesize_speech_with_murf(text: str, sentiment: str = "neutral", api_key: str = None, api_url: str = None) -> bytes:
    """
    Synthesize speech using Murf TTS API.
    
    Args:
        text: Text to synthesize
        sentiment: Sentiment for voice style
        api_key: Murf API key (uses Config if not provided)
        api_url: Murf API URL (uses Config if not provided)
        
    Returns:
        Audio bytes (WAV format)
    """
    try:
        api_key = api_key or Config.MURF_API_KEY
        api_url = api_url or Config.MURF_API_URL
        
        if not api_key:
            raise ValueError("Murf API key not configured")
        
        # Import TTS client
        from ..tts.murf_client import MurfTTSClient
        
        tts_client = MurfTTSClient(api_key, api_url)
        audio_data = await tts_client.synthesize(text, sentiment=sentiment)
        await tts_client.close()
        
        return audio_data
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise

