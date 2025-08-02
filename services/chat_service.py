from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any
from models.chat import ChatSession, ChatMessage
from services.supabase_client import supabase_client


class ChatService:
    def __init__(self):
        self.db = supabase_client

    def create_chat_session(self, wallet_address: str, title: str = "New Chat") -> ChatSession:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        query = """
            INSERT INTO chat_sessions (id, wallet_address, title, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, wallet_address, title, created_at, updated_at
        """
        
        result = self.db.execute_query(
            query, 
            (session_id, wallet_address, title, created_at, created_at)
        )
        
        if result:
            row = result[0]
            return ChatSession(
                id=row['id'],
                wallet_address=row['wallet_address'],
                title=row['title'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        
        raise Exception("Failed to create chat session")

    def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID"""
        query = """
            SELECT id, wallet_address, title, created_at, updated_at
            FROM chat_sessions 
            WHERE id = %s
        """
        
        result = self.db.execute_query(query, (session_id,))
        
        if result:
            row = result[0]
            return ChatSession(
                id=row['id'],
                wallet_address=row['wallet_address'],
                title=row['title'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        
        return None

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        """Add a message to a chat session"""
        message_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        query = """
            INSERT INTO chat_messages (id, session_id, role, content, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, session_id, role, content, metadata, created_at
        """
        
        import json
        metadata_json = json.dumps(metadata) if metadata else None
        
        result = self.db.execute_query(
            query,
            (message_id, session_id, role, content, metadata_json, created_at)
        )
        
        if result:
            row = result[0]
            return ChatMessage(
                id=row['id'],
                session_id=row['session_id'],
                role=row['role'],
                content=row['content'],
                metadata=row['metadata'],
                created_at=row['created_at']
            )
        
        raise Exception("Failed to add message")

    def get_conversation_history(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a chat session"""
        query = """
            SELECT id, session_id, role, content, metadata, created_at
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
        """
        
        result = self.db.execute_query(query, (session_id,))
        
        messages = []
        for row in result:
            messages.append(ChatMessage(
                id=row['id'],
                session_id=row['session_id'],
                role=row['role'],
                content=row['content'],
                metadata=row['metadata'],
                created_at=row['created_at']
            ))
        
        return messages

    def get_user_chat_sessions(self, wallet_address: str) -> List[ChatSession]:
        """Get all chat sessions for a specific user"""
        query = """
            SELECT id, wallet_address, title, created_at, updated_at
            FROM chat_sessions 
            WHERE wallet_address = %s
            ORDER BY updated_at DESC
        """
        
        result = self.db.execute_query(query, (wallet_address,))
        
        sessions = []
        for row in result:
            sessions.append(ChatSession(
                id=row['id'],
                wallet_address=row['wallet_address'],
                title=row['title'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ))
        
        return sessions

    def update_session_timestamp(self, session_id: str):
        """Update the updated_at timestamp for a session"""
        query = """
            UPDATE chat_sessions 
            SET updated_at = %s 
            WHERE id = %s
        """
        
        self.db.execute_query(query, (datetime.utcnow(), session_id))


chat_service = ChatService()