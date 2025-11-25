"""Word of the Day cognitive exercise feature - uses Groq for dynamic generation."""
import asyncio
from typing import Dict, Optional
import logging
import os

logger = logging.getLogger(__name__)

class WordOfTheDay:
    """Word of the Day cognitive exercise using Groq for dynamic generation."""
    
    def __init__(self, dynamic_config=None):
        """
        Initialize Word of the Day feature.
        
        Args:
            dynamic_config: DynamicConfig instance (not used for Groq, kept for compatibility)
        """
        self.dynamic_config = dynamic_config
        self.current_word = None
        self.groq_generator = None
        self._init_groq()
    
    def _init_groq(self):
        """Initialize Groq word generator."""
        try:
            from .groq_word_generator import GroqWordGenerator
            groq_key = os.getenv("GROQ_API_KEY", "")
            if groq_key:
                self.groq_generator = GroqWordGenerator(api_key=groq_key)
                logger.info("Initialized Groq word generator")
            else:
                logger.warning("GROQ_API_KEY not found, word generation will fail")
        except Exception as e:
            logger.error(f"Failed to initialize Groq generator: {e}")
    
    async def get_word_of_day_async(self) -> Dict:
        """
        Get a word of the day using Groq (async).
        
        Returns:
            Dictionary with word, definition, and prompts
        """
        if not self.groq_generator:
            raise ValueError("Groq word generator not initialized. Please set GROQ_API_KEY in .env")
        
        word = await self.groq_generator.generate_word()
        self.current_word = word
        logger.info(f"Generated word of the day: {word.get('word', 'unknown')}")
        return word
    
    def get_word_of_day(self) -> Dict:
        """
        Get a word of the day using Groq (synchronous wrapper).
        
        Returns:
            Dictionary with word, definition, and prompts
        """
        if not self.groq_generator:
            raise ValueError("Groq word generator not initialized. Please set GROQ_API_KEY in .env")
        
        # Run async method in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_word_of_day_async())
    
    def generate_introduction(self) -> str:
        """
        Generate introduction message for word of the day.
        
        Returns:
            Introduction message
        """
        if not self.current_word:
            # Try to get word synchronously (for compatibility)
            try:
                self.get_word_of_day()
            except Exception as e:
                logger.error(f"Error getting word: {e}")
                return "I'd love to share a word with you, but I'm having trouble generating one right now."
        
        word = self.current_word.get("word", "word")
        definition = self.current_word.get("definition", "an interesting concept")
        prompt = self.current_word.get("prompt", "What do you think about that?")
        
        return f"I learned a new word today: '{word}'. It means {definition}. {prompt}"
    
    async def generate_introduction_async(self) -> str:
        """
        Generate introduction message for word of the day (async version).
        
        Returns:
            Introduction message
        """
        if not self.current_word:
            # Get word asynchronously
            try:
                await self.get_word_of_day_async()
            except Exception as e:
                logger.error(f"Error getting word: {e}")
                return "I'd love to share a word with you, but I'm having trouble generating one right now."
        
        word = self.current_word.get("word", "word")
        definition = self.current_word.get("definition", "an interesting concept")
        prompt = self.current_word.get("prompt", "What do you think about that?")
        
        return f"I learned a new word today: '{word}'. It means {definition}. {prompt}"
    
    def generate_follow_up(self, user_response: str) -> str:
        """
        Generate follow-up based on user response.
        
        Args:
            user_response: User's response to the word prompt
            
        Returns:
            Follow-up message
        """
        if not self.current_word:
            return "That's interesting! Tell me more."
        
        # Check if user gave a positive response
        response_lower = user_response.lower()
        follow_up = self.current_word.get("follow_up", "That's wonderful! Tell me more.")
        
        if any(word in response_lower for word in ["yes", "love", "like", "enjoy"]):
            return follow_up
        elif any(word in response_lower for word in ["no", "don't", "not"]):
            return "That's okay, we all have different preferences. What do you enjoy instead?"
        else:
            # User shared a story or longer response
            return follow_up or "That's a wonderful story. Thank you for sharing that with me."

