"""Audio playback utility."""
import pyaudio
import wave
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AudioPlayer:
    """Play audio from bytes data."""
    
    def __init__(self, sample_rate=24000, channels=1, format=pyaudio.paInt16):
        """
        Initialize audio player.
        
        Args:
            sample_rate: Audio sample rate
            channels: Number of channels
            format: Audio format
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.format = format
        self.audio = pyaudio.PyAudio()
    
    def play_bytes(self, audio_data: bytes):
        """
        Play audio from bytes.
        
        Args:
            audio_data: Audio data in WAV format
        """
        try:
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_data)
            
            # Open WAV file
            wf = wave.open(audio_file, 'rb')
            
            # Open audio stream
            stream = self.audio.open(
                format=self.audio.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )
            
            # Play audio
            data = wf.readframes(1024)
            while data:
                stream.write(data)
                data = wf.readframes(1024)
            
            # Cleanup
            stream.stop_stream()
            stream.close()
            wf.close()
            
            logger.debug("Audio playback completed")
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            raise
    
    def cleanup(self):
        """Clean up audio resources."""
        self.audio.terminate()

