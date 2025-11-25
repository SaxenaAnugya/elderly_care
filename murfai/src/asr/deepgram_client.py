"""Deepgram ASR client with Patience Mode for elderly users."""
import asyncio
import json
import websockets
from typing import Optional, Callable
import logging
from ..config import Config

logger = logging.getLogger(__name__)

class DeepgramASRClient:
    """ASR client with extended silence detection for patience mode."""
    
    def __init__(self, api_key: str, on_transcript: Callable[[str], None]):
        """
        Initialize Deepgram ASR client.
        
        Args:
            api_key: Deepgram API key
            on_transcript: Callback function called when transcript is received
        """
        self.api_key = api_key
        self.on_transcript = on_transcript
        self.websocket = None
        self.is_listening = False
        
    async def connect(self):
        """Establish WebSocket connection to Deepgram."""
        try:
            uri = f"wss://api.deepgram.com/v1/listen?model={Config.ASR_MODEL}&language=en-US&punctuate=true&interim_results=true&endpointing={Config.PATIENCE_MODE_SILENCE_MS}"
            
            headers = {
                "Authorization": f"Token {self.api_key}"
            }
            
            self.websocket = await websockets.connect(uri, extra_headers=headers)
            logger.info("Connected to Deepgram ASR")
            
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
                        await self.websocket.send(audio_chunk)
            except Exception as e:
                logger.error(f"Error sending audio: {e}")
                self.is_listening = False
        
        async def receive_transcripts():
            """Receive transcripts from Deepgram."""
            try:
                async for message in self.websocket:
                    data = json.loads(message)
                    
                    if "channel" in data and "alternatives" in data["channel"]:
                        transcript = data["channel"]["alternatives"][0].get("transcript", "")
                        is_final = data.get("is_final", False)
                        
                        if transcript and is_final:
                            logger.info(f"Final transcript: {transcript}")
                            await self.on_transcript(transcript)
                        elif transcript:
                            # Interim result - user is still speaking
                            logger.debug(f"Interim transcript: {transcript}")
                            
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

