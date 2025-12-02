"""FastAPI backend server for Loneliness Companion frontend."""
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import subprocess
import shutil
import io
import tempfile

# Add parent directory to Python path so we can import from src
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.companion import LonelinessCompanion
from src.config import Config
from src.memory.conversation_db import ConversationMemory
from src.llm.response_generator import DynamicResponseGenerator
from src.sentiment.analyzer import SentimentAnalyzer
from src.utils.audio_processor import synthesize_speech_with_murf, transcribe_audio_with_deepgram

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _save_and_convert_debug_audio(session_id: str, label: str, audio_bytes: bytes, ext_hint: str = 'webm') -> Dict[str, str]:
    """Save raw received audio to received_audio/ as <label>.webm and attempt to convert to WAV using ffmpeg.
    Returns dict with paths: {'webm': str, 'wav': str|None}.
    """
    received_dir = project_root / "received_audio"
    received_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime as _dt
    base_name = f"ws_{session_id}_{label}_{_dt.now().strftime('%Y%m%dT%H%M%S%f') }"
    webm_name = base_name + f".{ext_hint}"
    webm_path = received_dir / webm_name
    try:
        with open(webm_path, 'wb') as f:
            f.write(audio_bytes)
        logger.info(f"Saved received audio for inspection: {webm_path}")
    except Exception as e:
        logger.warning(f"Failed to save received audio (webm): {e}")
        webm_path = None

    wav_path = None
    # Try to convert to WAV using ffmpeg if available
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        try:
            # Use subprocess with pipes to convert in-memory bytes
            proc = subprocess.Popen(
                [ffmpeg_path, '-hide_banner', '-loglevel', 'error', '-i', 'pipe:0', '-f', 'wav', 'pipe:1'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            out, err = proc.communicate(audio_bytes, timeout=15)
            if proc.returncode == 0 and out:
                wav_name = base_name + '.wav'
                wav_path = received_dir / wav_name
                with open(wav_path, 'wb') as wf:
                    wf.write(out)
                logger.info(f"Saved converted WAV for inspection: {wav_path}")
            else:
                logger.warning(f"ffmpeg conversion failed: rc={proc.returncode} err={err.decode('utf-8', errors='ignore')}")
        except Exception as e:
            logger.warning(f"ffmpeg conversion exception: {e}")
    else:
        logger.info("ffmpeg not found in PATH; skipping WAV conversion of received audio")

    return { 'webm': str(webm_path) if webm_path else '', 'wav': str(wav_path) if wav_path else '' }

# Initialize FastAPI app
app = FastAPI(title="Loneliness Companion API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global companion instance
companion: Optional[LonelinessCompanion] = None
memory: Optional[ConversationMemory] = None
active_sessions: Dict[str, Dict[str, Any]] = {}
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
llm_generator = DynamicResponseGenerator(api_provider=LLM_PROVIDER)
sentiment_analyzer = SentimentAnalyzer()

# Hardcoded default settings (not from .env - these come from database)
# These are only used if settings are not found in the database
DEFAULT_PATIENCE_MODE_MS = 2000
DEFAULT_SUNDOWNING_HOUR = 17
DEFAULT_VOICE_LOCALE = "en-US"

def get_effective_settings() -> Dict[str, Any]:
    """
    Get effective settings from database, falling back to hardcoded defaults.
    Settings are always loaded from database when available - no .env fallback.
    """
    default_settings = {
        "volume": 80,
        "speech_rate": 1.0,
        "patience_mode": DEFAULT_PATIENCE_MODE_MS,
        "sundowning_hour": DEFAULT_SUNDOWNING_HOUR,
        "medication_reminders_enabled": True,
        "word_of_day_enabled": True,
        "voice_gender": "female",  # Default to female voice
        "voice_locale": DEFAULT_VOICE_LOCALE,
    }
    
    if memory:
        try:
            saved_settings = memory.get_settings()
            # Update defaults with saved settings
            default_settings.update(saved_settings)
            logger.debug(f"Using settings from database: {list(saved_settings.keys())}")
        except Exception as e:
            logger.warning(f"Error loading settings from database: {e}, using defaults")
    
    return default_settings

def _normalize_locale(locale_value: Optional[str]) -> str:
    """Normalize locale value, using hardcoded default if not provided."""
    if not locale_value:
        return DEFAULT_VOICE_LOCALE
    return locale_value

def _session_state(session_id: str) -> Dict[str, Any]:
    session = active_sessions.setdefault(session_id, {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "is_listening": True,
        "is_speaking": False,
        "state": "idle",
        "reminiscence_turns_left": 0,
        "medication_nudges": {},
        "last_prompt_at": None,
    })
    return session

def _should_trigger_reminiscence(transcript: str, sentiment: str) -> bool:
    lowered = transcript.lower()
    keywords = [
        "lonely",
        "alone",
        "miss",
        "remember",
        "memory",
        "husband",
        "wife",
        "days",
        "old times",
        "childhood",
    ]
    if sentiment in ("sad", "negative"):
        return True
    return any(word in lowered for word in keywords)

async def _build_response_for_transcript(
    transcript: str,
    session_id: str,
    trigger: str,
    forced_state: Optional[str] = None,
    topic: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")

    settings = get_effective_settings()
    voice_locale = _normalize_locale(settings.get("voice_locale"))
    session_ctx = _session_state(session_id)
    logger.info(f"[Pipeline] Processing transcript trigger={trigger} len={len(transcript)} chars (session {session_id})")

    sentiment_result = sentiment_analyzer.analyze(transcript)

    conversation_state = forced_state or session_ctx.get("state", "idle")
    if conversation_state == "idle" and _should_trigger_reminiscence(transcript, sentiment_result["sentiment"]):
        conversation_state = "reminiscence"
        session_ctx["state"] = "reminiscence"
        session_ctx["reminiscence_turns_left"] = 3
        session_ctx["last_reminiscence_at"] = datetime.now().isoformat()
    elif conversation_state == "reminiscence":
        turns_left = session_ctx.get("reminiscence_turns_left", 3) - 1
        session_ctx["reminiscence_turns_left"] = turns_left
        if turns_left <= 0 or any(stop in transcript.lower() for stop in ("stop", "enough", "done")):
            session_ctx["state"] = "idle"
            conversation_state = "idle"

    context = memory.get_conversation_context(limit=5)

    try:
        response_text = await llm_generator.generate_response(
            user_message=transcript,
            sentiment=sentiment_result["sentiment"],
            context=context,
            state=conversation_state,
            additional_context=additional_context,
        )
    except Exception as e:
        logger.error(f"LLM generation error: {e}", exc_info=True)
        response_text = "I'm here with you. Would you like to tell me a memory or how you're feeling?"

    if not response_text:
        response_text = "I'm right here whenever you want to continue."

    speech_rate = settings.get("speech_rate", 1.0)
    sundowning_hour = settings.get("sundowning_hour", DEFAULT_SUNDOWNING_HOUR)
    voice_gender = settings.get("voice_gender", "female")

    response_audio: Optional[bytes] = None
    if Config.MURF_API_KEY:
        try:
            response_audio = await synthesize_speech_with_murf(
                response_text,
                sentiment=sentiment_result["sentiment"],
                api_key=Config.MURF_API_KEY,
                api_url=Config.MURF_API_URL,
                speech_rate=speech_rate,
                sundowning_hour=sundowning_hour,
                voice_gender=voice_gender,
                voice_locale=voice_locale,
            )
        except Exception as e:
            logger.error(f"Murf synthesis failed: {e}", exc_info=True)
            response_audio = None

    memory.save_conversation(
        transcript,
        response_text,
        sentiment=sentiment_result["sentiment"],
        topic=topic or conversation_state,
    )

    return {
        "text": response_text,
        "sentiment": sentiment_result["sentiment"],
        "audio": response_audio,
        "voice_locale": voice_locale,
        "state": conversation_state,
    }

async def _send_medication_nudge(
    session_id: str,
    safe_send_json,
    medication: Dict[str, Any],
    phase: str,
):
    settings = get_effective_settings()
    locale = _normalize_locale(settings.get("voice_locale"))
    med_name = medication.get("medication_name", "your medicine")
    due_time = medication.get("time")

    if locale.lower().startswith("hi"):
        if phase == "upcoming":
            message = f"लगभग {due_time} बजे {med_name} लेने का समय आने वाला है। क्या हम इसे तैयार रखें?"
        else:
            message = f"अब {med_name} लेने का समय है। क्या आपने ले लिया?"
    else:
        if phase == "upcoming":
            message = f"It's almost time for your {med_name} around {due_time}. Shall we get it ready?"
        else:
            message = f"It's time to take {med_name}. Have you had it yet?"

    await safe_send_json({
        "type": "medication_nudge",
        "phase": phase,
        "medication": medication,
        "text": message,
    })

    audio_payload = None
    if Config.MURF_API_KEY:
        try:
            audio_payload = await synthesize_speech_with_murf(
                message,
                sentiment="neutral",
                api_key=Config.MURF_API_KEY,
                api_url=Config.MURF_API_URL,
                speech_rate=settings.get("speech_rate", 1.0),
                sundowning_hour=settings.get("sundowning_hour", DEFAULT_SUNDOWNING_HOUR),
                voice_gender=settings.get("voice_gender", "female"),
                voice_locale=locale,
            )
        except Exception as e:
            logger.error(f"Medication nudge TTS failed: {e}", exc_info=True)

    if audio_payload:
        import base64
        await safe_send_json({
            "type": "audio",
            "data": base64.b64encode(audio_payload).decode("utf-8"),
            "format": "wav",
        })

    memory.save_conversation(
        "[medication_nudge]",
        message,
        sentiment="neutral",
        topic="medication_nudge",
    )

def _time_to_minutes(time_str: str) -> Optional[int]:
    try:
        parts = time_str.split(":")
        if len(parts) < 2:
            return None
        hour = int(parts[0])
        minute = int(parts[1])
        return hour * 60 + minute
    except Exception:
        return None

async def _medication_nudge_loop(session_id: str, safe_send_json, stop_event: asyncio.Event):
    if not memory:
        return

    logger.info(f"Starting medication nudge loop for session {session_id}")
    lead = Config.MEDICATION_NUDGE_LEAD_MINUTES
    grace = Config.MEDICATION_NUDGE_GRACE_MINUTES

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=30)
            if stop_event.is_set():
                break
        except asyncio.TimeoutError:
            pass

        try:
            meds = memory.get_all_medications()
            if not meds:
                continue

            now = datetime.now()
            now_minutes = now.hour * 60 + now.minute
            session_ctx = _session_state(session_id)
            nudges = session_ctx.setdefault("medication_nudges", {})

            for med in meds:
                med_time = med.get("time")
                med_minutes = _time_to_minutes(med_time) if med_time else None
                if med_minutes is None:
                    continue

                diff = med_minutes - now_minutes
                med_id = med.get("id", med_time)
                day_key = now.strftime("%Y-%m-%d")

                upcoming_key = f"{med_id}_upcoming_{day_key}"
                due_key = f"{med_id}_due_{day_key}"

                if 0 < diff <= lead and upcoming_key not in nudges:
                    await _send_medication_nudge(session_id, safe_send_json, med, "upcoming")
                    nudges[upcoming_key] = now.isoformat()

                if abs(diff) <= grace and due_key not in nudges:
                    await _send_medication_nudge(session_id, safe_send_json, med, "due")
                    nudges[due_key] = now.isoformat()
                    if med.get("id"):
                        memory.mark_medication_reminded(med["id"])
        except Exception as med_err:
            logger.error(f"Medication nudge loop error: {med_err}", exc_info=True)

    logger.info(f"Medication nudge loop stopped for session {session_id}")

# Pydantic models
class ConversationMessage(BaseModel):
    user_message: str
    ai_response: str
    sentiment: Optional[str] = None
    topic: Optional[str] = None

class Medication(BaseModel):
    medication_name: str
    time: str
    last_reminded: Optional[str] = None
    last_taken: Optional[str] = None

class MedicationResponse(Medication):
    id: int

class Settings(BaseModel):
    volume: Optional[int] = None
    speech_rate: Optional[float] = None
    patience_mode: Optional[int] = None
    sundowning_hour: Optional[int] = None
    medication_reminders_enabled: Optional[bool] = None
    word_of_day_enabled: Optional[bool] = None
    voice_gender: Optional[str] = None  # "male" or "female"
    voice_locale: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize companion and memory on startup."""
    global companion, memory
    try:
        logger.info("Initializing Loneliness Companion...")
        # Use absolute path for database (project root)
        db_path = project_root / Config.DB_PATH
        logger.info(f"Database path: {db_path}")
        memory = ConversationMemory(str(db_path))
        # Initialize companion (may fail if audio devices not available, that's OK for API)
        try:
            companion = LonelinessCompanion()
            logger.info("Companion initialized successfully")
        except Exception as e:
            logger.warning(f"Companion initialization warning (audio may not be available): {e}")
            # Create a minimal companion for API-only mode
            companion = None
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        memory = None
        companion = None

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global companion
    if companion:
        await companion.stop()

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# WebSocket test endpoint
@app.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    """Simple WebSocket test endpoint to verify WebSocket functionality."""
    origin = websocket.headers.get("origin", "")
    logger.info(f"Test WebSocket connection attempt from origin: {origin}")
    
    try:
        # Accept connection - no origin restrictions for development
        await websocket.accept()
        logger.info("Test WebSocket connection accepted")
        await websocket.send_json({"type": "connected", "message": "WebSocket test successful"})
        
        # Keep connection alive and echo messages
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "message": f"Echo: {data}"})
    except WebSocketDisconnect:
        logger.info("Test WebSocket disconnected")
    except Exception as e:
        logger.error(f"Test WebSocket error: {e}", exc_info=True)

# Test LLM endpoint
@app.post("/test/llm")
async def test_llm(request: Dict[str, Any]):
    """Test LLM integration."""
    try:
        message = request.get("message", "Hello, how are you?")
        
        from src.llm.response_generator import DynamicResponseGenerator
        from src.sentiment.analyzer import SentimentAnalyzer
        
        # Analyze sentiment
        analyzer = SentimentAnalyzer()
        sentiment_result = analyzer.analyze(message)
        
        # Generate response
        generator = DynamicResponseGenerator(api_provider="groq")
        response = await generator.generate_response(
            user_message=message,
            sentiment=sentiment_result["sentiment"],
            context="",
            state="idle"
        )
        
        return {
            "status": "success",
            "input": message,
            "sentiment": sentiment_result["sentiment"],
            "response": response,
            "provider": "groq"
        }
    except Exception as e:
        logger.error(f"LLM test error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Check GROQ_API_KEY in .env file"
        }

# Voice endpoints
@app.post("/voice/start")
async def start_voice_session():
    """Start a new voice session."""
    session_id = str(uuid.uuid4())
    _session_state(session_id)
    logger.info(f"Started voice session: {session_id}")
    return {"session_id": session_id}

@app.post("/voice/stop/{session_id}")
async def stop_voice_session(session_id: str):
    """Stop a voice session."""
    if session_id in active_sessions:
        del active_sessions[session_id]
        logger.info(f"Stopped voice session: {session_id}")
        return {"status": "stopped"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.post("/voice/message/{session_id}")
async def send_voice_message(session_id: str, audio: UploadFile = File(...)):
    """
    Complete voice processing pipeline:
    Audio Input → Deepgram ASR → Sentiment → Groq LLM → Murf TTS → Audio Output
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    
    try:
        audio_data = await audio.read()
        logger.info(f"[HTTP] /voice/message session={session_id} bytes={len(audio_data)} type={audio.content_type}")

        if not Config.DEEPGRAM_API_KEY:
            raise HTTPException(status_code=500, detail="Deepgram API key not configured. Add DEEPGRAM_API_KEY to .env file")

        settings = get_effective_settings()
        patience_mode = settings.get("patience_mode", DEFAULT_PATIENCE_MODE_MS)
        voice_locale = _normalize_locale(settings.get("voice_locale"))

        content_type = audio.content_type or "audio/webm;codecs=opus"
        try:
            logger.info(f"Deepgram input: {len(audio_data)} bytes (snippet hex: {audio_data[:64].hex()})")
        except Exception:
            logger.info(f"Deepgram input: {len(audio_data)} bytes")

        try:
            transcript = await transcribe_audio_with_deepgram(
                audio_data,
                Config.DEEPGRAM_API_KEY,
                content_type,
                patience_mode_ms=patience_mode,
                language=voice_locale,
            )
        except Exception as e:
            logger.warning(f"Deepgram transcription error: {e}", exc_info=True)
            transcript = ""

        if transcript:
            logger.info(f"Deepgram transcript: '{transcript}'")
        else:
            logger.info("Deepgram transcript: BLANK_OR_EMPTY")

        if not transcript:
            logger.info("[HTTP] No speech detected; returning empty response without TTS.")
            return {
                "transcript": "",
                "response": "",
                "sentiment": "neutral",
            }

        payload = await _build_response_for_transcript(
            transcript,
            session_id,
            trigger="http_fallback",
        )

        response_data = {
            "transcript": transcript,
            "response": payload["text"],
            "sentiment": payload["sentiment"],
        }
        logger.info(f"[HTTP] Transcribed {len(transcript)} chars -> response {len(payload['text'])} chars (session {session_id})")

        if payload.get("audio"):
            import base64
            response_data["response_audio"] = base64.b64encode(payload["audio"]).decode("utf-8")
            response_data["response_audio_format"] = "wav"

        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing voice: {str(e)}")

@app.get("/voice/status/{session_id}")
async def get_voice_status(session_id: str):
    """Get voice session status."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return active_sessions[session_id]

# Conversation endpoints
@app.get("/conversations")
async def get_conversations(limit: int = 10):
    """Get conversation history."""
    if not memory:
        return []
    
    conversations = memory.get_recent_conversations(limit=limit)
    return conversations

@app.post("/conversations")
async def save_conversation(conversation: ConversationMessage):
    """Save a conversation."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    
    memory.save_conversation(
        conversation.user_message,
        conversation.ai_response,
        sentiment=conversation.sentiment,
        topic=conversation.topic
    )
    return {"status": "saved"}

# Medication endpoints
@app.get("/medications")
async def get_medications():
    """Get all medications."""
    if not memory:
        return []
    
    try:
        import sqlite3
        conn = sqlite3.connect(Config.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, medication_name, time, last_reminded, last_taken
            FROM medication_schedule
            ORDER BY time
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        medications = []
        for row in rows:
            med = {
                "id": row["id"],
                "medication_name": row["medication_name"],
                "time": row["time"],
                "last_reminded": row["last_reminded"],
                "last_taken": row["last_taken"]
            }
            medications.append(med)
        
        logger.info(f"Retrieved {len(medications)} medications")
        return medications
    except Exception as e:
        logger.error(f"Error getting medications: {e}")
        return []

@app.post("/medications")
async def add_medication(medication: Medication):
    """Add a medication."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    
    try:
        memory.save_medication_schedule(medication.medication_name, medication.time)
        
        # Get the newly created medication ID
        import sqlite3
        conn = sqlite3.connect(Config.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, medication_name, time, last_reminded, last_taken
            FROM medication_schedule
            WHERE medication_name = ? AND time = ?
            ORDER BY id DESC
            LIMIT 1
        """, (medication.medication_name, medication.time))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = {
                "id": row["id"],
                "medication_name": row["medication_name"],
                "time": row["time"],
                "last_reminded": row["last_reminded"],
                "last_taken": row["last_taken"]
            }
            logger.info(f"Added medication: {medication.medication_name} at {medication.time}")
            return result
        else:
            return {
                "id": 0,
                "medication_name": medication.medication_name,
                "time": medication.time
            }
    except Exception as e:
        logger.error(f"Error adding medication: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add medication: {str(e)}")

@app.patch("/medications/{medication_id}")
async def update_medication(medication_id: int, medication: Dict[str, Any]):
    """Update a medication."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    
    try:
        import sqlite3
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if "medication_name" in medication:
            updates.append("medication_name = ?")
            values.append(medication["medication_name"])
        
        if "time" in medication:
            updates.append("time = ?")
            values.append(medication["time"])
        
        if "last_taken" in medication:
            updates.append("last_taken = ?")
            values.append(medication["last_taken"])
        
        if "last_reminded" in medication:
            updates.append("last_reminded = ?")
            values.append(medication["last_reminded"])
        
        if updates:
            values.append(medication_id)
            query = f"UPDATE medication_schedule SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
        
        logger.info(f"Updated medication {medication_id}")
        return {"status": "updated", "id": medication_id}
    except Exception as e:
        logger.error(f"Error updating medication: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update medication: {str(e)}")

@app.delete("/medications/{medication_id}")
async def delete_medication(medication_id: int):
    """Delete a medication."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    
    try:
        import sqlite3
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM medication_schedule WHERE id = ?", (medication_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted medication {medication_id}")
        return {"status": "deleted", "id": medication_id}
    except Exception as e:
        logger.error(f"Error deleting medication: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete medication: {str(e)}")

@app.get("/medications/due")
async def get_medications_due():
    """Get medications due now."""
    try:
        if companion and hasattr(companion, 'medication_reminder'):
            medications = companion.medication_reminder.check_medications_due()
        else:
            # Fallback: check directly from memory
            if not memory:
                return []
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M")
            medications = memory.get_medications_due(current_time)
        return medications
    except Exception as e:
        logger.error(f"Error getting due medications: {e}")
        return []

# Word of the day endpoint
@app.get("/word-of-day")
async def get_word_of_day():
    """Get word of the day - uses Groq to generate dynamic words."""
    try:
        import os
        
        # Check if Groq is available
        groq_key = os.getenv("GROQ_API_KEY", "")
        
        if not groq_key:
            raise HTTPException(
                status_code=500, 
                detail="GROQ_API_KEY not configured. Please add it to your .env file to generate words."
            )
        
        # Always use Groq - no fallback to static words
        from src.features.groq_word_generator import GroqWordGenerator
        generator = GroqWordGenerator(api_key=groq_key)
        word = await generator.generate_word()
        
        logger.info(f"Generated word of day with Groq: {word.get('word', 'unknown')}")
        return word
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating word of day with Groq: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate word with Groq: {str(e)}. Please check your GROQ_API_KEY."
        )

# WebSocket endpoint for real-time voice communication
@app.websocket("/ws/voice")
async def websocket_voice(websocket: WebSocket):
    """WebSocket endpoint for real-time voice communication."""
    # Note: CORS middleware doesn't apply to WebSockets, so we handle it manually
    origin = websocket.headers.get("origin", "")
    client_host = websocket.client.host if websocket.client else "unknown"
    
    logger.info(f"WebSocket connection attempt from origin: {origin}, client: {client_host}")
    
    # Accept connection - FastAPI WebSocket accepts all origins by default
    # We can add origin checking here if needed, but for development we accept all
    try:
        await websocket.accept()
        logger.info(f"WebSocket connection accepted from origin: {origin}")
    except Exception as e:
        logger.error(f"Failed to accept WebSocket connection: {e}", exc_info=True)
        # Try to close gracefully
        try:
            await websocket.close(code=1008, reason="Connection acceptance failed")
        except:
            pass
        return
    
    session_id = str(uuid.uuid4())
    session_state = _session_state(session_id)

    logger.info(f"WebSocket connection established: {session_id}")

    # Helper to safely send JSON over the websocket without raising when closed.
    async def safe_send_json(payload: Dict[str, Any]) -> bool:
        try:
            await websocket.send_json(payload)
            return True
        except Exception as e:
            logger.warning(f"WebSocket send failed (likely closed): {e}")
            return False

    async def send_status(state: str, detail: Optional[str] = None):
        payload: Dict[str, Any] = {"type": "status", "state": state}
        if detail:
            payload["detail"] = detail
        await safe_send_json(payload)

    processing_lock = asyncio.Lock()
    medication_stop_event = asyncio.Event()
    medication_task = asyncio.create_task(_medication_nudge_loop(session_id, safe_send_json, medication_stop_event))
    
    # Buffer to accumulate audio chunks per utterance
    audio_buffer: list[bytes] = []
    silence_task: Optional[asyncio.Task] = None
    await send_status("connected")
    
    async def process_complete_audio(complete_audio: bytes, trigger: str):
        if not complete_audio:
            return

        if not memory:
            await safe_send_json({
                "type": "error",
                "message": "Memory not initialized",
            })
            return

        if not Config.DEEPGRAM_API_KEY:
            await safe_send_json({
                "type": "error",
                "message": "Deepgram API key not configured",
            })
            return

        settings = get_effective_settings()
        patience_mode = settings.get("patience_mode", DEFAULT_PATIENCE_MODE_MS)
        voice_locale = _normalize_locale(settings.get("voice_locale"))

        async with processing_lock:
            await send_status("processing", trigger)
            try:
                transcript = await transcribe_audio_with_deepgram(
                    complete_audio,
                    Config.DEEPGRAM_API_KEY,
                    "audio/webm;codecs=opus",
                    patience_mode_ms=patience_mode,
                    language=voice_locale,
                )
            except Exception as e:
                logger.warning(f"Deepgram transcription error ({trigger}): {e}", exc_info=True)
                transcript = ""

            if not transcript:
                await safe_send_json({
                    "type": "transcript",
                    "text": "",
                    "status": "no_speech",
                })
                await send_status("listening", trigger)
                logger.info(f"[WebSocket] No speech detected for session {session_id} (trigger={trigger})")
                return

            await safe_send_json({
                "type": "transcript",
                "text": transcript,
                "status": "complete",
            })
            logger.info(f"[WebSocket] Transcript len={len(transcript)} chars (trigger={trigger}, session={session_id})")

            response_payload = await _build_response_for_transcript(
                transcript,
                session_id,
                trigger,
            )

            await safe_send_json({
                "type": "response",
                "text": response_payload["text"],
                "sentiment": response_payload["sentiment"],
            })

            if response_payload.get("audio"):
                import base64
                await send_status("ai_speaking", trigger)
                await safe_send_json({
                    "type": "audio",
                    "data": base64.b64encode(response_payload["audio"]).decode("utf-8"),
                    "format": "wav",
                    "text": response_payload["text"],  # Include text so frontend can update displayed response
                })

            await send_status("listening", trigger)

    try:
        while True:
            # Receive data from client
            data = await websocket.receive()
            
            if "bytes" in data:
                # Audio chunk received - accumulate it
                audio_chunk = data["bytes"]
                if audio_chunk:
                    audio_buffer.append(audio_chunk)
                    logger.info(f"Received audio chunk: {len(audio_chunk)} bytes (total: {sum(len(c) for c in audio_buffer)} bytes)")
                    # Reset / start silence timer
                    if silence_task and not silence_task.done():
                        silence_task.cancel()

                    async def on_silence():
                        await asyncio.sleep(0.8)  # 800ms of no audio = end of utterance
                        if not audio_buffer:
                            return
                        complete_audio = b"".join(audio_buffer)
                        audio_buffer.clear()
                        logger.info(f"Silence detected, processing utterance of {len(complete_audio)} bytes")

                        try:
                            saved = _save_and_convert_debug_audio(session_id, 'on_silence', complete_audio, ext_hint='webm')
                            logger.info(f"Saved received audio files: {saved}")
                        except Exception as e:
                            logger.warning(f"Failed to save/convert received audio: {e}")

                        await process_complete_audio(complete_audio, "on_silence")

                    silence_task = asyncio.create_task(on_silence())

            elif "text" in data:
                # JSON message received
                try:
                    import json
                    message = json.loads(data["text"])
                    logger.info(f"WebSocket JSON message received from client: {message.get('type')}")
                    
                    if message.get("type") == "ping":
                        if not await safe_send_json({"type": "pong"}):
                            return
                    elif message.get("type") == "end_of_utterance":
                        # Client signaled end of utterance (client-side VAD)
                        logger.info("Received end_of_utterance from client")
                        # Cancel server-side silence task if running
                        if silence_task and not silence_task.done():
                            try:
                                silence_task.cancel()
                            except Exception:
                                pass

                        if not audio_buffer:
                            if not await safe_send_json({
                                "type": "transcript",
                                "text": "",
                                "status": "no_speech"
                            }):
                                return
                            continue

                        # Concatenate all buffered chunks into a single complete audio blob
                        complete_audio = b"".join(audio_buffer)
                        audio_buffer.clear()
                        logger.info(f"Processing client-finalized utterance of {len(complete_audio)} bytes")

                        # Save received audio to disk for debugging/playback and try to convert to WAV
                        try:
                            saved = _save_and_convert_debug_audio(session_id, 'end_of_utterance', complete_audio, ext_hint='webm')
                            logger.info(f"Saved received audio files: {saved}")
                        except Exception as e:
                            logger.warning(f"Failed to save/convert received audio: {e}")

                        await process_complete_audio(complete_audio, "end_of_utterance")
                    elif message.get("type") == "close":
                        break
                        
                except json.JSONDecodeError:
                    await safe_send_json({
                        "type": "error",
                        "message": "Invalid JSON"
                    })
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except:
            pass
    finally:
        medication_stop_event.set()
        try:
            await medication_task
        except Exception:
            medication_task.cancel()
        if session_id in active_sessions:
            del active_sessions[session_id]
        logger.info(f"WebSocket session closed: {session_id}")

# Settings endpoints
@app.get("/settings")
async def get_settings():
    """Get current settings from database, initializing with defaults if empty."""
    # Hardcoded defaults (not from .env)
    default_settings = {
        "volume": 80,
        "speech_rate": 1.0,
        "patience_mode": DEFAULT_PATIENCE_MODE_MS,
        "sundowning_hour": DEFAULT_SUNDOWNING_HOUR,
        "medication_reminders_enabled": True,
        "word_of_day_enabled": True,
        "voice_gender": "female",
        "voice_locale": DEFAULT_VOICE_LOCALE,
    }
    
    if not memory:
        # Return defaults if memory not initialized
        return default_settings
    
    # Load settings from database
    saved_settings = memory.get_settings()
    
    # If database is empty (first run), initialize with defaults
    if not saved_settings:
        logger.info("Database settings empty - initializing with hardcoded defaults")
        memory.save_settings(default_settings)
        return default_settings
    
    # Update defaults with saved settings (database takes precedence)
    default_settings.update(saved_settings)
    
    return default_settings

@app.patch("/settings")
async def update_settings(settings: Settings):
    """Update settings and save to database. Only saves changed fields (partial update)."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    
    try:
        # Convert Pydantic model to dict, excluding None values
        settings_dict = settings.dict(exclude_none=True)
        
        logger.info(f"Received settings update request: {list(settings_dict.keys())}")
        logger.debug(f"Settings values: {settings_dict}")
        
        # Save only the changed fields (partial update) - this is faster and more efficient
        # The database will update only these keys, leaving others unchanged
        memory.save_settings(settings_dict)
        
        # Immediately reload from database to verify and return current state
        saved = memory.get_settings()
        logger.info(f"Settings saved successfully. Retrieved from DB: {list(saved.keys())}")
        logger.debug(f"All current settings: {saved}")
        
        return {"status": "updated", "settings": saved}
    except Exception as e:
        logger.error(f"Error updating settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("=" * 60)
    logger.info("Starting Loneliness Companion API server...")
    logger.info("Server will be available at: http://localhost:8000")
    logger.info("WebSocket endpoint: ws://localhost:8000/ws/voice")
    logger.info("Test WebSocket endpoint: ws://localhost:8000/ws/test")
    logger.info("API docs: http://localhost:8000/docs")
    logger.info("=" * 60)
    # Enable WebSocket support explicitly
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        ws="auto"  # Enable WebSocket support
    )


