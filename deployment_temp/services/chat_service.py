from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any
from models.chat import ChatSession, ChatMessage
from services.supabase_client import supabase_client


class ChatService:
    def __init__(self):
        self.db = supabase_client

    def create_chat_session(self, user_id: str, title: str = "New Chat") -> ChatSession:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        query = """
            INSERT INTO chat_sessions (id, user_id, title, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, user_id, title, created_at, updated_at
        """
        print(query)
        result = self.db.execute_query(
            query, 
            (session_id, user_id, title, created_at, created_at)
        )
        print(result)
        if result:
            row = result[0]
            return ChatSession(
                id=row['id'],
                user_id=row['user_id'],
                title=row['title'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        
        raise Exception("Failed to create chat session")

    def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID"""
        query = """
            SELECT id, user_id, title, created_at, updated_at
            FROM chat_sessions 
            WHERE id = %s
        """
        
        result = self.db.execute_query(query, (session_id,))
        
        if result:
            row = result[0]
            return ChatSession(
                id=row['id'],
                user_id=row['user_id'],
                title=row['title'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        
        return None

    def add_message(self, session_id: str, role: str, content: str, code: Optional[str] = None, next_steps: Optional[str] = None, is_deployable: Optional[bool] = None, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        """Add a message to a chat session"""
        message_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        query = """
            INSERT INTO chat_messages (id, session_id, role, content, code, next_steps, is_deployable, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, session_id, role, content, code, next_steps, is_deployable, metadata, created_at
        """
        
        import json
        metadata_json = json.dumps(metadata) if metadata else None
        
        result = self.db.execute_query(
            query,
            (message_id, session_id, role, content, code, next_steps, is_deployable, metadata_json, created_at)
        )
        
        if result:
            row = result[0]
            return ChatMessage(
                id=row['id'],
                session_id=row['session_id'],
                role=row['role'],
                content=row['content'],
                code=row['code'],
                next_steps=row['next_steps'],
                is_deployable=row['is_deployable'],
                metadata=row['metadata'],
                created_at=row['created_at']
            )
        
        raise Exception("Failed to add message")

    def get_conversation_history(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a chat session"""
        query = """
            SELECT id, session_id, role, content, code, next_steps, is_deployable, metadata, created_at
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
                code=row['code'],
                next_steps=row['next_steps'],
                is_deployable=row['is_deployable'],
                metadata=row['metadata'],
                created_at=row['created_at']
            ))
        
        return messages

    def get_user_chat_sessions(self, user_id: str) -> List[ChatSession]:
        """Get all chat sessions for a specific user"""
        query = """
            SELECT id, user_id, title, created_at, updated_at
            FROM chat_sessions 
            WHERE user_id = %s
            ORDER BY updated_at DESC
        """
        
        result = self.db.execute_query(query, (user_id,))
        
        sessions = []
        for row in result:
            sessions.append(ChatSession(
                id=row['id'],
                user_id=row['user_id'],
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

    def add_llm_response(self, session_id: str, llm_response: str) -> ChatMessage:
        """Parse LLM response as JSON and add message with extracted fields"""
        import json
        
        code = None
        next_steps = None
        is_deployable = None
        content = llm_response
        
        try:
            # Try to parse the response as JSON
            parsed_response = json.loads(llm_response)
            
            # Extract fields if they exist
            if isinstance(parsed_response, dict):
                code = parsed_response.get('code')
                next_steps = parsed_response.get('next_steps')
                is_deployable = parsed_response.get('is_deployable')
                # Use the content field if it exists, otherwise use the original response
                content = parsed_response.get('content', llm_response)
        except json.JSONDecodeError:
            # If it's not valid JSON, treat the entire response as content
            pass
        
        return self.add_message(
            session_id=session_id,
            role="assistant",
            content=content,
            code=code,
            next_steps=next_steps,
            is_deployable=is_deployable
        )


chat_service = ChatService()