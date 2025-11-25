"""Audio capture for microphone input."""
import pyaudio
import asyncio
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

class AudioCapture:
    """Capture audio from microphone for ASR."""
    
    def __init__(self, sample_rate=16000, chunk_size=1024, channels=1):
        """
        Initialize audio capture.
        
        Args:
            sample_rate: Audio sample rate (Hz)
            chunk_size: Number of frames per buffer
            channels: Number of audio channels
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
    def start_stream(self):
        """Start audio input stream."""
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            logger.info("Audio stream started")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            raise
    
    async def audio_generator(self) -> AsyncGenerator[bytes, None]:
        """
        Async generator yielding audio chunks.
        
        Yields:
            bytes: Audio chunk data
        """
        if not self.stream:
            self.start_stream()
        
        try:
            while True:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                yield data
        except Exception as e:
            logger.error(f"Error in audio capture: {e}")
            raise
    
    def stop_stream(self):
        """Stop audio input stream."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            logger.info("Audio stream stopped")
    
    def cleanup(self):
        """Clean up audio resources."""
        self.stop_stream()
        self.audio.terminate()

