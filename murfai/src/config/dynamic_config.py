"""Dynamic configuration loader from files and environment."""
import json
import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class DynamicConfig:
    """Load and manage dynamic configuration."""
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize dynamic config.
        
        Args:
            config_file: Path to JSON configuration file
        """
        self.config_file = config_file
        self.config_data: Dict = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or create default."""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.warning(f"Error loading config file: {e}, using defaults")
                self.config_data = self._get_default_config()
        else:
            logger.info(f"Config file not found, creating default at {self.config_file}")
            self.config_data = self._get_default_config()
            self.save_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            "llm": {
                "provider": os.getenv("LLM_PROVIDER", "huggingface"),
                "api_key": os.getenv("HUGGINGFACE_API_KEY", ""),
                "model": "microsoft/DialoGPT-medium",
                "temperature": 0.7,
                "max_tokens": 100
            },
            "voice_styles": {
                "happy": "Excited",
                "sad": "Whisper",
                "neutral": "Conversational",
                "calm": "Soft"
            },
            "word_database": {
                "source": "groq",  # Always use Groq for dynamic word generation
                "provider": "groq",
                "note": "Words are now generated dynamically using Groq API - no static database"
            },
            "medication_reminders": {
                "templates": {
                    "morning": "I noticed it's {time}. Usually, we take {medication} now with some water. Have you had breakfast yet?",
                    "afternoon": "It's {time} and time for your {medication}. Have you had lunch yet?",
                    "evening": "Good evening! It's {time} and time for your {medication}. Have you had dinner?"
                },
                "follow_ups": {
                    "not_eaten": "Okay, let's get some food first, then the {medication}. I'll remind you in 10 minutes.",
                    "eaten": "Great! I'm glad you remembered. How are you feeling today?",
                    "taken": "Perfect! I'm proud of you for remembering. Is there anything else you'd like to talk about?"
                }
            },
            "conversation": {
                "system_prompt_template": "You are a warm, empathetic AI companion for elderly users. {sentiment_guidance} {state_guidance}",
                "max_context_length": 5,
                "response_max_length": 150
            },
            "features": {
                "medication_reminders": True,
                "word_of_day": True,
                "sentiment_analysis": True,
                "sundowning_support": True
            }
        }
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get(self, key_path: str, default=None):
        """
        Get configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path (e.g., "llm.provider")
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value):
        """
        Set configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config_data
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self.save_config()
    
    def get_words(self) -> List[Dict]:
        """Get word database - now always uses Groq (returns empty list as words are generated dynamically)."""
        # Words are now generated dynamically via Groq API
        # This method is kept for compatibility but returns empty list
        logger.info("Word database now uses Groq for dynamic generation")
        return []
    
    def get_medication_template(self, time_of_day: str) -> str:
        """Get medication reminder template for time of day."""
        templates = self.get("medication_reminders.templates", {})
        return templates.get(time_of_day, templates.get("morning", "Time for your {medication}."))
    
    def get_medication_follow_up(self, response_type: str) -> str:
        """Get medication reminder follow-up template."""
        follow_ups = self.get("medication_reminders.follow_ups", {})
        return follow_ups.get(response_type, "Okay, I'll remind you again later.")

