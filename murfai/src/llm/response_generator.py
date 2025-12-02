"""Dynamic LLM-based response generator using free APIs."""
import aiohttp
import json
import logging
import os
from typing import Optional, Dict, List
from ..config import Config

logger = logging.getLogger(__name__)

class DynamicResponseGenerator:
    """Generate dynamic responses using free LLM APIs."""
    
    def __init__(self, api_provider: str = "huggingface", config: Optional[Dict] = None):
        """
        Initialize response generator.
        
        Args:
            api_provider: LLM provider ("huggingface", "groq", or "local")
            config: Optional config dictionary with API keys
        """
        self.api_provider = api_provider
        self.session: Optional[aiohttp.ClientSession] = None
        self.config = config or {}
        
        # Load API keys from environment or config
        if api_provider == "huggingface":
            self.api_key = os.getenv("HUGGINGFACE_API_KEY", "") or self.config.get("llm", {}).get("api_key", "")
        elif api_provider == "groq":
            self.api_key = os.getenv("GROQ_API_KEY", "") or self.config.get("llm", {}).get("api_key", "")
        else:
            self.api_key = ""
        
    async def _get_session(self):
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _build_system_prompt(self, sentiment: str, context: str, state: str) -> str:
        """
        Build dynamic system prompt based on context.
        
        Args:
            sentiment: Detected sentiment
            context: Conversation context
            state: Current conversation state
            
        Returns:
            System prompt string
        """
        base_prompt = """You are a warm, empathetic AI companion for elderly users. Your role is to:
- Provide emotional support and companionship
- Remember past conversations and reference them naturally
- Use simple, clear language appropriate for seniors
- Be patient and understanding
- Show genuine interest in their stories and memories
- Adapt your tone based on their emotional state

Guidelines:
- Keep responses concise (1-2 sentences, max 50 words)
- Use warm, conversational language
- Ask follow-up questions to encourage conversation
- Reference past conversations when relevant
- Never be condescending or patronizing
"""
        
        # Add sentiment-specific guidance
        if sentiment == "sad":
            base_prompt += "\n- The user seems sad. Be extra gentle, compassionate, and supportive.\n- Use softer, more comforting language.\n- Offer to listen without pushing.\n"
        elif sentiment == "happy":
            base_prompt += "\n- The user seems happy. Match their energy positively but not overly excited.\n- Celebrate with them naturally.\n"
        
        # Add state-specific guidance
        if state == "medication_reminder":
            base_prompt += "\n- You're in a medication reminder conversation. Be helpful and conversational, not alarm-like.\n"
        elif state == "word_of_day":
            base_prompt += "\n- You're discussing a word of the day. Keep it engaging and encourage the user to share.\n"
        elif state == "medication_nudge":
            base_prompt += (
                "\n- This is a medication follow-up. Remind them kindly, confirm if they've taken it,"
                " and offer help. Use calm, reassuring words.\n"
            )
        elif state == "reminiscence":
            base_prompt += (
                "\n- The user needs gentle reminiscence therapy. Invite them to share a warm memory,"
                " ask about sensory details, and validate their feelings. Keep a hopeful, nostalgic tone.\n"
            )
        elif state == "patience_prompt":
            base_prompt += (
                "\n- The user has been silent. Offer a short, friendly nudge letting them know you're still listening"
                " with no pressure. Encourage them softly to continue when ready.\n"
            )
        
        return base_prompt
    
    async def generate_response(
        self,
        user_message: str,
        sentiment: str,
        context: str,
        state: str = "idle",
        additional_context: Optional[Dict] = None
    ) -> str:
        """
        Generate dynamic response using LLM.
        
        Args:
            user_message: User's message
            sentiment: Detected sentiment
            context: Conversation history context
            state: Current conversation state
            additional_context: Additional context (medications, word of day, etc.)
            
        Returns:
            Generated response text
        """
        if self.api_provider == "huggingface":
            return await self._generate_huggingface(user_message, sentiment, context, state, additional_context)
        elif self.api_provider == "groq":
            return await self._generate_groq(user_message, sentiment, context, state, additional_context)
        else:
            # Fallback to rule-based (but still dynamic)
            return self._generate_rule_based(user_message, sentiment, context, state, additional_context)
    
    async def _generate_huggingface(
        self,
        user_message: str,
        sentiment: str,
        context: str,
        state: str,
        additional_context: Optional[Dict]
    ) -> str:
        """Generate response using Hugging Face Inference API (free tier)."""
        try:
            session = await self._get_session()
            
            # Use a small, fast model for free tier
            model = "microsoft/DialoGPT-medium"  # Free, no API key needed for some models
            api_url = f"https://api-inference.huggingface.co/models/{model}"
            
            # Build prompt
            system_prompt = self._build_system_prompt(sentiment, context, state)
            
            # Build conversation history
            messages = []
            if context and context != "No previous conversations.":
                # Parse context into messages
                lines = context.split("\n")
                for line in lines:
                    if line.startswith("User: "):
                        messages.append({"role": "user", "content": line[6:]})
                    elif line.startswith("AI: "):
                        messages.append({"role": "assistant", "content": line[4:]})
            
            messages.append({"role": "user", "content": user_message})
            
            # Add additional context if available
            if additional_context:
                if "medication" in additional_context:
                    user_message += f" [Context: Medication reminder about {additional_context['medication']}]"
                if "word_of_day" in additional_context:
                    user_message += f" [Context: Discussing word '{additional_context['word_of_day']}']"
            
            payload = {
                "inputs": {
                    "past_user_inputs": [msg["content"] for msg in messages[:-1] if msg["role"] == "user"],
                    "generated_responses": [msg["content"] for msg in messages[:-1] if msg["role"] == "assistant"],
                    "text": user_message
                },
                "parameters": {
                    "max_length": 100,
                    "temperature": 0.7,
                    "do_sample": True
                }
            }
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            async with session.post(api_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    result = await response.json()
                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get("generated_text", "")
                        # Clean up the response
                        response_text = generated_text.strip()
                        # Limit length
                        if len(response_text) > 150:
                            response_text = response_text[:150].rsplit('.', 1)[0] + "."
                        return response_text if response_text else self._generate_rule_based(user_message, sentiment, context, state, additional_context)
                    else:
                        return self._generate_rule_based(user_message, sentiment, context, state, additional_context)
                else:
                    logger.warning(f"Hugging Face API returned {response.status}, using rule-based fallback")
                    return self._generate_rule_based(user_message, sentiment, context, state, additional_context)
                    
        except Exception as e:
            logger.warning(f"Error with Hugging Face API: {e}, using rule-based fallback")
            return self._generate_rule_based(user_message, sentiment, context, state, additional_context)
    
    async def _generate_groq(
        self,
        user_message: str,
        sentiment: str,
        context: str,
        state: str,
        additional_context: Optional[Dict]
    ) -> str:
        """Generate response using Groq API (free tier, very fast)."""
        try:
            # Get API key from environment or config
            groq_key = os.getenv("GROQ_API_KEY", "") or self.api_key
            if not groq_key:
                logger.warning("Groq API key not found. Using rule-based fallback.")
                return self._generate_rule_based(user_message, sentiment, context, state, additional_context)
            
            session = await self._get_session()
            
            system_prompt = self._build_system_prompt(sentiment, context, state)
            
            # Build messages
            messages = [{"role": "system", "content": system_prompt}]
            
            if context and context != "No previous conversations.":
                lines = context.split("\n")
                for line in lines:
                    if line.startswith("User: "):
                        messages.append({"role": "user", "content": line[6:]})
                    elif line.startswith("AI: "):
                        messages.append({"role": "assistant", "content": line[4:]})
            
            messages.append({"role": "user", "content": user_message})
            
            payload = {
                "model": "llama-3.1-8b-instant",  # Free, fast model
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 100
            }
            
            headers = {
                "Authorization": f"Bearer {groq_key}",
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
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    return self._generate_rule_based(user_message, sentiment, context, state, additional_context)
                    
        except Exception as e:
            logger.warning(f"Error with Groq API: {e}, using rule-based fallback")
            return self._generate_rule_based(user_message, sentiment, context, state, additional_context)
    
    def _generate_rule_based(
        self,
        user_message: str,
        sentiment: str,
        context: str,
        state: str,
        additional_context: Optional[Dict]
    ) -> str:
        """
        Dynamic rule-based fallback that's more flexible than hard-coded responses.
        
        Args:
            user_message: User's message
            sentiment: Detected sentiment
            context: Conversation context
            state: Current state
            additional_context: Additional context
            
        Returns:
            Generated response
        """
        message_lower = user_message.lower()
        
        # Handle special states dynamically
        if state == "medication_reminder" and additional_context and "medication" in additional_context:
            med_name = additional_context["medication"]
            if any(word in message_lower for word in ["no", "not yet", "haven't"]):
                return f"Okay, let's get some food first, then the {med_name}. I'll remind you again in 10 minutes."
            elif any(word in message_lower for word in ["yes", "taken", "done"]):
                return f"Great! I'm glad you remembered. How are you feeling today?"
            else:
                return f"Just let me know when you're ready, and I'll remind you about the {med_name}."
        
        if state == "word_of_day" and additional_context and "word_of_day" in additional_context:
            word_info = additional_context["word_of_day"]
            if any(word in message_lower for word in ["yes", "love", "like", "enjoy"]):
                return word_info.get("follow_up", "That's wonderful! Tell me more about that.")
            elif any(word in message_lower for word in ["no", "don't", "not"]):
                return "That's okay, we all have different preferences. What do you enjoy instead?"
            else:
                return "That's a wonderful story. Thank you for sharing that with me."
        
        # Dynamic sentiment-based responses
        if sentiment == "sad":
            if any(word in message_lower for word in ["miss", "lonely", "sad", "depressed"]):
                return "I'm here with you. It's okay to feel this way. Would you like to talk about what's on your mind? I'm listening."
            elif any(word in message_lower for word in ["husband", "wife", "spouse", "partner", "loved one"]):
                return "They sound like a wonderful person. Would you like to tell me more about them? I'd love to hear your memories."
            else:
                return "I understand. Sometimes it helps to talk about things. I'm here to listen whenever you need me."
        
        elif sentiment == "happy":
            if any(word in message_lower for word in ["great", "wonderful", "amazing", "excited"]):
                return "That's wonderful to hear! I'm so glad you're feeling good. What made you happy today?"
            else:
                return "That sounds lovely! Tell me more about what's making you happy."
        
        # Greeting detection
        if any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
            return "Hello! It's so good to hear from you. How are you feeling today?"
        
        # Question detection
        if "how are you" in message_lower or "how's your day" in message_lower:
            return "I'm doing well, thank you for asking! I've been thinking about you. How has your day been so far?"
        
        # Reference context if available
        if context and context != "No previous conversations.":
            # Try to reference something from context
            return "That's interesting. Tell me more about that. I'm here to listen."
        
        # Default engaging response
        return "I'd love to hear more about that. Can you tell me more?"

