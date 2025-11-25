"""Main companion agent orchestrator with dynamic response generation."""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from ..asr.deepgram_client import DeepgramASRClient
from ..asr.audio_capture import AudioCapture
from ..tts.murf_client import MurfTTSClient
from ..sentiment.analyzer import SentimentAnalyzer
from ..memory.conversation_db import ConversationMemory
from ..features.medication_reminder import MedicationReminder
from ..features.word_of_day import WordOfTheDay
from ..utils.audio_player import AudioPlayer
from ..llm.response_generator import DynamicResponseGenerator
from ..config.dynamic_config import DynamicConfig
from ..config import Config

logger = logging.getLogger(__name__)

class LonelinessCompanion:
    """Main companion agent for elderly care with dynamic response generation."""
    
    def __init__(self):
        """Initialize the companion."""
        # Initialize dynamic configuration
        self.dynamic_config = DynamicConfig()
        
        # Initialize components
        self.memory = ConversationMemory(Config.DB_PATH)
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Initialize with dynamic config
        self.medication_reminder = MedicationReminder(self.memory, self.dynamic_config)
        self.word_of_day = WordOfTheDay(self.dynamic_config)
        
        # Initialize dynamic response generator
        llm_provider = self.dynamic_config.get("llm.provider", "huggingface")
        llm_config = {
            "llm": {
                "provider": llm_provider,
                "api_key": self.dynamic_config.get("llm.api_key", ""),
                "model": self.dynamic_config.get("llm.model", ""),
            }
        }
        self.response_generator = DynamicResponseGenerator(api_provider=llm_provider, config=llm_config)
        
        self.audio_capture = AudioCapture()
        self.audio_player = AudioPlayer()
        
        # Initialize ASR and TTS clients
        self.asr_client = DeepgramASRClient(
            Config.DEEPGRAM_API_KEY,
            self._on_transcript_received
        )
        self.tts_client = MurfTTSClient(
            Config.MURF_API_KEY,
            Config.MURF_API_URL
        )
        
        self.is_running = False
        self.current_conversation_state = "idle"
        self.last_user_message = None
    
    async def _on_transcript_received(self, transcript: str):
        """
        Handle received transcript from ASR.
        
        Args:
            transcript: Transcribed user speech
        """
        logger.info(f"User said: {transcript}")
        self.last_user_message = transcript
        
        # Process the message
        await self._process_user_message(transcript)
    
    async def _process_user_message(self, message: str):
        """
        Process user message and generate response.
        
        Args:
            message: User's message
        """
        # Analyze sentiment
        sentiment_result = self.sentiment_analyzer.analyze(message)
        sentiment = sentiment_result["sentiment"]
        
        # Get conversation context
        context = self.memory.get_conversation_context(limit=3)
        
        # Generate response based on context
        response = await self._generate_response(message, sentiment, context)
        
        # Save conversation
        self.memory.save_conversation(
            message,
            response,
            sentiment=sentiment
        )
        
        # Synthesize and play response
        await self._speak(response, sentiment)
    
    async def _generate_response(
        self,
        user_message: str,
        sentiment: str,
        context: str
    ) -> str:
        """
        Generate AI response dynamically using LLM or rule-based system.
        
        Args:
            user_message: User's message
            sentiment: Detected sentiment
            context: Conversation history context
            
        Returns:
            AI response text
        """
        # Prepare additional context for special states
        additional_context = {}
        
        # Handle medication-related responses
        if self.current_conversation_state == "medication_reminder":
            medications = self.medication_reminder.check_medications_due()
            if medications:
                additional_context["medication"] = medications[0]['medication_name']
                # Use medication reminder handler for structured responses
                return self.medication_reminder.handle_medication_response(
                    user_message,
                    medications[0]
                )
        
        # Handle word of the day responses
        if self.current_conversation_state == "word_of_day":
            if self.word_of_day.current_word:
                additional_context["word_of_day"] = self.word_of_day.current_word
                # Use word of day handler for structured responses
                return self.word_of_day.generate_follow_up(user_message)
        
        # Use dynamic LLM-based response generator
        try:
            response = await self.response_generator.generate_response(
                user_message=user_message,
                sentiment=sentiment,
                context=context,
                state=self.current_conversation_state,
                additional_context=additional_context if additional_context else None
            )
            return response
        except Exception as e:
            logger.error(f"Error generating dynamic response: {e}")
            # Fallback to simple response
            return "I'm here to listen. Can you tell me more about that?"
    
    async def _speak(self, text: str, sentiment: str = "neutral"):
        """
        Synthesize and play speech.
        
        Args:
            text: Text to speak
            sentiment: Sentiment for voice styling
        """
        try:
            # Synthesize speech
            audio_data = await self.tts_client.synthesize(text, sentiment=sentiment)
            
            # Play audio
            self.audio_player.play_bytes(audio_data)
            
        except Exception as e:
            logger.error(f"Error speaking: {e}")
            # Fallback: print text (no TTS fallback as per requirements)
            print(f"[AI]: {text}")
    
    async def _check_medications(self):
        """Periodically check for medications due."""
        while self.is_running:
            try:
                medications = self.medication_reminder.check_medications_due()
                
                if medications:
                    for medication in medications:
                        reminder_msg = self.medication_reminder.generate_reminder_message(medication)
                        self.current_conversation_state = "medication_reminder"
                        
                        # Analyze sentiment for reminder (usually neutral)
                        await self._speak(reminder_msg, sentiment="neutral")
                        
                        # Mark as reminded
                        self.medication_reminder.memory.mark_medication_reminded(medication['id'])
                
                # Check every minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error checking medications: {e}")
                await asyncio.sleep(60)
    
    async def _introduce_word_of_day(self):
        """Periodically introduce word of the day using Groq."""
        while self.is_running:
            try:
                # Introduce word of the day once per day (check every hour)
                await asyncio.sleep(3600)  # 1 hour
                
                # Only introduce if conversation is idle
                if self.current_conversation_state == "idle":
                    try:
                        # Get word from Groq
                        word = await self.word_of_day.get_word_of_day_async()
                        word_intro = self.word_of_day.generate_introduction()
                        self.current_conversation_state = "word_of_day"
                        await self._speak(word_intro, sentiment="happy")
                    except Exception as e:
                        logger.error(f"Error generating word of day: {e}")
                        # Skip this cycle if Groq fails
                
            except Exception as e:
                logger.error(f"Error introducing word of day: {e}")
    
    async def start(self):
        """Start the companion agent."""
        logger.info("Starting Loneliness Companion...")
        self.is_running = True
        
        try:
            # Connect to ASR
            await self.asr_client.connect()
            
            # Start background tasks
            medication_task = asyncio.create_task(self._check_medications())
            word_task = asyncio.create_task(self._introduce_word_of_day())
            
            # Initial greeting (dynamic)
            greeting = await self.response_generator.generate_response(
                user_message="Hello",
                sentiment="neutral",
                context="",
                state="idle"
            ) or "Hello! I'm your companion. I'm here to listen and chat with you. How are you doing today?"
            await self._speak(greeting, sentiment="neutral")
            
            # Start listening
            await self.asr_client.start_listening(self.audio_capture.audio_generator())
            
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Error in companion: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the companion agent."""
        logger.info("Stopping Loneliness Companion...")
        self.is_running = False
        
        # Stop ASR
        await self.asr_client.stop_listening()
        
        # Cleanup
        self.audio_capture.cleanup()
        self.audio_player.cleanup()
        await self.tts_client.close()
        
        logger.info("Companion stopped")

