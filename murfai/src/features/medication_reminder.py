"""Medication reminder system with conversational flow."""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from ..memory.conversation_db import ConversationMemory

logger = logging.getLogger(__name__)

class MedicationReminder:
    """Conversational medication reminder system with dynamic templates."""
    
    def __init__(self, memory: ConversationMemory, dynamic_config=None):
        """
        Initialize medication reminder.
        
        Args:
            memory: Conversation memory instance
            dynamic_config: DynamicConfig instance for templates
        """
        self.memory = memory
        self.dynamic_config = dynamic_config
        self.last_reminder_time = {}
    
    def check_medications_due(self) -> List[Dict]:
        """
        Check if any medications are due now.
        
        Returns:
            List of medications due
        """
        current_time = datetime.now().strftime("%H:%M")
        current_day = datetime.now().weekday()  # 0=Monday, 6=Sunday
        medications = self.memory.get_medications_due(current_time, current_day)
        
        # Filter out recently reminded medications
        due_medications = []
        for med in medications:
            med_id = med['id']
            last_reminded = med.get('last_reminded')
            
            # Only remind if not reminded in last 30 minutes
            if last_reminded:
                last_time = datetime.fromisoformat(last_reminded)
                if datetime.now() - last_time < timedelta(minutes=30):
                    continue
            
            due_medications.append(med)
        
        return due_medications
    
    def generate_reminder_message(self, medication: Dict) -> str:
        """
        Generate conversational reminder message using dynamic templates.
        
        Args:
            medication: Medication dictionary
            
        Returns:
            Reminder message
        """
        med_name = medication['medication_name']
        current_hour = datetime.now().hour
        current_time = datetime.now().strftime("%H:%M")
        
        # Determine time context
        if current_hour < 12:
            time_context = "morning"
        elif current_hour < 17:
            time_context = "afternoon"
        else:
            time_context = "evening"
        
        # Get template from dynamic config
        if self.dynamic_config:
            try:
                template = self.dynamic_config.get_medication_template(time_context)
                message = template.format(time=current_time, medication=med_name)
                return message
            except Exception as e:
                logger.warning(f"Error using dynamic template: {e}, using fallback")
        
        # Fallback to default template
        meal_context = "breakfast" if time_context == "morning" else ("lunch" if time_context == "afternoon" else "dinner")
        return f"I noticed it's time for your {med_name}. Usually we take it around this time. Have you had {meal_context} yet?"
    
    def handle_medication_response(self, user_response: str, medication: Dict) -> str:
        """
        Handle user's response to medication reminder using dynamic templates.
        
        Args:
            user_response: User's response
            medication: Medication dictionary
            
        Returns:
            Follow-up message
        """
        response_lower = user_response.lower()
        med_name = medication['medication_name']
        
        # Determine response type
        if any(word in response_lower for word in ["no", "not yet", "haven't", "didn't"]):
            response_type = "not_eaten"
        elif any(word in response_lower for word in ["yes", "taken", "already", "done"]):
            response_type = "taken"
        else:
            response_type = "not_eaten"  # Default
        
        # Get template from dynamic config
        if self.dynamic_config:
            try:
                template = self.dynamic_config.get_medication_follow_up(response_type)
                message = template.format(medication=med_name)
                return message
            except Exception as e:
                logger.warning(f"Error using dynamic template: {e}, using fallback")
        
        # Fallback to default responses
        if response_type == "not_eaten":
            return f"Okay, let's get some food first, then the {med_name}. I'll remind you again in 10 minutes."
        elif response_type == "taken":
            return f"Great! I'm glad you remembered. How are you feeling today?"
        else:
            return f"Just let me know when you're ready, and I'll remind you about the {med_name}."
    
    def schedule_reminder(self, medication_name: str, time: str):
        """
        Schedule a medication reminder.
        
        Args:
            medication_name: Name of medication
            time: Time in HH:MM format
        """
        self.memory.save_medication_schedule(medication_name, time)
        logger.info(f"Scheduled reminder: {medication_name} at {time}")

