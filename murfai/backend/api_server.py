"""FastAPI backend server for Loneliness Companion frontend."""
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
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

def get_effective_settings() -> Dict[str, Any]:
    """
    Get effective settings from database, falling back to Config defaults.
    This ensures database settings are used when available.
    """
    default_settings = {
        "volume": 80,
        "speech_rate": 1.0,
        "patience_mode": Config.PATIENCE_MODE_SILENCE_MS,
        "sundowning_hour": Config.SUNDOWNING_HOUR,
        "medication_reminders_enabled": True,
        "word_of_day_enabled": True,
        "voice_gender": "female",  # Default to female voice
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
    active_sessions[session_id] = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "is_listening": False,
        "is_speaking": False,
    }
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
        # Step 1: Read audio file
        audio_data = await audio.read()
        logger.info(f"Received audio: {len(audio_data)} bytes")
        
        # Step 2: Transcribe audio with Deepgram ASR
        from src.utils.audio_processor import transcribe_audio_with_deepgram
        from src.config import Config
        
        if not Config.DEEPGRAM_API_KEY:
            raise HTTPException(status_code=500, detail="Deepgram API key not configured. Add DEEPGRAM_API_KEY to .env file")
        
        # Get effective settings from database
        settings = get_effective_settings()
        patience_mode = settings.get("patience_mode", Config.PATIENCE_MODE_SILENCE_MS)
        
        # Detect audio format from content type or default to webm
        content_type = audio.content_type or "audio/webm"
        # Log what we're sending to Deepgram (size + snippet) and handle transcription errors gracefully
        try:
            logger.info(f"Deepgram input: {len(audio_data)} bytes (snippet hex: {audio_data[:64].hex()})")
        except Exception:
            logger.info(f"Deepgram input: {len(audio_data)} bytes")

        try:
            transcript = await transcribe_audio_with_deepgram(
                audio_data,
                Config.DEEPGRAM_API_KEY,
                content_type,
                patience_mode_ms=patience_mode
            )
        except Exception as e:
            logger.warning(f"Deepgram transcription error: {e}", exc_info=True)
            transcript = ""

        if transcript:
            logger.info(f"Deepgram transcript: '{transcript}'")
        else:
            logger.info("Deepgram transcript: BLANK_OR_EMPTY")

        if not transcript:
            raise HTTPException(status_code=400, detail="No speech detected in audio")
        
        # Step 3: Analyze sentiment
        if companion and hasattr(companion, 'sentiment_analyzer'):
            sentiment_result = companion.sentiment_analyzer.analyze(transcript)
        else:
            from src.sentiment.analyzer import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            sentiment_result = analyzer.analyze(transcript)
        
        # Step 4: Get conversation context
        context = memory.get_conversation_context(limit=3)
        
        # Step 5: Generate response with Groq LLM
        try:
            if companion and hasattr(companion, '_generate_response'):
                logger.info("Using companion's response generator")
                response_text = await companion._generate_response(
                    transcript,
                    sentiment_result["sentiment"],
                    context
                )
            else:
                logger.info("Using standalone response generator with Groq")
                from src.llm.response_generator import DynamicResponseGenerator
                import os
                llm_provider = os.getenv("LLM_PROVIDER", "groq")
                generator = DynamicResponseGenerator(api_provider=llm_provider)
                response_text = await generator.generate_response(
                    transcript,
                    sentiment_result["sentiment"],
                    context,
                    state="idle"
                )
            
            if not response_text or response_text.strip() == "":
                raise Exception("LLM returned empty response")
            
            logger.info(f"Generated response: {response_text[:100]}...")
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")
        
        # Step 6: Synthesize speech with Murf TTS
        from src.utils.audio_processor import synthesize_speech_with_murf
        from src.config import Config
        
        if not Config.MURF_API_KEY:
            raise HTTPException(status_code=500, detail="Murf API key not configured. Add MURF_API_KEY to .env file")
        
        try:
            # Get effective settings from database for TTS
            settings = get_effective_settings()
            speech_rate = settings.get("speech_rate", 1.0)
            sundowning_hour = settings.get("sundowning_hour", Config.SUNDOWNING_HOUR)
            voice_gender = settings.get("voice_gender", "female")
            
            response_audio = await synthesize_speech_with_murf(
                response_text,
                sentiment=sentiment_result["sentiment"],
                api_key=Config.MURF_API_KEY,
                api_url=Config.MURF_API_URL,
                speech_rate=speech_rate,
                sundowning_hour=sundowning_hour,
                voice_gender=voice_gender
            )
            logger.info(f"Generated audio: {len(response_audio)} bytes")
        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")
        
        # Step 7: Save conversation
        memory.save_conversation(
            transcript,
            response_text,
            sentiment=sentiment_result["sentiment"]
        )
        
        # Step 8: Update session
        active_sessions[session_id]["is_listening"] = False
        
        # Step 9: Return response
        from fastapi.responses import Response
        
        response_data = {
            "transcript": transcript,
            "response": response_text,
            "sentiment": sentiment_result["sentiment"]
        }
        
        # If we have audio, return it as base64 or provide download URL
        if response_audio:
            import base64
            audio_base64 = base64.b64encode(response_audio).decode('utf-8')
            response_data["response_audio"] = audio_base64
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
    active_sessions[session_id] = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "is_listening": False,
        "is_speaking": False,
    }
    
    logger.info(f"WebSocket connection established: {session_id}")

    # Helper to safely send JSON over the websocket without raising when closed.
    async def safe_send_json(payload: Dict[str, Any]) -> bool:
        try:
            await websocket.send_json(payload)
            return True
        except Exception as e:
            logger.warning(f"WebSocket send failed (likely closed): {e}")
            return False
    
    # Buffer to accumulate audio chunks per utterance
    audio_buffer: list[bytes] = []
    silence_task: Optional[asyncio.Task] = None
    
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

                        # Save received audio to disk for debugging/playback and try to convert to WAV
                        try:
                            saved = _save_and_convert_debug_audio(session_id, 'on_silence', complete_audio, ext_hint='webm')
                            logger.info(f"Saved received audio files: {saved}")
                        except Exception as e:
                            logger.warning(f"Failed to save/convert received audio: {e}")

                        if not memory:
                            await safe_send_json({
                                "type": "error",
                                "message": "Memory not initialized"
                            })
                            return

                        try:
                            # Step 1: Transcribe audio with Deepgram ASR
                            from src.utils.audio_processor import transcribe_audio_with_deepgram
                            from src.config import Config

                            if not Config.DEEPGRAM_API_KEY:
                                await safe_send_json({
                                    "type": "error",
                                    "message": "Deepgram API key not configured"
                                })
                                return

                            settings = get_effective_settings()
                            patience_mode = settings.get("patience_mode", Config.PATIENCE_MODE_SILENCE_MS)

                            # Log what we are about to send to Deepgram and handle errors
                            try:
                                logger.info(f"Deepgram input (on_silence): {len(complete_audio)} bytes (snippet hex: {complete_audio[:64].hex()})")
                            except Exception:
                                logger.info(f"Deepgram input (on_silence): {len(complete_audio)} bytes")

                            try:
                                transcript = await transcribe_audio_with_deepgram(
                                    complete_audio,
                                    Config.DEEPGRAM_API_KEY,
                                    "audio/webm",
                                    patience_mode_ms=patience_mode
                                )
                            except Exception as e:
                                logger.warning(f"Deepgram transcription error (on_silence): {e}", exc_info=True)
                                transcript = ""

                            if not transcript:
                                logger.info("Deepgram transcript (on_silence): BLANK_OR_EMPTY")
                                # Inform client that no speech was detected
                                if not await safe_send_json({
                                    "type": "transcript",
                                    "text": "",
                                    "status": "no_speech"
                                }):
                                    return

                                # Fallback: generate a polite prompt and synthesize TTS so client changes to speaking
                                try:
                                    fallback_text = "I didn't catch that — could you please repeat?"
                                    logger.info(f"Generating fallback TTS: {fallback_text}")
                                    from src.utils.audio_processor import synthesize_speech_with_murf
                                    settings = get_effective_settings()
                                    speech_rate = settings.get("speech_rate", 1.0)
                                    sundowning_hour = settings.get("sundowning_hour", Config.SUNDOWNING_HOUR)
                                    voice_gender = settings.get("voice_gender", "female")

                                    response_audio = await synthesize_speech_with_murf(
                                        fallback_text,
                                        sentiment="neutral",
                                        api_key=Config.MURF_API_KEY,
                                        api_url=Config.MURF_API_URL,
                                        speech_rate=speech_rate,
                                        sundowning_hour=sundowning_hour,
                                        voice_gender=voice_gender
                                    )

                                    import base64
                                    audio_base64 = base64.b64encode(response_audio).decode('utf-8')

                                    if not await safe_send_json({
                                        "type": "response",
                                        "text": fallback_text,
                                        "sentiment": "neutral"
                                    }):
                                        return

                                    if not await safe_send_json({
                                        "type": "audio",
                                        "data": audio_base64,
                                        "format": "wav"
                                    }):
                                        return
                                except Exception as e:
                                    logger.error(f"Fallback TTS error (on_silence): {e}", exc_info=True)
                                return

                            logger.info(f"Deepgram transcript (on_silence): '{transcript}'")

                            # Send transcript immediately
                            if not await safe_send_json({
                                "type": "transcript",
                                "text": transcript,
                                "status": "complete"
                            }):
                                return

                            # Step 2: Analyze sentiment
                            if companion and hasattr(companion, 'sentiment_analyzer'):
                                sentiment_result = companion.sentiment_analyzer.analyze(transcript)
                            else:
                                from src.sentiment.analyzer import SentimentAnalyzer
                                analyzer = SentimentAnalyzer()
                                sentiment_result = analyzer.analyze(transcript)

                            # Step 3: Get conversation context
                            context = memory.get_conversation_context(limit=3)

                            # Step 4: Generate response with Groq LLM
                            try:
                                if companion and hasattr(companion, '_generate_response'):
                                    response_text = await companion._generate_response(
                                        transcript,
                                        sentiment_result["sentiment"],
                                        context
                                    )
                                else:
                                    from src.llm.response_generator import DynamicResponseGenerator
                                    import os
                                    llm_provider = os.getenv("LLM_PROVIDER", "groq")
                                    generator = DynamicResponseGenerator(api_provider=llm_provider)
                                    response_text = await generator.generate_response(
                                        transcript,
                                        sentiment_result["sentiment"],
                                        context,
                                        state="idle"
                                    )

                                if not response_text or response_text.strip() == "":
                                    raise Exception("LLM returned empty response")

                            except Exception as e:
                                logger.error(f"Error generating LLM response: {e}", exc_info=True)
                                await safe_send_json({
                                    "type": "error",
                                    "message": f"Failed to generate response: {str(e)}"
                                })
                                return

                            # Send response text
                            if not await safe_send_json({
                                "type": "response",
                                "text": response_text,
                                "sentiment": sentiment_result["sentiment"]
                            }):
                                return

                            # Step 5: Synthesize speech with Murf TTS
                            if Config.MURF_API_KEY:
                                try:
                                    from src.utils.audio_processor import synthesize_speech_with_murf

                                    settings = get_effective_settings()
                                    speech_rate = settings.get("speech_rate", 1.0)
                                    sundowning_hour = settings.get("sundowning_hour", Config.SUNDOWNING_HOUR)
                                    voice_gender = settings.get("voice_gender", "female")

                                    response_audio = await synthesize_speech_with_murf(
                                        response_text,
                                        sentiment=sentiment_result["sentiment"],
                                        api_key=Config.MURF_API_KEY,
                                        api_url=Config.MURF_API_URL,
                                        speech_rate=speech_rate,
                                        sundowning_hour=sundowning_hour,
                                        voice_gender=voice_gender
                                    )

                                    # Send audio as base64
                                    import base64
                                    audio_base64 = base64.b64encode(response_audio).decode('utf-8')

                                    if not await safe_send_json({
                                        "type": "audio",
                                        "data": audio_base64,
                                        "format": "wav"
                                    }):
                                        return

                                except Exception as e:
                                    logger.error(f"TTS error: {e}", exc_info=True)
                                    await safe_send_json({
                                        "type": "error",
                                        "message": f"TTS error: {str(e)}"
                                    })

                            # Step 6: Save conversation
                            memory.save_conversation(
                                transcript,
                                response_text,
                                sentiment=sentiment_result["sentiment"]
                            )

                        except Exception as e:
                            logger.error(f"Error processing voice message: {e}", exc_info=True)
                            await safe_send_json({
                                "type": "error",
                                "message": str(e)
                            })

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

                        try:
                            # Step 1: Transcribe audio with Deepgram ASR
                            from src.utils.audio_processor import transcribe_audio_with_deepgram
                            from src.config import Config

                            if not Config.DEEPGRAM_API_KEY:
                                await safe_send_json({
                                    "type": "error",
                                    "message": "Deepgram API key not configured"
                                })
                                continue

                            settings = get_effective_settings()
                            patience_mode = settings.get("patience_mode", Config.PATIENCE_MODE_SILENCE_MS)

                            # Log what we are about to send to Deepgram and handle errors
                            try:
                                logger.info(f"Deepgram input (end_of_utterance): {len(complete_audio)} bytes (snippet hex: {complete_audio[:64].hex()})")
                            except Exception:
                                logger.info(f"Deepgram input (end_of_utterance): {len(complete_audio)} bytes")

                            try:
                                # Send full concatenated audio to Deepgram; hint codec for webm/opus
                                transcript = await transcribe_audio_with_deepgram(
                                    complete_audio,
                                    Config.DEEPGRAM_API_KEY,
                                    "audio/webm;codecs=opus",
                                    patience_mode_ms=patience_mode
                                )
                            except Exception as e:
                                logger.warning(f"Deepgram transcription error (end_of_utterance): {e}", exc_info=True)
                                transcript = ""

                            if not transcript:
                                logger.info("Deepgram transcript (end_of_utterance): BLANK_OR_EMPTY")
                                # Notify client
                                if not await safe_send_json({
                                    "type": "transcript",
                                    "text": "",
                                    "status": "no_speech"
                                }):
                                    return

                                # Fallback: synthesize a polite prompt so the companion speaks
                                try:
                                    fallback_text = "I didn't catch that — could you please repeat?"
                                    logger.info(f"Generating fallback TTS (end_of_utterance): {fallback_text}")
                                    from src.utils.audio_processor import synthesize_speech_with_murf
                                    settings = get_effective_settings()
                                    speech_rate = settings.get("speech_rate", 1.0)
                                    sundowning_hour = settings.get("sundowning_hour", Config.SUNDOWNING_HOUR)
                                    voice_gender = settings.get("voice_gender", "female")

                                    response_audio = await synthesize_speech_with_murf(
                                        fallback_text,
                                        sentiment="neutral",
                                        api_key=Config.MURF_API_KEY,
                                        api_url=Config.MURF_API_URL,
                                        speech_rate=speech_rate,
                                        sundowning_hour=sundowning_hour,
                                        voice_gender=voice_gender
                                    )

                                    import base64
                                    audio_base64 = base64.b64encode(response_audio).decode('utf-8')

                                    if not await safe_send_json({
                                        "type": "response",
                                        "text": fallback_text,
                                        "sentiment": "neutral"
                                    }):
                                        return

                                    if not await safe_send_json({
                                        "type": "audio",
                                        "data": audio_base64,
                                        "format": "wav"
                                    }):
                                        return
                                except Exception as e:
                                    logger.error(f"Fallback TTS error (end_of_utterance): {e}", exc_info=True)
                                continue

                            logger.info(f"Deepgram transcript (end_of_utterance): '{transcript}'")

                            # Send transcript immediately
                            if not await safe_send_json({
                                "type": "transcript",
                                "text": transcript,
                                "status": "complete"
                            }):
                                return

                            # Step 2: Analyze sentiment
                            if companion and hasattr(companion, 'sentiment_analyzer'):
                                sentiment_result = companion.sentiment_analyzer.analyze(transcript)
                            else:
                                from src.sentiment.analyzer import SentimentAnalyzer
                                analyzer = SentimentAnalyzer()
                                sentiment_result = analyzer.analyze(transcript)

                            # Step 3: Get conversation context
                            context = memory.get_conversation_context(limit=3)

                            # Step 4: Generate response with Groq LLM
                            try:
                                if companion and hasattr(companion, '_generate_response'):
                                    response_text = await companion._generate_response(
                                        transcript,
                                        sentiment_result["sentiment"],
                                        context
                                    )
                                else:
                                    from src.llm.response_generator import DynamicResponseGenerator
                                    import os
                                    llm_provider = os.getenv("LLM_PROVIDER", "groq")
                                    generator = DynamicResponseGenerator(api_provider=llm_provider)
                                    response_text = await generator.generate_response(
                                        transcript,
                                        sentiment_result["sentiment"],
                                        context,
                                        state="idle"
                                    )

                                if not response_text or response_text.strip() == "":
                                    raise Exception("LLM returned empty response")

                            except Exception as e:
                                logger.error(f"Error generating LLM response: {e}", exc_info=True)
                                await safe_send_json({
                                    "type": "error",
                                    "message": f"Failed to generate response: {str(e)}"
                                })
                                continue

                            # Send response text
                            if not await safe_send_json({
                                "type": "response",
                                "text": response_text,
                                "sentiment": sentiment_result["sentiment"]
                            }):
                                return

                            # Step 5: Synthesize speech with Murf TTS
                            if Config.MURF_API_KEY:
                                try:
                                    from src.utils.audio_processor import synthesize_speech_with_murf

                                    settings = get_effective_settings()
                                    speech_rate = settings.get("speech_rate", 1.0)
                                    sundowning_hour = settings.get("sundowning_hour", Config.SUNDOWNING_HOUR)
                                    voice_gender = settings.get("voice_gender", "female")

                                    response_audio = await synthesize_speech_with_murf(
                                        response_text,
                                        sentiment=sentiment_result["sentiment"],
                                        api_key=Config.MURF_API_KEY,
                                        api_url=Config.MURF_API_URL,
                                        speech_rate=speech_rate,
                                        sundowning_hour=sundowning_hour,
                                        voice_gender=voice_gender
                                    )

                                    # Send audio as base64
                                    import base64
                                    audio_base64 = base64.b64encode(response_audio).decode('utf-8')

                                    if not await safe_send_json({
                                        "type": "audio",
                                        "data": audio_base64,
                                        "format": "wav"
                                    }):
                                        return

                                except Exception as e:
                                    logger.error(f"TTS error: {e}", exc_info=True)
                                    await safe_send_json({
                                        "type": "error",
                                        "message": f"TTS error: {str(e)}"
                                    })

                            # Step 6: Save conversation
                            memory.save_conversation(
                                transcript,
                                response_text,
                                sentiment=sentiment_result["sentiment"]
                            )

                        except Exception as e:
                            logger.error(f"Error processing voice message: {e}", exc_info=True)
                            await safe_send_json({
                                "type": "error",
                                "message": str(e)
                            })
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
        if session_id in active_sessions:
            del active_sessions[session_id]
        logger.info(f"WebSocket session closed: {session_id}")

