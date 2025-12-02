"""Configuration management for the Loneliness Companion."""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration."""
    
    # API Keys
    MURF_API_KEY = os.getenv("MURF_API_KEY", "")
    MURF_API_URL = os.getenv("MURF_API_URL", "https://api.murf.ai/v1")
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
    # NOTE: DEFAULT_VOICE_LOCALE, PATIENCE_MODE_SILENCE_MS, and SUNDOWNING_HOUR
    # are now managed in the database via settings. These are hardcoded defaults
    # only used as fallback when database is not available.
    DEFAULT_VOICE_LOCALE = "en-US"  # Hardcoded default (not from .env)
    
    # ASR Settings - Patience Mode
    PATIENCE_MODE_SILENCE_MS = 2000  # Hardcoded default (not from .env)
    ASR_MODEL = "nova-3"  # Deepgram model optimized for conversational audio
    
    # TTS Settings - Murf Falcon
    MURF_VOICE_ID = "en-US-Neural"  # Base voice ID (adjust based on available voices)
    # Voice IDs for male and female voices (adjust based on available voices in Murf)
    MURF_VOICE_FEMALE = "en-US-Neural-Female"  # Female voice ID
    MURF_VOICE_MALE = "en-US-Neural-Male"  # Male voice ID
    DEFAULT_SPEECH_RATE = 1.0
    CALM_SPEECH_RATE = 0.9  # 10% slower for Sundowning
    DEFAULT_PITCH = 0.0
    CALM_PITCH = -0.1  # Slightly lower pitch for calming effect
    
    # Time-based Settings
    SUNDOWNING_HOUR = 17  # Hardcoded default (not from .env) - 5 PM
    
    # Medication Reminders
    MEDICATION_REMINDER_INTERVAL_MINUTES = int(os.getenv("MEDICATION_REMINDER_INTERVAL_MINUTES", "60"))
    MEDICATION_NUDGE_LEAD_MINUTES = int(os.getenv("MEDICATION_NUDGE_LEAD_MINUTES", "10"))
    MEDICATION_NUDGE_GRACE_MINUTES = int(os.getenv("MEDICATION_NUDGE_GRACE_MINUTES", "2"))
    
    # Voice Styles for Murf Falcon (based on sentiment)
    VOICE_STYLES = {
        "happy": "Excited",
        "sad": "Whisper",
        "neutral": "Conversational",
        "calm": "Soft"
    }
    
    # Listening sounds during pauses
    LISTENING_SOUNDS = [
        "Hmm...",
        "Go on...",
        "I'm listening...",
        "Take your time..."
    ]
    
    # Database
    DB_PATH = "conversation_memory.db"

