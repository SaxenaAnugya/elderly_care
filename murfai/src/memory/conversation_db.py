"""Conversation memory database for remembering past interactions."""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ConversationMemory:
    """Store and retrieve conversation history."""
    
    def __init__(self, db_path: str):
        """
        Initialize conversation memory.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                sentiment TEXT,
                topic TEXT
            )
        """)
        
        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Medication schedule table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medication_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medication_name TEXT NOT NULL,
                time TEXT NOT NULL,
                last_reminded TEXT,
                last_taken TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def save_conversation(
        self,
        user_message: str,
        ai_response: str,
        sentiment: Optional[str] = None,
        topic: Optional[str] = None
    ):
        """
        Save a conversation turn.
        
        Args:
            user_message: User's message
            ai_response: AI's response
            sentiment: Detected sentiment
            topic: Conversation topic
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversations (timestamp, user_message, ai_response, sentiment, topic)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), user_message, ai_response, sentiment, topic))
        
        conn.commit()
        conn.close()
        logger.debug(f"Saved conversation: {user_message[:50]}...")
    
    def get_recent_conversations(self, limit: int = 10) -> List[Dict]:
        """
        Get recent conversations.
        
        Args:
            limit: Number of recent conversations to retrieve
            
        Returns:
            List of conversation dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM conversations
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_conversation_context(self, limit: int = 5) -> str:
        """
        Get conversation context as formatted string.
        
        Args:
            limit: Number of recent conversations to include
            
        Returns:
            Formatted context string
        """
        conversations = self.get_recent_conversations(limit)
        
        if not conversations:
            return "No previous conversations."
        
        context_parts = []
        for conv in reversed(conversations):  # Reverse to show chronological order
            context_parts.append(f"User: {conv['user_message']}")
            context_parts.append(f"AI: {conv['ai_response']}")
        
        return "\n".join(context_parts)
    
    def save_medication_schedule(self, medication_name: str, time: str):
        """
        Save medication schedule.
        
        Args:
            medication_name: Name of medication
            time: Time to take medication (HH:MM format)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if medication already exists at this time
        cursor.execute("""
            SELECT id FROM medication_schedule
            WHERE medication_name = ? AND time = ?
        """, (medication_name, time))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            cursor.execute("""
                UPDATE medication_schedule
                SET medication_name = ?, time = ?
                WHERE id = ?
            """, (medication_name, time, existing[0]))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO medication_schedule (medication_name, time)
                VALUES (?, ?)
            """, (medication_name, time))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved medication schedule: {medication_name} at {time}")
    
    def get_medications_due(self, current_time: str) -> List[Dict]:
        """
        Get medications due at current time.
        
        Args:
            current_time: Current time in HH:MM format
            
        Returns:
            List of medications due
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM medication_schedule
            WHERE time = ?
        """, (current_time,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def mark_medication_reminded(self, medication_id: int):
        """Mark medication as reminded."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE medication_schedule
            SET last_reminded = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), medication_id))
        
        conn.commit()
        conn.close()

