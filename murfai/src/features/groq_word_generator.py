"""Groq-based dynamic word of the day generator."""
import aiohttp
import json
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class GroqWordGenerator:
    """Generate words of the day using Groq LLM."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq word generator.
        
        Args:
            api_key: Groq API key (uses env var if not provided)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self):
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def generate_word(self) -> Dict:
        """
        Generate a word of the day using Groq.
        
        Returns:
            Dictionary with word, definition, prompt, and follow_up
        """
        if not self.api_key:
            raise ValueError("Groq API key not configured")
        
        try:
            session = await self._get_session()
            
            # System prompt for word generation
            system_prompt = """You are a helpful assistant that generates interesting words of the day for elderly users. 
Generate words that are:
- Not too complex or obscure (avoid very technical terms)
- Have positive, neutral, or uplifting meanings
- Are engaging and conversation-starting
- Appropriate for cognitive exercises and memory stimulation
- Words that seniors can relate to and discuss

Examples of good words: Serendipity, Gratitude, Resilience, Harmony, Nostalgia, Wisdom, Comfort, Joy, Peace, Hope, Kindness, Patience

Always return ONLY a valid JSON object with these exact fields:
{
  "word": "the word",
  "definition": "simple, clear definition in plain language",
  "prompt": "engaging, warm question to start conversation",
  "follow_up": "warm, empathetic follow-up response"
}

Do not include any text before or after the JSON. Return only the JSON object."""
            
            user_prompt = "Generate a new, unique word of the day for an elderly user. Make it interesting but not too difficult. Return only the JSON object with word, definition, prompt, and follow_up fields."
            
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 200,
                "response_format": {"type": "json_object"}
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    word_data = json.loads(content)
                    
                    # Validate required fields
                    required_fields = ["word", "definition", "prompt", "follow_up"]
                    if all(field in word_data for field in required_fields):
                        logger.info(f"Generated word with Groq: {word_data['word']}")
                        return word_data
                    else:
                        raise ValueError(f"Missing required fields in Groq response: {word_data}")
                else:
                    error_text = await response.text()
                    logger.error(f"Groq API error {response.status}: {error_text}")
                    raise Exception(f"Groq API error: {error_text}")
                    
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Groq JSON response: {e}")
            raise Exception("Invalid JSON response from Groq")
        except Exception as e:
            logger.error(f"Error generating word with Groq: {e}")
            raise