# Settings endpoints
@app.get("/settings")
async def get_settings():
    """Get current settings from database or return defaults."""
    if not memory:
        # Return defaults if memory not initialized
        return {
            "volume": 80,
            "speech_rate": 1.0,
            "patience_mode": Config.PATIENCE_MODE_SILENCE_MS,
            "sundowning_hour": Config.SUNDOWNING_HOUR,
            "medication_reminders_enabled": True,
            "word_of_day_enabled": True,
            "voice_gender": "female",
        }
    
    # Load settings from database
    saved_settings = memory.get_settings()
    
    # Merge with defaults (saved settings take precedence)
    default_settings = {
        "volume": 80,
        "speech_rate": 1.0,
        "patience_mode": Config.PATIENCE_MODE_SILENCE_MS,
        "sundowning_hour": Config.SUNDOWNING_HOUR,
        "medication_reminders_enabled": True,
        "word_of_day_enabled": True,
        "voice_gender": "female",
    }
    
    # Update defaults with saved settings
    default_settings.update(saved_settings)
    
    return default_settings

@app.patch("/settings")
async def update_settings(settings: Settings):
    """Update settings and save to database."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")
    
    try:
        # Convert Pydantic model to dict, excluding None values
        settings_dict = settings.dict(exclude_none=True)
        
        logger.info(f"Received settings update request: {list(settings_dict.keys())}")
        logger.debug(f"Settings values: {settings_dict}")
        
        # Save to database
        memory.save_settings(settings_dict)
        
        # Verify it was saved by reading it back
        saved = memory.get_settings()
        logger.info(f"Settings saved successfully. Retrieved from DB: {list(saved.keys())}")
        
        return {"status": "updated", "settings": settings_dict}
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


