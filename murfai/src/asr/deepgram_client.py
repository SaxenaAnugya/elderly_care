"""Deepgram ASR client with Patience Mode for elderly users."""
import asyncio
import json
import logging
from typing import Optional, Callable
import aiohttp
from ..config import Config

logger = logging.getLogger(__name__)

class DeepgramASRClient:
    """ASR client with extended silence detection for patience mode."""
    
    def __init__(self, api_key: str, on_transcript: Callable[[str], None], patience_mode_ms: Optional[int] = None):
        """
        Initialize Deepgram ASR client.
        
        Args:
            api_key: Deepgram API key
            on_transcript: Callback function called when transcript is received
            patience_mode_ms: Patience mode silence detection in milliseconds (overrides Config)
        """
        self.api_key = api_key
        self.on_transcript = on_transcript
        self.websocket = None
        self._session: Optional[aiohttp.ClientSession] = None
        self.is_listening = False
        self.patience_mode_ms = patience_mode_ms if patience_mode_ms is not None else Config.PATIENCE_MODE_SILENCE_MS
        
    async def connect(self):
        """Establish WebSocket connection to Deepgram."""
        try:
            uri = f"wss://api.deepgram.com/v1/listen?model={Config.ASR_MODEL}&language=en-US&punctuate=true&interim_results=true&endpointing={self.patience_mode_ms}"

            headers = {
                "Authorization": f"Token {self.api_key}"
            }

            self._session = aiohttp.ClientSession()
            self.websocket = await self._session.ws_connect(uri, headers=headers)
            logger.info("Connected to Deepgram ASR (via aiohttp)")
            
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            raise
    
    async def start_listening(self, audio_stream):
        """
        Start listening to audio stream.
        
        Args:
            audio_stream: Async generator yielding audio chunks
        """
        if not self.websocket:
            await self.connect()
        
        self.is_listening = True
        
        async def send_audio():
            """Send audio chunks to Deepgram."""
            try:
                async for audio_chunk in audio_stream:
                    if self.websocket and self.is_listening:
                        # aiohttp WebSocket client expects bytes to be sent with send_bytes
                        await self.websocket.send_bytes(audio_chunk)
            except Exception as e:
                logger.error(f"Error sending audio: {e}")
                self.is_listening = False
        
        async def receive_transcripts():
            """Receive transcripts from Deepgram (aiohttp WebSocket messages)."""
            try:
                async for msg in self.websocket:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                        except Exception:
                            logger.debug("Received non-json text from Deepgram")
                            continue

                        if "channel" in data and "alternatives" in data["channel"]:
                            transcript = data["channel"]["alternatives"][0].get("transcript", "")
                            is_final = data.get("is_final", False)

                            if transcript and is_final:
                                logger.info(f"Final transcript: {transcript}")
                                await self.on_transcript(transcript)
                            elif transcript:
                                logger.debug(f"Interim transcript: {transcript}")
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error from Deepgram: {msg}")
                        break
            except Exception as e:
                logger.error(f"Error receiving transcripts: {e}")
                self.is_listening = False
        
        # Run both tasks concurrently
        await asyncio.gather(
            send_audio(),
            receive_transcripts()
        )
    
    async def stop_listening(self):
        """Stop listening and close connection."""
        self.is_listening = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected from Deepgram ASR")
        if self._session:
            await self._session.close()
            self._session = None

