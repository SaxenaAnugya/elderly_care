"""FastAPI backend server for Loneliness Companion frontend."""
import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

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

@app.on_event("startup")
async def startup_event():
    """Initialize companion and memory on startup."""
    global companion, memory
    try:
        logger.info("Initializing Loneliness Companion...")
        memory = ConversationMemory(Config.DB_PATH)
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
        
        # Detect audio format from content type or default to webm
        content_type = audio.content_type or "audio/webm"
        transcript = await transcribe_audio_with_deepgram(audio_data, Config.DEEPGRAM_API_KEY, content_type)
        logger.info(f"Transcript: {transcript}")
        
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
            # Fallback response
            response_text = f"I heard you say '{transcript}'. I'm here to listen and help. Can you tell me more?"
            logger.warning(f"Using fallback response: {response_text}")
        
        # Step 6: Synthesize speech with Murf TTS
        from src.utils.audio_processor import synthesize_speech_with_murf
        from src.config import Config
        
        if not Config.MURF_API_KEY:
            logger.warning("Murf API key not configured, returning text only")
            response_audio = None
        else:
            try:
                response_audio = await synthesize_speech_with_murf(
                    response_text,
                    sentiment=sentiment_result["sentiment"],
                    api_key=Config.MURF_API_KEY,
                    api_url=Config.MURF_API_URL
                )
                logger.info(f"Generated audio: {len(response_audio)} bytes")
            except Exception as e:
                logger.error(f"TTS error: {e}, returning text only")
                response_audio = None
        
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

# Settings endpoints
@app.get("/settings")
async def get_settings():
    """Get current settings."""
    # Return default settings or from config
    return {
        "volume": 80,
        "speech_rate": 1.0,
        "patience_mode": Config.PATIENCE_MODE_SILENCE_MS,
        "sundowning_hour": Config.SUNDOWNING_HOUR,
        "medication_reminders_enabled": True,
        "word_of_day_enabled": True,
    }

@app.patch("/settings")
async def update_settings(settings: Settings):
    """Update settings."""
    # In production, save to database or config file
    return {"status": "updated", "settings": settings.dict(exclude_none=True)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

