from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ChatSession(BaseModel):
    id: Optional[str] = None
    wallet_address: str
    server_id: str
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChatMessage(BaseModel):
    id: Optional[str] = None
    session_id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None